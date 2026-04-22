"""HTTP-client-level tests for HcflLegacyScraper.

Uses pytest-httpx to mock HCFL endpoints. Exercises:
  - error-return convention (dicts, never raises for expected failures)
  - search → filter → fetch flow
  - search-type-tab fallback when first tab has no match
  - rate limiter integration (minimal — full tests live in polite_rate_limiter)
"""
from pathlib import Path

import httpx
import pytest

from app.services.hcfl_legacy_scraper import BASE, HcflLegacyScraper, PermitStub
from app.services.polite_rate_limiter import PoliteRateLimiter

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "hcfl_html"


def _load(name: str) -> str:
    return (FIXTURE_DIR / name).read_text()


@pytest.fixture
def fast_rate_limiter():
    # Nearly no-op rate limiter for speed in unit tests.
    return PoliteRateLimiter(base_delay_s=0.0, jitter_fraction=0.0, max_per_minute=10000)


@pytest.fixture
async def scraper(fast_rate_limiter):
    s = HcflLegacyScraper(hvac_prefixes=["NME", "NMC", "FCM"], rate_limiter=fast_rate_limiter)
    async with s:
        yield s


class TestSearchStreet:
    async def test_successful_search_returns_stubs(self, scraper, httpx_mock):
        httpx_mock.add_response(
            url=f"{BASE}/Search/GetResults?searchBy=oStreet&searchTerm=KENNEDY&searchType=Inspections",
            text=_load("search_kennedy_inspections.html"),
            status_code=200,
        )
        result = await scraper.search_street("KENNEDY")
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(s, PermitStub) for s in result)

    async def test_500_returns_error_dict(self, scraper, httpx_mock):
        httpx_mock.add_response(
            url=f"{BASE}/Search/GetResults?searchBy=oStreet&searchTerm=STREET&searchType=Inspections",
            status_code=500,
        )
        result = await scraper.search_street("STREET")
        assert isinstance(result, dict)
        assert result["error"] == "http_500"

    async def test_connection_error_returns_error_dict(self, scraper, httpx_mock):
        httpx_mock.add_exception(httpx.ConnectTimeout("test timeout"))
        result = await scraper.search_street("STREET")
        assert isinstance(result, dict)
        assert "http_error" in result["error"]

    async def test_parser_crash_returns_error_dict(self, scraper, httpx_mock, monkeypatch):
        httpx_mock.add_response(
            url=f"{BASE}/Search/GetResults?searchBy=oStreet&searchTerm=X&searchType=Inspections",
            text="<html></html>",
            status_code=200,
        )

        def _boom(*a, **kw):
            raise RuntimeError("test parser crash")
        monkeypatch.setattr(scraper, "parse_search_results", _boom)
        result = await scraper.search_street("X")
        assert isinstance(result, dict)
        assert "parser_crash" in result["error"]


class TestFetchPermitDetail:
    async def test_found_in_first_tab_returns_detail(self, scraper, httpx_mock):
        httpx_mock.add_response(
            url=f"{BASE}/Permit/NME36051/Inspections",
            text=_load("permit_nme36051.html"),
            status_code=200,
        )
        from app.services.hcfl_legacy_scraper import PermitDetail
        result = await scraper.fetch_permit_detail("NME36051")
        assert isinstance(result, PermitDetail)
        assert result.permit_number == "NME36051"
        assert result.search_type == "Inspections"

    async def test_falls_back_to_next_tab(self, scraper, httpx_mock):
        # Inspections returns 200 but without the permit number in HTML
        # → scraper tries LHNC next.
        httpx_mock.add_response(
            url=f"{BASE}/Permit/NME36051/Inspections",
            text="<html>Your search returned 0 result(s).</html>",
            status_code=200,
        )
        httpx_mock.add_response(
            url=f"{BASE}/Permit/NME36051/LHNC",
            text=_load("permit_nme36051.html"),
            status_code=200,
        )
        result = await scraper.fetch_permit_detail("NME36051")
        from app.services.hcfl_legacy_scraper import PermitDetail
        assert isinstance(result, PermitDetail)
        assert result.search_type == "LHNC"

    async def test_not_found_in_any_tab_returns_error(self, scraper, httpx_mock):
        for st in ("Inspections", "LHNC", "Electrical"):
            httpx_mock.add_response(
                url=f"{BASE}/Permit/DOESNOTEXIST/{st}",
                text="<html>not here</html>",
                status_code=200,
            )
        result = await scraper.fetch_permit_detail("DOESNOTEXIST")
        assert isinstance(result, dict)
        assert result["error"] == "permit_not_found_in_tab"

    async def test_500_on_all_tabs_returns_error(self, scraper, httpx_mock):
        for st in ("Inspections", "LHNC", "Electrical"):
            httpx_mock.add_response(
                url=f"{BASE}/Permit/X/{st}",
                status_code=500,
            )
        result = await scraper.fetch_permit_detail("X")
        assert isinstance(result, dict)
        assert result["error"] == "http_500"


class TestLoadHvacPrefixes:
    def test_loads_config_file(self):
        # Real config shipped in M4; verify integration with real file.
        from app.services.hcfl_legacy_scraper import load_hvac_prefixes
        prefixes = load_hvac_prefixes()
        assert "NME" in prefixes
        assert all(len(p) == 3 and p.isupper() for p in prefixes)

    def test_missing_config_returns_empty(self, tmp_path):
        from app.services.hcfl_legacy_scraper import load_hvac_prefixes
        result = load_hvac_prefixes(tmp_path / "missing.json")
        assert result == []
