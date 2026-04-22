"""Validation tests for the HVAC prefix allowlist artifact.

The M5 scraper imports the list from hcfl_hvac_prefixes.json. If that
file is malformed or missing required fields, the scraper silently
scrapes zero permits — a silent failure mode. Lock the shape in here.
"""
import json
from pathlib import Path

import pytest

CONFIG_PATH = Path(__file__).parent.parent.parent / "app" / "config" / "hcfl_hvac_prefixes.json"


@pytest.fixture(scope="module")
def config_data():
    assert CONFIG_PATH.exists(), f"Missing config file: {CONFIG_PATH}"
    return json.loads(CONFIG_PATH.read_text())


class TestHvacPrefixAllowlistShape:
    def test_has_required_top_level_keys(self, config_data):
        required = {"generated_at", "seed_streets", "max_samples_per_prefix",
                    "hvac_prefixes", "all_classifications"}
        assert required.issubset(config_data.keys())

    def test_review_needed_if_present_is_valid(self, config_data):
        # review_needed is optional in older artifacts; if present, validate.
        review = config_data.get("review_needed", [])
        assert isinstance(review, list)
        for p in review:
            assert isinstance(p, str)
            assert len(p) == 3 and p.isalpha() and p.isupper()
        # A prefix can't be both allowlisted and needing review.
        assert not (set(review) & set(config_data["hvac_prefixes"]))

    def test_hvac_prefixes_is_non_empty_list_of_strings(self, config_data):
        hvac = config_data["hvac_prefixes"]
        assert isinstance(hvac, list)
        assert len(hvac) > 0, "Empty allowlist — scraper would ingest nothing"
        for p in hvac:
            assert isinstance(p, str)
            assert len(p) == 3, f"Prefix not 3 chars: {p!r}"
            assert p.isupper(), f"Prefix not uppercase: {p!r}"
            assert p.isalpha(), f"Prefix has non-alpha chars: {p!r}"

    def test_allowlist_has_some_entries(self, config_data):
        # Weaker invariant than "NME must always be present" — HCFL may
        # retire prefixes over time. What we need to catch is the
        # silent-empty case where a broken classifier run wrote an
        # empty allowlist and the scraper ingests nothing.
        assert len(config_data["hvac_prefixes"]) >= 1

    def test_all_classifications_matches_allowlist(self, config_data):
        # Every prefix in hvac_prefixes must have an is_hvac=True entry
        # in all_classifications — keeps the two fields in sync.
        hvac_from_detail = {
            c["prefix"] for c in config_data["all_classifications"] if c["is_hvac"]
        }
        hvac_from_list = set(config_data["hvac_prefixes"])
        assert hvac_from_list == hvac_from_detail, (
            f"Drift between hvac_prefixes and classifications: "
            f"list_only={hvac_from_list - hvac_from_detail}, "
            f"detail_only={hvac_from_detail - hvac_from_list}"
        )

    def test_all_classifications_have_required_fields(self, config_data):
        for c in config_data["all_classifications"]:
            assert {"prefix", "sample_count", "hvac_matches",
                    "match_ratio", "is_hvac", "sample_descriptions"}.issubset(c.keys())

    def test_match_ratio_consistent_with_counts(self, config_data):
        for c in config_data["all_classifications"]:
            if c["sample_count"] == 0:
                assert c["match_ratio"] == 0.0
                continue
            expected = c["hvac_matches"] / c["sample_count"]
            # JSON rounds to 3 decimals — allow small diff
            assert abs(c["match_ratio"] - round(expected, 3)) < 0.002

    def test_seed_streets_is_non_empty(self, config_data):
        assert len(config_data["seed_streets"]) > 0
