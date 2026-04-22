"""HCFL street-name normalization.

Shared between scripts/build_hcfl_streets.py (populates the hcfl_streets
table from TIGER/Line data) and the HCFL legacy scraper (M5), which
uses the same normalized form to iterate and query HCFL's legacy search.

The normalized form collapses cosmetic variations so the scraper's
iteration list is minimal without losing coverage:
  - Strips trailing street-type suffixes (ST, AVE, BLVD, ...) because
    HCFL's legacy PermitReports search is a substring-match, so
    "DALE MABRY" matches records with "DALE MABRY HWY" and variants.
  - Strips trailing AND leading directionals (N/S/E/W) because HCFL's
    substring search finds "N DALE MABRY" and "S DALE MABRY" when we
    search "DALE MABRY" — halving the HTTP call count with no coverage
    loss. The permit detail response has the full address so direction
    is recoverable at ingest time.
"""
from __future__ import annotations

import re

# Common street-type suffixes. Leaving the list broad: over-stripping
# just means the scraper iteration list is a bit smaller (conservative
# wrt coverage because HCFL's search is substring-match, not exact).
_STREET_TYPE_SUFFIXES = {
    "ST", "STREET",
    "AVE", "AV", "AVENUE",
    "BLVD", "BL", "BOULEVARD",
    "RD", "ROAD",
    "HWY", "HIGHWAY",
    "DR", "DRIVE",
    "LN", "LANE",
    "PL", "PLACE",
    "CT", "COURT",
    "WAY",
    "CIR", "CIRCLE",
    "TER", "TERR", "TERRACE",
    "PKWY", "PARKWAY",
    "TRL", "TRAIL",
    "PATH",
    "LOOP",
    "ALY", "ALLEY",
    "EXPY", "EXPRESSWAY",
    "FWY", "FREEWAY",
    "RUN",
    "WALK",
    "XING", "CROSSING",
    "SQ", "SQUARE",
    "CV", "COVE",
    "RDG", "RIDGE",
    "MDW", "MEADOW",
    "GRV", "GROVE",
    "PT", "POINT",
    "HTS", "HEIGHTS",
    "VW", "VIEW",
    "BND", "BEND",
    "KNL", "KNOLL",
    "HOL", "HOLLOW",
    "HL", "HILL",
}

_DIRECTIONAL_TOKENS = {
    "N", "S", "E", "W",
    "NE", "NW", "SE", "SW",
    "NORTH", "SOUTH", "EAST", "WEST",
    "NORTHEAST", "NORTHWEST", "SOUTHEAST", "SOUTHWEST",
}

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_street(raw: str | None) -> str | None:
    """Normalize a raw street name for HCFL legacy scraper iteration.

    Returns None for empty / whitespace-only input.

    The algorithm preserves multi-token cores:
      "N Teakwood Dr E" -> "N TEAKWOOD DR E"
         -> strip trailing "E" (directional) -> "N TEAKWOOD DR"
         -> strip trailing "DR" (type)       -> "N TEAKWOOD"
         -> strip leading "N" (directional)  -> "TEAKWOOD"
      "DALE MABRY HWY" -> "DALE MABRY HWY" -> "DALE MABRY"
      "N DALE MABRY HWY" -> "DALE MABRY"
      "CHURCH ST" -> "CHURCH"
      "ST" -> "ST" (only one token; don't strip to empty)
    """
    if raw is None:
        return None
    cleaned = _WHITESPACE_RE.sub(" ", raw.strip().upper())
    if not cleaned:
        return None

    tokens = cleaned.split(" ")

    # Iteratively strip trailing directional or type tokens until the
    # core is reached. Never strip down to zero tokens.
    while len(tokens) > 1 and (
        tokens[-1] in _DIRECTIONAL_TOKENS or tokens[-1] in _STREET_TYPE_SUFFIXES
    ):
        tokens.pop()

    # Strip a single leading directional if it's a prefix on a multi-token name.
    if len(tokens) > 1 and tokens[0] in _DIRECTIONAL_TOKENS:
        tokens.pop(0)

    return " ".join(tokens)


# MTFCC (MAF/TIGER Feature Class Code) values for streets we want to
# enumerate. Target: local streets and secondary roads. Excludes
# interstates, ramps, trails, private drives, pedestrian paths, etc.
TIGER_STREET_MTFCC = {
    "S1200",  # Secondary Road (US Hwy, State Hwy, County Hwy)
    "S1400",  # Local Neighborhood Road, Rural Road, City Street
}
