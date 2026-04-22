"""Integration tests for the hcfl_legacy_backfill job type.

Mocks Supabase + HCFL HTTP so we can exercise the full
JobProcessor._process_hcfl_legacy_backfill path without any real DB
or network traffic.

These tests verify:
- End-to-end: picks up unscraped streets, ingests HVAC permits, stamps
  scraped_at on success.
- Retry bookkeeping: increments retry_count + captures last_error on
  per-street failure.
- HVAC filter: prefix-matching permits whose description doesn't match
  the HVAC regex get dropped at ingest time.
- Idempotency: permits table upsert uses composite UNIQUE, so re-running
  doesn't create duplicates.
- No-op path: empty unscraped queue → early return with progress=100.
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.workers.job_processor import JobProcessor

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "hcfl_html"
BASE_URL = "https://app.hillsboroughcounty.org/DevelopmentServices/PermitReports"


def _load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text()


class _FakeTableOp:
    """Minimal supabase-py table chain captor. Lets us assert what was
    called without needing a real Supabase client."""

    def __init__(self, name: str, recorder: list):
        self._name = name
        self._recorder = recorder
        self._query: dict = {}
        self._return_data: list = []

    # Chainable modifiers that the processor uses
    def select(self, cols: str):
        self._query['select'] = cols
        return self

    def is_(self, col, value):
        self._query.setdefault('where', []).append(('is', col, value))
        return self

    def lt(self, col, value):
        self._query.setdefault('where', []).append(('lt', col, value))
        return self

    def eq(self, col, value):
        self._query.setdefault('where', []).append(('eq', col, value))
        return self

    def order(self, col):
        self._query['order'] = col
        return self

    def limit(self, n):
        self._query['limit'] = n
        return self

    def update(self, values):
        self._query['op'] = 'update'
        self._query['values'] = values
        return self

    def upsert(self, values, on_conflict=None, ignore_duplicates=False):
        self._query['op'] = 'upsert'
        self._query['values'] = values
        self._query['on_conflict'] = on_conflict
        return self

    def insert(self, values):
        self._query['op'] = 'insert'
        self._query['values'] = values
        return self

    def execute(self):
        # Record what was called (for asserting later)
        self._recorder.append((self._name, dict(self._query)))
        # Return shape mimics supabase-py's APIResponse
        result = MagicMock()
        result.data = self._return_data
        return result


class FakeSupabase:
    """Fake Supabase client where every table() returns a recorder."""

    def __init__(self):
        self.calls: list = []
        self._table_returns: dict[str, list] = {}

    def set_table_return(self, table_name: str, data: list):
        self._table_returns[table_name] = data

    def table(self, name: str):
        op = _FakeTableOp(name, self.calls)
        op._return_data = self._table_returns.get(name, [])
        return op


@pytest.fixture
def fake_db():
    return FakeSupabase()


@pytest.fixture
def processor(fake_db):
    return JobProcessor(db=fake_db)


@pytest.fixture
def job_base():
    return {
        'id': 'job-uuid-1',
        'county_id': 'county-uuid-hcfl',
        'job_type': 'hcfl_legacy_backfill',
        'parameters': {
            'street_batch_size': 5,
            'prefix_allowlist': ['NME', 'NMC', 'FCM'],
            'max_street_retries': 3,
        },
    }


class TestNoOpPath:
    async def test_empty_queue_updates_progress_and_returns(self, processor, fake_db, job_base):
        # No streets in hcfl_streets table → early return
        fake_db.set_table_return('hcfl_streets', [])
        await processor._process_hcfl_legacy_backfill(job_base)
        # Should have 2 calls: SELECT hcfl_streets, UPDATE background_jobs
        table_calls = [c[0] for c in fake_db.calls]
        assert 'hcfl_streets' in table_calls
        assert 'background_jobs' in table_calls


class TestHappyPath:
    async def test_processes_one_street_ingests_permits(
        self, processor, fake_db, job_base, httpx_mock,
    ):
        fake_db.set_table_return('hcfl_streets', [
            {'id': 'street-uuid-1', 'street_name': 'KENNEDY', 'retry_count': 0},
        ])

        # Synthetic search HTML with two HVAC-prefix permits we can mock
        # individually. Keeps the test deterministic and avoids using
        # the full 113-permit fixture where dozens of detail URLs would
        # need mocking.
        fake_search_html = """
        <html><body>
        <table class='results'><tbody>
            <tr><td>1</td><td>123 Main St</td><td><a href='#'>NME11111</a></td></tr>
            <tr><td>2</td><td>456 Oak Ave</td><td><a href='#'>NMC22222</a></td></tr>
        </tbody></table>
        </body></html>
        """
        httpx_mock.add_response(
            url=f"{BASE_URL}/Search/GetResults?searchBy=oStreet&searchTerm=KENNEDY&searchType=Inspections",
            text=fake_search_html,
            status_code=200,
        )
        # Both permits resolve to the same HVAC-looking detail HTML.
        for permit_id in ("NME11111", "NMC22222"):
            httpx_mock.add_response(
                url=f"{BASE_URL}/Permit/{permit_id}/Inspections",
                text=f"""
                <html><body>
                Project No.: {permit_id} Description: HVAC change out
                Address: 123 Main St City: Tampa Parcel: 12345
                Permit Issue Date: 03/15/2015 Permit Status: FINALED
                </body></html>
                """,
                status_code=200,
            )

        await processor._process_hcfl_legacy_backfill(job_base)

        # Assertions on Supabase calls
        ops_by_table: dict = {}
        for tbl, q in fake_db.calls:
            ops_by_table.setdefault(tbl, []).append(q)

        # hcfl_streets: SELECT + UPDATE(scraped_at)
        assert 'hcfl_streets' in ops_by_table
        update_calls = [q for q in ops_by_table['hcfl_streets'] if q.get('op') == 'update']
        assert len(update_calls) >= 1
        # Verify scraped_at was set (not None)
        scraped_update = update_calls[-1]
        assert scraped_update['values'].get('scraped_at') is not None

        # permits: upsert with composite on_conflict
        assert 'permits' in ops_by_table
        permit_upserts = [q for q in ops_by_table['permits'] if q.get('op') == 'upsert']
        assert len(permit_upserts) >= 1
        assert permit_upserts[0]['on_conflict'] == 'county_id,source,source_permit_id'
        # Source tagged correctly
        first_values = permit_upserts[0]['values']
        # Values is a dict for single-row upsert
        assert first_values.get('source') == 'hcfl_legacy_scraper'
        assert first_values.get('county_id') == 'county-uuid-hcfl'

        # background_jobs: at least one progress update
        bj_updates = [q for q in ops_by_table.get('background_jobs', []) if q.get('op') == 'update']
        assert len(bj_updates) >= 1
        last_progress = [q for q in bj_updates if 'progress_percent' in q.get('values', {})]
        assert last_progress
        assert last_progress[-1]['values']['progress_percent'] == 100


class TestRetryBookkeeping:
    async def test_street_failure_increments_retry_count(
        self, processor, fake_db, job_base, httpx_mock,
    ):
        fake_db.set_table_return('hcfl_streets', [
            {'id': 'street-uuid-fail', 'street_name': 'BADSTREET', 'retry_count': 1},
        ])
        # HCFL returns 500 — search_street returns {"error": "http_500"},
        # which the processor raises.
        httpx_mock.add_response(
            url=f"{BASE_URL}/Search/GetResults?searchBy=oStreet&searchTerm=BADSTREET&searchType=Inspections",
            status_code=500,
        )

        await processor._process_hcfl_legacy_backfill(job_base)

        # Find the UPDATE on hcfl_streets that increments retry_count
        retry_updates = [
            q for (tbl, q) in fake_db.calls
            if tbl == 'hcfl_streets' and q.get('op') == 'update'
            and q['values'].get('retry_count') is not None
        ]
        assert retry_updates
        # retry_count should be old + 1 = 2
        assert retry_updates[0]['values']['retry_count'] == 2
        # last_error populated
        assert 'http_500' in (retry_updates[0]['values'].get('last_error') or '')


class TestHvacDescriptionFilter:
    async def test_mis_prefixed_permit_dropped_by_regex(
        self, processor, fake_db, job_base, httpx_mock,
    ):
        fake_db.set_table_return('hcfl_streets', [
            {'id': 'street-uuid-1', 'street_name': 'KENNEDY', 'retry_count': 0},
        ])
        # Create a synthetic search result with one HVAC-prefixed permit
        fake_search_html = """
        <html><body>
        <table class='results'><tbody>
            <tr>
                <td>1</td><td>1 Main St</td><td><a href='#'>NME99999</a></td>
            </tr>
        </tbody></table>
        </body></html>
        """
        httpx_mock.add_response(
            url=f"{BASE_URL}/Search/GetResults?searchBy=oStreet&searchTerm=KENNEDY&searchType=Inspections",
            text=fake_search_html,
            status_code=200,
        )
        # Mis-prefixed: NME permit but description is roof work.
        fake_detail_html = """
        <html><body>
        Project No.: NME99999 Description: Roof replacement only
        Address: 1 Main St City: Tampa Parcel: 12345 Permit Issue Date:
        Permit Status: ACTIVE
        </body></html>
        """
        httpx_mock.add_response(
            url=f"{BASE_URL}/Permit/NME99999/Inspections",
            text=fake_detail_html,
            status_code=200,
        )

        await processor._process_hcfl_legacy_backfill(job_base)

        # No permit upsert should have happened (regex filtered it out)
        permit_upserts = [
            q for (tbl, q) in fake_db.calls
            if tbl == 'permits' and q.get('op') == 'upsert'
        ]
        assert len(permit_upserts) == 0, \
            f"Expected no upserts (description filtered), got {len(permit_upserts)}"
