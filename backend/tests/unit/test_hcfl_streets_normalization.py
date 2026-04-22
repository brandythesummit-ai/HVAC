"""Unit tests for HCFL street-name normalization.

normalize_street() is a correctness-critical function: the HCFL legacy
scraper iterates the output set, so false duplicates waste HTTP calls
and false uniques miss whole corridors of permits.
"""
import pytest

from app.services.hcfl_streets import TIGER_STREET_MTFCC, normalize_street


class TestNormalizeStreetBasic:
    def test_none_returns_none(self):
        assert normalize_street(None) is None

    def test_empty_string_returns_none(self):
        assert normalize_street("") is None

    def test_whitespace_only_returns_none(self):
        assert normalize_street("   ") is None

    def test_uppercases(self):
        assert normalize_street("kennedy") == "KENNEDY"

    def test_strips_leading_trailing_whitespace(self):
        assert normalize_street("  KENNEDY  ") == "KENNEDY"

    def test_collapses_internal_whitespace(self):
        assert normalize_street("DALE   MABRY") == "DALE MABRY"


class TestNormalizeStreetSuffixStripping:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("KENNEDY BLVD", "KENNEDY"),
            ("DALE MABRY HWY", "DALE MABRY"),
            ("N DALE MABRY HWY", "DALE MABRY"),  # leading directional stripped
            ("CHURCH ST", "CHURCH"),
            ("OAK STREET", "OAK"),
            ("MAIN AVE", "MAIN"),
            ("MAIN AV", "MAIN"),
            ("MAIN AVENUE", "MAIN"),
            ("NEBRASKA AVE", "NEBRASKA"),
            ("SOMETHING DRIVE", "SOMETHING"),
            ("BUSCH BLVD", "BUSCH"),
            ("BEACH TRAIL", "BEACH"),
            ("MOUNTAIN RIDGE", "MOUNTAIN"),
            ("HIDDEN COVE", "HIDDEN"),
            ("SUNSET PKWY", "SUNSET"),
        ],
    )
    def test_strips_common_suffixes(self, raw, expected):
        assert normalize_street(raw) == expected

    def test_lowercase_input_normalized_then_stripped(self):
        assert normalize_street("kennedy blvd") == "KENNEDY"

    def test_leading_directional_collapsed(self):
        # N/S/E/W prefixes collapse — HCFL substring search finds both
        # N and S branches when we search "DALE MABRY", so iterating
        # both wastes HTTP calls. Direction is recoverable from the
        # permit detail at ingest time.
        assert normalize_street("N KENNEDY BLVD") == "KENNEDY"
        assert normalize_street("S DALE MABRY HWY") == "DALE MABRY"
        assert normalize_street("E MAIN ST") == "MAIN"

    def test_trailing_directional_stripped(self):
        # TIGER FULLNAME often has post-directional: "N Teakwood Dr E"
        assert normalize_street("N TEAKWOOD DR E") == "TEAKWOOD"
        # "ROCKY POINT DR W" — W (directional) stripped, DR (type) stripped,
        # then POINT (type — we list PT/POINT) stripped. Result: "ROCKY".
        # HCFL substring search still finds permits under "ROCKY POINT DR"
        # because "ROCKY" is a substring.
        assert normalize_street("ROCKY POINT DR W") == "ROCKY"
        assert normalize_street("STERLING AVE W") == "STERLING"

    def test_iterative_strip_type_then_directional(self):
        assert normalize_street("OAK ST E") == "OAK"
        assert normalize_street("ELM RD NW") == "ELM"


class TestNormalizeStreetEdgeCases:
    def test_single_word_suffix_only(self):
        # "ST" alone — don't strip to empty string, preserve as-is.
        assert normalize_street("ST") == "ST"

    def test_suffix_in_middle_not_stripped(self):
        # "STREET VIEW" -> both tokens look like suffixes; iterative loop
        # strips VIEW (type), then STREET is alone so stops. Result: "STREET".
        # Loss of nuance acceptable — HCFL substring search still finds it.
        assert normalize_street("STREET VIEW") == "STREET"

    def test_multiple_suffixes_strip_iteratively(self):
        # "OAK HILL DRIVE" -> strip DRIVE (type), then HILL (also a type).
        # Result: "OAK". Intentional: reduces scraper iteration count.
        assert normalize_street("OAK HILL DRIVE") == "OAK"

    def test_hyphenated_names_preserved(self):
        # Hyphens aren't whitespace — treated as part of the token.
        assert normalize_street("MCKINLEY-ROOSEVELT RD") == "MCKINLEY-ROOSEVELT"

    def test_numeric_street_names(self):
        assert normalize_street("42ND AVE") == "42ND"
        assert normalize_street("101 ST") == "101"

    def test_mixed_case_suffix(self):
        assert normalize_street("Main St") == "MAIN"

    def test_tabs_and_other_whitespace(self):
        assert normalize_street("DALE\tMABRY\nHWY") == "DALE MABRY"


class TestNormalizeStreetRealWorldEdgeCases:
    """Lock in current behavior for patterns actually seen in TIGER / HCFL data."""

    def test_pure_numeric(self):
        assert normalize_street("1234") == "1234"

    def test_street_name_contains_no_stripable_tokens(self):
        # "BROKEN PIPE" is a real Tampa street; neither token is a type
        # or directional, so the name passes through unchanged.
        assert normalize_street("BROKEN PIPE") == "BROKEN PIPE"

    def test_mlk_jr_blvd(self):
        # Multi-word names with titles survive except for trailing type.
        assert normalize_street("MLK JR BLVD") == "MLK JR"

    def test_us_highway_naming(self):
        # TIGER FULLNAME often has "US HWY 41" — HWY isn't trailing so
        # it stays. Result preserves the highway designation.
        assert normalize_street("US HWY 41") == "US HWY 41"

    def test_state_route_naming(self):
        assert normalize_street("SR 60") == "SR 60"

    def test_ordinal_street_number_with_st_suffix(self):
        # "101 ST" is treated as ordinal "101st" by our stripper.
        # HCFL's substring search will still find permits on either form.
        # Documented tradeoff: we collapse "101st street" with "street #101".
        assert normalize_street("101 ST") == "101"


class TestNormalizeStreetIdempotency:
    @pytest.mark.parametrize(
        "raw",
        ["KENNEDY BLVD", "dale mabry hwy", "N DALE MABRY HWY", "OAK ST"],
    )
    def test_normalize_twice_stable(self, raw):
        # Calling normalize again on the output should produce the same
        # string (after the first call, there's no suffix left to strip).
        once = normalize_street(raw)
        twice = normalize_street(once)
        assert once == twice


class TestTigerStreetMtfcc:
    def test_includes_local_and_secondary(self):
        assert "S1400" in TIGER_STREET_MTFCC
        assert "S1200" in TIGER_STREET_MTFCC

    def test_excludes_interstates_and_trails(self):
        # S1100 = primary road (interstate), S1500 = vehicular trail,
        # S1630 = ramp, S1710 = walkway, S1740 = private drive.
        for excluded in ("S1100", "S1500", "S1630", "S1710", "S1740"):
            assert excluded not in TIGER_STREET_MTFCC
