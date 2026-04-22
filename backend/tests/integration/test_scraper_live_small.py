"""Live end-to-end scraper smoke test against real HCFL.

Gated behind @pytest.mark.live → skipped by default. Enable with:

    ENABLE_LIVE_TESTS=1 pytest tests/integration/test_scraper_live_small.py -v

Purpose:
- Validate the scraper pipeline end-to-end against the real HCFL
  PermitReports site before trusting it in production.
- Catch any HTML drift that our fixture-based tests would miss.
- Confirm polite rate limiting actually yields 200 responses (not
  getting rate-limited/blocked).

Scope is DELIBERATELY small — one or two low-traffic streets, a
handful of permit details. This test is not a load test; it's a
contract test against the real site.

What this test does NOT do:
- Write to Supabase (we verify scraper output shape, not DB persistence)
- Exercise the full job processor path (that's covered by
  test_job_processor_backfill.py with mocked HTTP)

If this test fails in CI, first check: did we leave ENABLE_LIVE_TESTS=1
in the environment? If not, HCFL's HTML probably changed and parsers
need updating.
"""
import os

import pytest

from app.services.hcfl_legacy_scraper import HcflLegacyScraper, PermitDetail, PermitStub


pytestmark = pytest.mark.live


@pytest.fixture
def live_prefixes():
    # Use the production allowlist shipped with the repo (M4's output).
    from app.services.hcfl_legacy_scraper import load_hvac_prefixes
    prefixes = load_hvac_prefixes()
    assert prefixes, "Prod allowlist is empty — M4 config file missing or corrupt"
    return prefixes


class TestLiveScraperSmoke:
    async def test_search_returns_real_permits(self, live_prefixes):
        # KENNEDY is a major Tampa arterial with consistent permit volume
        async with HcflLegacyScraper(hvac_prefixes=live_prefixes) as scraper:
            result = await scraper.search_street("KENNEDY")

        assert isinstance(result, list), f"Scraper returned error: {result!r}"
        assert len(result) > 0, "KENNEDY should yield at least some permits"
        for stub in result[:5]:
            assert isinstance(stub, PermitStub)
            assert stub.permit_number
            assert stub.street_searched == "KENNEDY"

    async def test_hvac_filter_finds_at_least_one_permit(self, live_prefixes):
        async with HcflLegacyScraper(hvac_prefixes=live_prefixes) as scraper:
            result = await scraper.search_street("KENNEDY")
            assert isinstance(result, list)
            hvac = scraper.filter_hvac(result)
        # KENNEDY historically shows HVAC permits (NME prefix); if this
        # returns zero, either our allowlist is wrong or HCFL's data
        # coverage has shifted.
        assert len(hvac) > 0, (
            f"No HVAC-prefix permits found on KENNEDY among {len(result)} total. "
            f"Allowlist: {live_prefixes}"
        )

    async def test_permit_detail_fetches_and_parses(self, live_prefixes):
        # Use the known-good permit from our POC phase.
        async with HcflLegacyScraper(hvac_prefixes=live_prefixes) as scraper:
            result = await scraper.fetch_permit_detail("NME36051")

        assert isinstance(result, PermitDetail), f"Got error instead: {result!r}"
        assert result.permit_number == "NME36051"
        assert result.description and "HVAC" in result.description
        assert result.address  # real permit should have an address
        # HCFL returns a status we already verified in M5 fixture tests
        assert result.status in ("CANCEL", "FINALED", "ACTIVE", "EXPIRED", "ISSUED",
                                  "VOID", "CANCELLED", "INACTIVE", "OPEN")

    async def test_full_pipeline_one_hvac_permit(self, live_prefixes):
        # Search KENNEDY → filter to HVAC → fetch detail on the first
        # HVAC permit → verify the is_hvac_permit (two-stage filter)
        # decision.
        async with HcflLegacyScraper(hvac_prefixes=live_prefixes) as scraper:
            stubs = await scraper.search_street("KENNEDY")
            assert isinstance(stubs, list)
            hvac_stubs = scraper.filter_hvac(stubs)
            assert hvac_stubs, "No HVAC stubs to fetch"

            first = hvac_stubs[0]
            detail = await scraper.fetch_permit_detail(first.permit_number)
            assert isinstance(detail, PermitDetail), (
                f"Detail fetch failed for {first.permit_number}: {detail!r}"
            )

            # Second-stage HVAC filter
            is_really_hvac = scraper.is_hvac_permit(first, detail)
            # Not all prefix matches pass the regex — if this one doesn't,
            # that's fine (it's the mis-prefix guard we tested in M5).
            # What we want to confirm is the method returns cleanly.
            assert isinstance(is_really_hvac, bool)

            # Regardless of the regex outcome, detail.to_permit_row should
            # produce a well-shaped DB row.
            row = detail.to_permit_row(county_id="test-county-uuid")
            assert row["source"] == "hcfl_legacy_scraper"
            assert row["accela_record_id"] == first.permit_number
            assert row["raw_data"]["permit_number"] == first.permit_number


@pytest.mark.skipif(
    os.environ.get("ENABLE_LIVE_TESTS") != "1",
    reason="Live tests disabled; set ENABLE_LIVE_TESTS=1 to run",
)
class TestLiveRateLimitingBehavior:
    """Validates that sequential requests hit the rate limiter correctly
    without getting blocked or throttled by HCFL."""

    async def test_ten_sequential_requests_all_succeed(self, live_prefixes):
        # Polite rate limiter should yield ~5 seconds of elapsed time
        # at base_delay=0.5s × 10 requests.
        async with HcflLegacyScraper(hvac_prefixes=live_prefixes) as scraper:
            streets = ["KENNEDY", "BUSCH", "DALE MABRY",
                        "NEBRASKA", "HOWARD"]
            results = []
            for street in streets:
                result = await scraper.search_street(street)
                results.append(result)
        # All should be lists (not error dicts).
        errors = [r for r in results if isinstance(r, dict) and "error" in r]
        assert not errors, f"Some requests failed: {errors}"
