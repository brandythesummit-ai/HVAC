"""Discover and classify HCFL legacy permit prefixes as HVAC or not.

Queries HCFL's legacy PermitReports search for each seed street, groups
every resulting permit by its 3-letter prefix, then fetches a handful
of permit detail pages per prefix to get description text. Each
prefix's descriptions are fed to the classifier (is_hvac_description /
classify_prefix) and an allowlist is written to
`backend/app/config/hcfl_hvac_prefixes.json`.

Why this exists: HCFL uses codes like NME, RFG, MCH, GAS, ROF, NEL.
Only some of those are HVAC. The M5 scraper uses the resulting
allowlist to skip non-HVAC permits at the search-response level
(cheap filter) and then double-checks at detail-ingest time via the
regex (safety net for mis-prefixed permits).

Usage:
    cd backend && source venv/bin/activate
    python -m scripts.classify_hvac_prefixes [--streets KENNEDY,DALE,BUSCH]

The script is polite (400-600ms jittered delay between HTTP calls)
and idempotent (re-running overwrites the JSON with fresh results).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.hcfl_prefix_classifier import classify_prefix  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("classify_hvac_prefixes")

BASE = "https://app.hillsboroughcounty.org/DevelopmentServices/PermitReports"
SEARCH_URL = f"{BASE}/Search/GetResults"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# Streets with known HVAC-heavy activity; spans residential + commercial
# corridors so we observe a broad prefix distribution.
DEFAULT_SEED_STREETS = [
    "KENNEDY",
    "DALE MABRY",
    "NEBRASKA",
    "BUSCH",
    "HOWARD",
    "HARBOUR ISLAND",
    "BAYSHORE",
    "COLUMBUS",
    "HILLSBOROUGH",
    "LINEBAUGH",
]

# At most this many permit detail pages per prefix. Keeps the run time
# bounded and the classifier needs only 3-5 samples for a stable signal.
MAX_DETAILS_PER_PREFIX = 5


def polite_sleep():
    time.sleep(random.uniform(0.4, 0.6))


def build_client() -> httpx.Client:
    return httpx.Client(
        headers={
            "User-Agent": UA,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": BASE,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        timeout=30.0,
        follow_redirects=True,
    )


def search_street(client: httpx.Client, street: str) -> list[dict]:
    # Returns list of {permit_number, address} dicts.
    try:
        resp = client.get(
            SEARCH_URL,
            params={
                "searchBy": "oStreet",
                "searchTerm": street,
                "searchType": "Inspections",
            },
        )
    except httpx.HTTPError as exc:
        log.warning("Street search failed for %s: %s", street, exc)
        return []
    if resp.status_code != 200:
        log.warning("Street search %s returned HTTP %d", street, resp.status_code)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    out = []
    for row in soup.select("table.results tbody tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        link = row.find("a")
        if not link:
            continue
        out.append(
            {
                "permit_number": link.get_text(strip=True),
                "address": cells[1].get_text(strip=True),
            }
        )
    return out


def fetch_permit_description(client: httpx.Client, permit_number: str) -> str | None:
    # Try the most likely searchType tabs until one returns the permit.
    for st in ("Inspections", "LHNC", "Electrical"):
        url = f"{BASE}/Permit/{permit_number}/{st}"
        try:
            resp = client.get(url)
        except httpx.HTTPError as exc:
            log.debug("Detail fetch failed %s (%s): %s", permit_number, st, exc)
            continue
        if resp.status_code != 200 or permit_number not in resp.text:
            continue
        soup = BeautifulSoup(resp.text, "html.parser")
        page_text = soup.get_text(" ", strip=True)

        # Look for explicit Description label, then Permit Type, then h1/h2.
        # HCFL's page format varies by permit type.
        markers = [
            "Description:",
            "Description",
            "Permit Type:",
            "Work Description:",
            "Project Description:",
        ]
        for marker in markers:
            idx = page_text.lower().find(marker.lower())
            if idx >= 0:
                slice_ = page_text[idx + len(marker) : idx + len(marker) + 200]
                # Trim at the next all-caps label-ish token
                cleaned = slice_.strip(" :\n\t")
                if cleaned:
                    return cleaned
        # Fallback: page title-ish first header
        heading = soup.find(["h1", "h2", "h3"])
        if heading:
            return heading.get_text(strip=True)
    return None


def extract_prefix(permit_number: str) -> str | None:
    # "NME36051" -> "NME"; "21060178-H" -> None (legacy digit-first format
    # gets its own bucket handled by caller).
    if len(permit_number) < 3:
        return None
    head = permit_number[:3]
    if head.isalpha():
        return head.upper()
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--streets",
        default=None,
        help="Comma-separated street list. Default: built-in seed set.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path for the JSON allowlist. Default: backend/app/config/hcfl_hvac_prefixes.json",
    )
    parser.add_argument(
        "--max-per-prefix",
        type=int,
        default=MAX_DETAILS_PER_PREFIX,
        help=f"Max permit detail fetches per prefix (default {MAX_DETAILS_PER_PREFIX}).",
    )
    args = parser.parse_args()

    streets = (
        [s.strip() for s in args.streets.split(",") if s.strip()]
        if args.streets
        else DEFAULT_SEED_STREETS
    )
    output_path = Path(args.output) if args.output else (
        Path(__file__).parent.parent / "app" / "config" / "hcfl_hvac_prefixes.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    log.info("Seed streets: %s", streets)
    log.info("Max details per prefix: %d", args.max_per_prefix)

    # Phase 1: collect permits across streets
    permits_by_prefix: dict[str, list[str]] = defaultdict(list)
    with build_client() as client:
        for street in streets:
            log.info("Searching street: %s", street)
            results = search_street(client, street)
            log.info("  got %d permits", len(results))
            for r in results:
                prefix = extract_prefix(r["permit_number"])
                if prefix:
                    permits_by_prefix[prefix].append(r["permit_number"])
            polite_sleep()

        log.info(
            "Found %d unique prefixes across %d permits",
            len(permits_by_prefix),
            sum(len(v) for v in permits_by_prefix.values()),
        )
        for p, nums in sorted(permits_by_prefix.items(), key=lambda kv: -len(kv[1])):
            log.info("  prefix %s: %d permits (e.g. %s)", p, len(nums), nums[:3])

        # Phase 2: classify each prefix by fetching sample descriptions
        classifications = []
        for prefix, permit_nums in sorted(permits_by_prefix.items()):
            samples = permit_nums[: args.max_per_prefix]
            log.info("Classifying prefix %s (sampling %d permits)", prefix, len(samples))
            descriptions = []
            for num in samples:
                desc = fetch_permit_description(client, num)
                log.info("  %s -> %s", num, (desc[:80] if desc else "<no description>"))
                descriptions.append(desc)
                polite_sleep()
            result = classify_prefix(prefix, descriptions)
            classifications.append(result)
            log.info(
                "  VERDICT: %s (%d/%d HVAC matches, ratio=%.2f)",
                "HVAC" if result.is_hvac else "NOT HVAC",
                result.hvac_matches,
                result.sample_count,
                result.match_ratio,
            )

    # Phase 3: persist results (fail loud on zero results to prevent
    # silent overwrite of a previously-working allowlist).
    hvac_prefixes = sorted(c.prefix for c in classifications if c.is_hvac)
    review_needed = sorted(
        c.prefix
        for c in classifications
        if not c.is_hvac and 0.2 <= c.match_ratio < 0.5
    )

    if len(classifications) == 0:
        log.error(
            "Zero prefixes classified — HCFL likely changed HTML or rate-limited. "
            "Refusing to overwrite %s.",
            output_path,
        )
        sys.exit(2)
    if not hvac_prefixes:
        log.error(
            "Zero HVAC prefixes identified across %d classifications — "
            "refusing to overwrite %s (would make scraper ingest nothing).",
            len(classifications),
            output_path,
        )
        sys.exit(3)

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "seed_streets": streets,
        "max_samples_per_prefix": args.max_per_prefix,
        "hvac_prefixes": hvac_prefixes,
        "review_needed": review_needed,  # borderline, below threshold — human check
        "all_classifications": [c.as_dict() for c in classifications],
    }
    # Atomic write: write to .tmp, then os.replace. Survives Ctrl-C / crash
    # without corrupting the committed artifact that M5's scraper loads.
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=False))
    os.replace(tmp_path, output_path)
    log.info("Allowlist written to %s", output_path)
    log.info("HVAC prefixes: %s", hvac_prefixes)
    if review_needed:
        log.warning("Prefixes that need human review (ratio 0.2-0.5): %s", review_needed)


if __name__ == "__main__":
    main()
