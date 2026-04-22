"""Classify HCFL legacy permit prefixes as HVAC-related or not.

HCFL's legacy PermitReports tool issues 3-letter prefixes like `NME`,
`RFG`, `MCH`, `GAS`, etc. The M5 scraper filters permits by prefix to
avoid ingesting non-HVAC permits (roofing, gas, electrical, ...).

This module provides:
  - HVAC_DESCRIPTION_RE: the regex the scraper uses at ingest time to
    double-check that a permit with an HVAC-looking prefix really is
    HVAC (catches mis-prefixed edge cases).
  - is_hvac_description(text): boolean classifier on a permit's
    description field.
  - classify_prefix(samples): aggregate classifier — given N sample
    permit descriptions for a prefix, decide if the prefix is HVAC.

The resulting allowlist is persisted to
`backend/app/config/hcfl_hvac_prefixes.json` so the scraper and the
product layer share one source of truth.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

# Conservative HVAC keyword set. "HEAT PUMP" AND "A/C" are always HVAC.
# "FURNACE" captures gas furnaces. "CONDENSER" / "COMPRESSOR" / "COIL"
# capture component replacements. "MECHANICAL" is intentional overmatch
# — an HVAC permit often has "Mechanical Permit" or similar type text.
HVAC_DESCRIPTION_RE = re.compile(
    r"("
    r"\bHVAC\b"
    r"|\bHEAT\s*PUMP\b"
    r"|\bHEATPUMP\b"
    # Match "A/C", "A.C.", "A C", "AC" when bounded by word-boundaries.
    # Trailing char is optional so "replace A/C" at end of line matches.
    r"|\bA[/\.\s]?C\b"
    # AIR COND, AIR-CONDITIONING, AIR CONDITIONER — allow letters after COND
    r"|\bAIR[\s-]?COND[A-Z]*"
    # Air handler / AHU / fan coil / evaporator coil
    r"|\bAIR\s*HANDLER\b"
    r"|\bAHU\b"
    r"|\bFAN\s+COIL\b"
    r"|\bEVAPORATOR\b"
    # Rooftop unit / condensing unit (common in commercial HVAC)
    r"|\bRTU\b"
    r"|\bROOFTOP\s+UNIT\b"
    r"|\bROOF[\s-]?TOP\s+A[/\.\s]?C\b"
    r"|\bCONDENSING\s+UNIT\b"
    r"|\bCONDENSER\b"
    r"|\bCOMPRESSOR\b"
    r"|\bFURNACE\b"
    # Ductwork, refrigeration lines
    r"|\bDUCT(WORK)?\b"
    r"|\bREFRIGERATION\b"
    # Change-out phrasing (CHANGEOUT, CHANGE OUT, CHANGE-OUT, C/O)
    r"|\bCHANGE[\s-]?OUT\b"
    r"|\bC/O\s+(HVAC|A[/\.]?C|AIR|SYSTEM|UNIT|HEAT)"
    # Split systems
    r"|\bSPLIT[\s-]?SYSTEM\b"
    r"|\bMINI[\s-]?SPLIT\b"
    # Generic mechanical / cooling / heating verbs
    r"|\bMECHANICAL\b"
    r"|\bCOOLING\b"
    r"|\bHEATING\b"
    r")",
    re.IGNORECASE,
)


def is_hvac_description(text: str | None) -> bool:
    # Return True iff the description/type field suggests HVAC work.
    # False for None, empty, or non-HVAC text.
    if not text:
        return False
    return bool(HVAC_DESCRIPTION_RE.search(text))


@dataclass
class PrefixClassification:
    prefix: str
    sample_count: int
    hvac_matches: int
    match_ratio: float  # 0.0 - 1.0
    is_hvac: bool
    sample_descriptions: list[str]  # truncated for logging

    def as_dict(self) -> dict:
        return {
            "prefix": self.prefix,
            "sample_count": self.sample_count,
            "hvac_matches": self.hvac_matches,
            "match_ratio": round(self.match_ratio, 3),
            "is_hvac": self.is_hvac,
            "sample_descriptions": self.sample_descriptions[:5],
        }


HVAC_PREFIX_THRESHOLD = 0.5
# Reasoning: HCFL prefix codes are NOT strictly one-type-per-prefix;
# some prefixes mix change-outs with other work. Classifying HVAC at
# 50% match ratio errs on inclusion — better to ingest a few non-HVAC
# permits (filtered at description-regex time) than miss a whole
# corridor of HVAC work that happens to share a prefix.


def classify_prefix(
    prefix: str,
    descriptions: Iterable[str | None],
) -> PrefixClassification:
    descs = [d for d in descriptions if d]
    if not descs:
        return PrefixClassification(
            prefix=prefix,
            sample_count=0,
            hvac_matches=0,
            match_ratio=0.0,
            is_hvac=False,
            sample_descriptions=[],
        )
    hvac_count = sum(1 for d in descs if is_hvac_description(d))
    ratio = hvac_count / len(descs)
    return PrefixClassification(
        prefix=prefix,
        sample_count=len(descs),
        hvac_matches=hvac_count,
        match_ratio=ratio,
        is_hvac=ratio >= HVAC_PREFIX_THRESHOLD,
        sample_descriptions=[d[:100] for d in descs[:5]],
    )
