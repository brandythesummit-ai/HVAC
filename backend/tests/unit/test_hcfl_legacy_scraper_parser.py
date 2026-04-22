"""Parser tests for HcflLegacyScraper. Offline, fixture-based — no HTTP."""
from datetime import date
from pathlib import Path

import pytest

from app.services.hcfl_legacy_scraper import HcflLegacyScraper, PermitStub

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "hcfl_html"


def _load(name: str) -> str:
    return (FIXTURE_DIR / name).read_text()


@pytest.fixture
def scraper():
    # Injected hvac_prefixes avoids reading config in unit tests.
    return HcflLegacyScraper(hvac_prefixes=["FCM", "NMC", "NME"])


class TestParseSearchResults:
    def test_parses_kennedy_search(self, scraper):
        html = _load("search_kennedy_inspections.html")
        stubs = scraper.parse_search_results(html, "KENNEDY")
        # KENNEDY search returned ~113 rows in live probe
        assert len(stubs) > 50, f"Too few stubs: {len(stubs)}"
        for s in stubs:
            assert isinstance(s.permit_number, str)
            assert s.permit_number  # non-empty
            assert s.street_searched == "KENNEDY"

    def test_empty_results_page_returns_empty_list(self, scraper):
        html = _load("search_no_results.html")
        stubs = scraper.parse_search_results(html, "DOESNOTEXIST999")
        assert stubs == []

    def test_parses_malformed_html_gracefully(self, scraper):
        # Missing table, unclosed tags, etc. — should return [], not crash.
        html = "<html><body><p>Error occurred</p></body></html>"
        stubs = scraper.parse_search_results(html, "ANY")
        assert stubs == []

    def test_extracted_permit_numbers_look_valid(self, scraper):
        html = _load("search_kennedy_inspections.html")
        stubs = scraper.parse_search_results(html, "KENNEDY")
        # Real HCFL permit numbers are alphanumeric and 6-15 chars
        for s in stubs[:20]:
            assert 3 <= len(s.permit_number) <= 20


class TestParsePermitDetail:
    def test_parses_nme36051_correctly(self, scraper):
        html = _load("permit_nme36051.html")
        detail = scraper.parse_permit_detail(html, "NME36051", search_type="Inspections")
        assert detail.permit_number == "NME36051"
        assert detail.source_permit_id == "NME36051"
        assert "HVAC" in (detail.description or "")
        assert "change out" in (detail.description or "").lower()
        # Address known from live probe
        assert detail.address and "DALE MABRY" in detail.address
        # Status was CANCEL per live page
        assert detail.status == "CANCEL"
        assert detail.search_type == "Inspections"

    def test_raw_fields_dict_populated(self, scraper):
        html = _load("permit_nme36051.html")
        detail = scraper.parse_permit_detail(html, "NME36051")
        assert "Description" in detail.raw_fields
        assert "Address" in detail.raw_fields
        assert detail.raw_fields["Description"].startswith("HVAC")


class TestPermitStubPrefix:
    @pytest.mark.parametrize(
        "permit_number,expected_prefix",
        [
            ("NME36051", "NME"),
            ("nme36051", "NME"),  # uppercase
            ("FCM01046", "FCM"),
            ("21060178-H", None),  # digit-first legacy format
            ("AB", None),  # too short
            ("", None),
        ],
    )
    def test_prefix_extraction(self, permit_number, expected_prefix):
        stub = PermitStub(permit_number=permit_number, address="", street_searched="")
        assert stub.prefix == expected_prefix


class TestFilterHvac:
    def test_allowlists_hvac_prefix_permits(self, scraper):
        stubs = [
            PermitStub(permit_number="NME36051", address="", street_searched="KENNEDY"),
            PermitStub(permit_number="RFG70206", address="", street_searched="KENNEDY"),  # roof
            PermitStub(permit_number="NMC01234", address="", street_searched="KENNEDY"),
            PermitStub(permit_number="FCM99999", address="", street_searched="KENNEDY"),
            PermitStub(permit_number="XYZ11111", address="", street_searched="KENNEDY"),
        ]
        filtered = scraper.filter_hvac(stubs)
        assert {s.permit_number for s in filtered} == {"NME36051", "NMC01234", "FCM99999"}

    def test_empty_allowlist_returns_empty(self):
        scraper = HcflLegacyScraper(hvac_prefixes=[])
        stubs = [PermitStub(permit_number="NME36051", address="", street_searched="K")]
        # Empty allowlist → defensive: return nothing, not everything.
        assert scraper.filter_hvac(stubs) == []

    def test_digit_first_permits_excluded(self, scraper):
        stubs = [PermitStub(permit_number="21060178-H", address="", street_searched="K")]
        # No alpha prefix → can't classify → excluded (safer than including).
        assert scraper.filter_hvac(stubs) == []


class TestParseDate:
    def test_mdy_slashes(self, scraper):
        html = "Permit Issue Date: 03/15/2018 Permit Status: ACTIVE"
        # Feed the fragment in as a full page to the labeled-field extractor
        detail = scraper.parse_permit_detail(f"<html><body>{html}</body></html>", "X")
        assert detail.opened_date == date(2018, 3, 15)

    def test_missing_date_returns_none(self, scraper):
        html = "<html><body>Permit Issue Date:  Permit Status: CANCEL</body></html>"
        detail = scraper.parse_permit_detail(html, "X")
        assert detail.opened_date is None


class TestIsHvacPermit:
    def test_hvac_prefix_and_hvac_description(self, scraper):
        stub = PermitStub(permit_number="NME36051", address="", street_searched="K")
        from app.services.hcfl_legacy_scraper import PermitDetail
        detail = PermitDetail(
            permit_number="NME36051",
            source_permit_id="NME36051",
            address=None,
            description="HVAC change out",
            status=None,
            opened_date=None,
            parcel=None,
        )
        assert scraper.is_hvac_permit(stub, detail) is True

    def test_hvac_prefix_but_non_hvac_description(self, scraper):
        # Mis-prefixed permit: NME but description is roof work.
        stub = PermitStub(permit_number="NME99999", address="", street_searched="K")
        from app.services.hcfl_legacy_scraper import PermitDetail
        detail = PermitDetail(
            permit_number="NME99999",
            source_permit_id="NME99999",
            address=None,
            description="Roof replacement",
            status=None,
            opened_date=None,
            parcel=None,
        )
        # Safety net: regex at ingest time rejects.
        assert scraper.is_hvac_permit(stub, detail) is False

    def test_non_hvac_prefix(self, scraper):
        stub = PermitStub(permit_number="RFG70206", address="", street_searched="K")
        assert scraper.is_hvac_permit(stub, None) is False

    def test_no_detail_allows_hvac_prefix_through(self, scraper):
        stub = PermitStub(permit_number="NME36051", address="", street_searched="K")
        # Without detail we can only check prefix. Pass it through; ingest
        # will re-check once detail is fetched.
        assert scraper.is_hvac_permit(stub, None) is True


class TestToPermitRow:
    def test_shapes_db_row_correctly(self, scraper):
        html = _load("permit_nme36051.html")
        detail = scraper.parse_permit_detail(html, "NME36051", search_type="Inspections")
        row = detail.to_permit_row(county_id="test-county-uuid")
        assert row["county_id"] == "test-county-uuid"
        assert row["source"] == "hcfl_legacy_scraper"
        assert row["source_permit_id"] == "NME36051"
        assert row["accela_record_id"] == "NME36051"  # satisfies legacy UNIQUE
        assert "HVAC" in (row["description"] or "")
        assert row["raw_data"]["source"] == "hcfl_legacy_scraper"
        assert row["raw_data"]["search_type"] == "Inspections"
        assert "parsed_fields" in row["raw_data"]
