"""CRITICAL correctness tests: property aggregation is load-order independent.

The user's explicit requirement (quoted from the grill-me session):

  "let's say we find an HVAC permit from 10 years ago. But we don't
   look at what's replaced a month ago. It would appear as though
   the HVAC is 10 years old, and that's just not the case. We need
   to aggregate all of the data for that address."

This test suite PROVES the invariant by processing the same set of
permits in all 6 permutations (3! = 6) and asserting the final
property state is identical. If a future refactor ever breaks
commutativity (e.g., by inlining a sort-by-date that depends on
insertion order), this suite fails loudly.

The tests don't touch the real DB — they use FakeSupabase that
records mutations in an in-memory store, giving us deterministic
"final state" snapshots to compare.
"""
import copy
import itertools
from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services.property_aggregator import PropertyAggregator


class FakePropertiesTable:
    """In-memory stand-in for the Supabase `properties` table. Tracks
    state by (county_id, normalized_address) tuple so upserts with
    on_conflict='county_id,normalized_address' behave like real DB."""

    def __init__(self):
        self._store: dict[tuple, dict] = {}  # (county_id, normalized_address) -> row
        self._by_id: dict[str, dict] = {}

    def upsert(self, data: dict, on_conflict: str | None = None) -> dict:
        key = (data['county_id'], data['normalized_address'])
        if key in self._store:
            # Merge: update existing
            existing = self._store[key]
            existing.update(data)
            return existing
        row = {**data, 'id': str(uuid4())}
        self._store[key] = row
        self._by_id[row['id']] = row
        return row

    def update_by_id(self, property_id: str, values: dict):
        if property_id not in self._by_id:
            raise KeyError(property_id)
        self._by_id[property_id].update(values)
        return self._by_id[property_id]

    def select_by_key(self, county_id: str, normalized_address: str) -> list[dict]:
        key = (county_id, normalized_address)
        if key in self._store:
            return [self._store[key]]
        return []

    def select_by_id(self, property_id: str) -> list[dict]:
        if property_id in self._by_id:
            return [self._by_id[property_id]]
        return []


class FakeLeadsTable:
    """Minimal leads table — tracks one row per property_id."""
    def __init__(self):
        self._store: dict[str, dict] = {}

    def upsert(self, data: dict) -> dict:
        pid = data['property_id']
        if pid in self._store:
            self._store[pid].update(data)
            return self._store[pid]
        row = {**data, 'id': str(uuid4())}
        self._store[pid] = row
        return row

    def update_by_property_id(self, property_id: str, values: dict):
        if property_id in self._store:
            self._store[property_id].update(values)


class FakeDb:
    """Mimics supabase-py chain API, backed by in-memory tables."""

    def __init__(self):
        self.properties = FakePropertiesTable()
        self.leads = FakeLeadsTable()

    def table(self, name: str):
        return _FakeTableChain(self, name)


class _FakeTableChain:
    def __init__(self, db: FakeDb, name: str):
        self._db = db
        self._name = name
        self._query: dict = {}

    def select(self, cols: str):
        self._query['select'] = cols
        return self

    def eq(self, col, value):
        self._query.setdefault('where', []).append((col, value))
        return self

    def upsert(self, data, on_conflict=None):
        self._query['op'] = 'upsert'
        self._query['data'] = data
        return self

    def update(self, values):
        self._query['op'] = 'update'
        self._query['values'] = values
        return self

    def insert(self, data):
        self._query['op'] = 'insert'
        self._query['data'] = data
        return self

    def execute(self):
        resp = MagicMock()
        resp.data = []

        if self._name == 'properties':
            if self._query.get('op') == 'upsert':
                resp.data = [self._db.properties.upsert(self._query['data'], self._query.get('on_conflict'))]
            elif self._query.get('op') == 'update':
                # Find the property by id from 'where'
                wheres = dict(self._query.get('where', []))
                pid = wheres.get('id')
                if pid and pid in self._db.properties._by_id:
                    self._db.properties.update_by_id(pid, self._query['values'])
                    resp.data = [self._db.properties._by_id[pid]]
            else:
                # SELECT path
                wheres = dict(self._query.get('where', []))
                if 'normalized_address' in wheres and 'county_id' in wheres:
                    resp.data = self._db.properties.select_by_key(
                        wheres['county_id'], wheres['normalized_address'],
                    )
                elif 'id' in wheres:
                    resp.data = self._db.properties.select_by_id(wheres['id'])

        elif self._name == 'leads':
            if self._query.get('op') == 'upsert':
                resp.data = [self._db.leads.upsert(self._query['data'])]
            elif self._query.get('op') == 'insert':
                d = self._query['data']
                resp.data = [self._db.leads.upsert(d)]
            elif self._query.get('op') == 'update':
                wheres = dict(self._query.get('where', []))
                if 'property_id' in wheres:
                    self._db.leads.update_by_property_id(wheres['property_id'], self._query['values'])
                    resp.data = [self._db.leads._store.get(wheres['property_id'], {})]

        return resp


@pytest.fixture
def hcfl_county_id():
    return "00000000-0000-0000-0000-000000000001"


def _make_permit(permit_id: str, opened_date: str) -> dict:
    # Minimal permit-dict shape that process_permit() needs.
    return {
        'id': permit_id,
        'property_address': "1519 DALE MABRY HWY, Tampa, FL 33609",
        'opened_date': opened_date,
        'owner_name': "Test Owner",
        'owner_phone': None,
        'owner_email': None,
        'year_built': 1990,
        'property_value': 350000,
        'raw_data': {'source': 'test'},
    }


# Three permits for one address. B is the NEWEST, so final state
# must always reflect B's date regardless of processing order.
PERMIT_A = _make_permit("permit-A", "2015-06-15")  # 10-ish years old
PERMIT_B = _make_permit("permit-B", "2024-03-01")  # recent replacement (WINNER)
PERMIT_C = _make_permit("permit-C", "2020-09-10")  # middle


async def _process_permits_in_order(
    aggregator: PropertyAggregator,
    permits: list[dict],
    county_id: str,
):
    for p in permits:
        await aggregator.process_permit(p, county_id)


def _extract_final_state(db: FakeDb) -> dict:
    """Snapshot the final property state as a comparison-ready dict."""
    properties = list(db.properties._store.values())
    assert len(properties) == 1, f"Expected 1 property, got {len(properties)}"
    prop = properties[0]
    # Only compare invariant fields — exclude timestamps etc.
    return {
        'normalized_address': prop['normalized_address'],
        'most_recent_hvac_date': prop.get('most_recent_hvac_date'),
        'most_recent_hvac_permit_id': prop.get('most_recent_hvac_permit_id'),
        'total_hvac_permits': prop.get('total_hvac_permits'),
        'hvac_age_years': prop.get('hvac_age_years'),
        'lead_tier': prop.get('lead_tier'),
        'is_qualified': prop.get('is_qualified'),
    }


class TestLoadOrderIndependence:
    """The critical test: all 6 permutations of 3 permits yield the
    same final property state."""

    @pytest.mark.parametrize(
        "permutation",
        list(itertools.permutations([PERMIT_A, PERMIT_B, PERMIT_C])),
        ids=lambda p: "→".join(
            perm['id'] if isinstance(perm, dict) else str(perm) for perm in p
        ) if isinstance(p, tuple) else str(p),
    )
    async def test_all_permutations_yield_identical_state(
        self, permutation, hcfl_county_id,
    ):
        db = FakeDb()
        aggregator = PropertyAggregator(db=db)
        await _process_permits_in_order(aggregator, list(permutation), hcfl_county_id)
        state = _extract_final_state(db)
        # Winner: B (2024-03-01)
        assert state['most_recent_hvac_date'] == "2024-03-01"
        assert state['most_recent_hvac_permit_id'] == "permit-B"
        assert state['total_hvac_permits'] == 3
        # Scoring: a 2024 HVAC is <2 years old → COLD, not qualified
        # (FL-tuned: <4 years is COLD — see property_aggregator.TIER_THRESHOLDS)
        assert state['lead_tier'] == "COLD"
        assert state['is_qualified'] is False

    async def test_all_permutations_produce_byte_identical_state(self, hcfl_county_id):
        # Stronger: every permutation yields the same dict, not just a
        # few fields. Catches subtle drift in future.
        snapshots = []
        for perm in itertools.permutations([PERMIT_A, PERMIT_B, PERMIT_C]):
            db = FakeDb()
            aggregator = PropertyAggregator(db=db)
            await _process_permits_in_order(aggregator, list(perm), hcfl_county_id)
            snapshots.append(_extract_final_state(db))

        # All 6 snapshots must be identical
        for i, snap in enumerate(snapshots[1:], start=1):
            assert snap == snapshots[0], (
                f"Permutation {i} diverged from permutation 0:\n"
                f"  0: {snapshots[0]}\n"
                f"  {i}: {snap}"
            )


class TestSourceIndependence:
    """Load-order independence must also hold across permit SOURCES.
    One address might have an Accela API permit AND a legacy-scraper
    permit — the final aggregated state must be source-agnostic."""

    async def test_accela_then_scraper_vs_scraper_then_accela(self, hcfl_county_id):
        # Mark sources in raw_data so we can see they round-trip correctly.
        accela_permit = {**_make_permit("accela-1", "2024-03-01"),
                          'raw_data': {'source': 'accela_api'}}
        scraper_permit = {**_make_permit("scraper-1", "2015-06-15"),
                           'raw_data': {'source': 'hcfl_legacy_scraper'}}

        # Order 1: accela first, then scraper
        db1 = FakeDb()
        agg1 = PropertyAggregator(db=db1)
        await _process_permits_in_order(agg1, [accela_permit, scraper_permit], hcfl_county_id)

        # Order 2: scraper first, then accela
        db2 = FakeDb()
        agg2 = PropertyAggregator(db=db2)
        await _process_permits_in_order(agg2, [scraper_permit, accela_permit], hcfl_county_id)

        state1 = _extract_final_state(db1)
        state2 = _extract_final_state(db2)

        # Source order doesn't matter — newer date wins, counter is 2.
        assert state1 == state2
        assert state1['most_recent_hvac_date'] == "2024-03-01"
        assert state1['most_recent_hvac_permit_id'] == "accela-1"
        assert state1['total_hvac_permits'] == 2


class TestUserGrilledScenario:
    """The exact scenario the user described during the grill-me session,
    reproduced as a test to prevent regression."""

    async def test_10_year_old_permit_then_recent_replacement(self, hcfl_county_id):
        # Quoted: "...find an HVAC permit from 10 years ago. But we
        # don't look at what's replaced a month ago. It would appear
        # as though the HVAC is 10 years old, and that's just not the case."
        old_permit = _make_permit("old-10y", "2016-04-01")
        recent_permit = _make_permit("recent-1mo", "2026-03-22")  # ~1 month ago

        db = FakeDb()
        aggregator = PropertyAggregator(db=db)
        # Process OLD first (mimics scraper finding historical permits first)
        await _process_permits_in_order(
            aggregator, [old_permit, recent_permit], hcfl_county_id,
        )

        state = _extract_final_state(db)
        assert state['most_recent_hvac_date'] == "2026-03-22", (
            "User's explicit correctness requirement violated: "
            "aggregation must reflect the newer HVAC permit, not the older one"
        )
        # <1 yr old → COLD, NOT qualified (FL-tuned: 4+ yr qualification)
        assert state['hvac_age_years'] in (0, 1)
        assert state['lead_tier'] == "COLD"
        assert state['is_qualified'] is False

    async def test_recent_first_then_old_still_correct(self, hcfl_county_id):
        # Reverse order: the newer permit arrives BEFORE the older one
        # (mimics Accela API returning 2024 permits before the scraper
        # backfills the 2016 history).
        old_permit = _make_permit("old-10y", "2016-04-01")
        recent_permit = _make_permit("recent-1mo", "2026-03-22")

        db = FakeDb()
        aggregator = PropertyAggregator(db=db)
        await _process_permits_in_order(
            aggregator, [recent_permit, old_permit], hcfl_county_id,
        )

        state = _extract_final_state(db)
        # Still the 2026-03-22 date — the older permit only increments
        # the counter, does NOT overwrite the most-recent date.
        assert state['most_recent_hvac_date'] == "2026-03-22"
        assert state['total_hvac_permits'] == 2
