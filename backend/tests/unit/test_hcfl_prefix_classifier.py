"""Unit tests for the HCFL prefix HVAC classifier.

The classifier is correctness-critical: it decides which permit
prefixes the scraper ingests. False negatives drop whole categories
of HVAC work from the lead pipeline.
"""
import pytest

from app.services.hcfl_prefix_classifier import (
    HVAC_PREFIX_THRESHOLD,
    classify_prefix,
    is_hvac_description,
)


class TestIsHvacDescription:
    @pytest.mark.parametrize(
        "text",
        [
            "HVAC equal change out 3 ton Straight Cool system with 10 kw",
            "Heat Pump Replacement",
            "HEAT PUMP REPLACEMENT",
            "HEATPUMP changeout",
            "A/C change out",
            "a/c unit replacement",
            "A.C. condenser replacement",
            "AIR CONDITIONER installation",
            "Air-Conditioner Replacement",
            "Furnace Replacement",
            "Install condenser unit",
            "Replace compressor",
            "Coil change-out",
            "Ductless mini-split install",
            "MINI SPLIT system",
            "Split System Replacement",
            "MECHANICAL PERMIT",
            "Install new cooling system",
            "Residential heating replacement",
            "Fan coil replacement",
            "Evaporator coil replacement",
            # Bug fixes from M4 code review:
            "replace A/C",  # end-of-line A/C
            "replace A/C.",  # A/C period at end
            "replace AC",  # compact AC
            "Install AHU on roof",  # air handler unit abbreviation
            "RTU replacement",  # rooftop unit
            "Rooftop A/C replacement",  # rooftop A/C
            "Ductwork replacement",
            "Duct replacement",
            "New air handler",
            "Condensing unit replacement",
            "refrigeration system replacement",
            "C/O HVAC system",  # change-out shorthand with HVAC
            "C/O A/C unit",  # change-out shorthand with A/C
        ],
    )
    def test_classifies_hvac_terms_as_hvac(self, text):
        assert is_hvac_description(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            "Roof replacement",
            "Install shingles",
            "New pool screen enclosure",
            "Gas line installation",
            "Water heater replacement",
            "Garage door installation",
            "Fence installation",
            "Window replacement",
            "Solar panel install",
            "Electrical panel upgrade",
            "Siding replacement",
            "",
            None,
            "   ",
        ],
    )
    def test_classifies_non_hvac_as_non_hvac(self, text):
        assert is_hvac_description(text) is False

    def test_water_heater_not_counted_as_heater(self):
        # "HEATING" and "HEATER" can be ambiguous. Our regex keys on
        # "HEATING" (not "HEATER"), so "water heater replacement" stays
        # non-HVAC. Lock this in.
        assert is_hvac_description("water heater replacement") is False


class TestClassifyPrefix:
    def test_all_hvac_samples_marks_prefix_hvac(self):
        descs = [
            "HVAC change out",
            "Heat Pump replacement",
            "AC compressor replacement",
        ]
        result = classify_prefix("NME", descs)
        assert result.is_hvac is True
        assert result.hvac_matches == 3
        assert result.sample_count == 3
        assert result.match_ratio == 1.0

    def test_no_hvac_samples_marks_prefix_non_hvac(self):
        descs = ["Roof replacement", "New shingles", "Gutter install"]
        result = classify_prefix("RFG", descs)
        assert result.is_hvac is False
        assert result.hvac_matches == 0
        assert result.match_ratio == 0.0

    def test_threshold_inclusive(self):
        # Exactly HVAC_PREFIX_THRESHOLD (50%) should be classified as HVAC.
        descs = ["HVAC install", "Install fence"]  # 1/2 = 0.5
        result = classify_prefix("MIX", descs)
        assert result.match_ratio == HVAC_PREFIX_THRESHOLD
        assert result.is_hvac is True

    def test_below_threshold_non_hvac(self):
        descs = ["HVAC install", "fence", "fence", "fence"]  # 1/4 = 0.25
        result = classify_prefix("FNC", descs)
        assert result.match_ratio == 0.25
        assert result.is_hvac is False

    def test_empty_samples_returns_non_hvac(self):
        result = classify_prefix("???", [])
        assert result.is_hvac is False
        assert result.sample_count == 0

    def test_none_values_skipped(self):
        descs = [None, "HVAC", None, "HVAC"]
        result = classify_prefix("XYZ", descs)
        assert result.sample_count == 2  # Nones skipped
        assert result.hvac_matches == 2
        assert result.is_hvac is True

    def test_as_dict_serializable(self):
        descs = ["HVAC change out"]
        result = classify_prefix("NME", descs)
        d = result.as_dict()
        assert d["prefix"] == "NME"
        assert d["is_hvac"] is True
        assert isinstance(d["sample_descriptions"], list)
        # match_ratio rounded to 3 decimals for JSON serialization stability
        assert isinstance(d["match_ratio"], float)

    def test_sample_descriptions_truncated_to_5(self):
        descs = ["HVAC " + str(i) for i in range(20)]
        result = classify_prefix("NME", descs)
        assert len(result.sample_descriptions) == 5
        # Each trimmed to 100 chars
        for d in result.sample_descriptions:
            assert len(d) <= 100

    def test_long_description_truncated(self):
        descs = ["HVAC " + ("X" * 500)]
        result = classify_prefix("NME", descs)
        assert len(result.sample_descriptions[0]) == 100
