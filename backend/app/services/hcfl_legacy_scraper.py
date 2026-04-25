"""HCFL Legacy PermitReports scraper service.

Pulls historical HVAC permits (pre-2021) from HCFL's legacy web tool:
https://app.hillsboroughcounty.org/DevelopmentServices/PermitReports

Architecture:
  - Iterates street names from the hcfl_streets table (populated by
    scripts/build_hcfl_streets.py from TIGER/Line data).
  - For each street, runs a search (returns permit stubs).
  - Filters stubs by HVAC prefix (loaded from hcfl_hvac_prefixes.json).
  - Fetches detail for each HVAC permit.
  - Returns structured PermitDetail records the job processor can
    insert into the permits table with source='hcfl_legacy_scraper'.

Error convention:
  All methods return structured results on success and a dict with
  {"error": "..."} on expected HTTP failures. They never raise for
  expected conditions. Matches `accela_client.py` so the job
  processor handles both services identically.

Rate limiting:
  Polite fixed delay 400-600ms jittered, rolling 60 req/min cap,
  exponential backoff on 429/5xx. See `polite_rate_limiter.py`.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.services.hcfl_prefix_classifier import is_hvac_description
from app.services.polite_rate_limiter import PoliteRateLimiter

log = logging.getLogger(__name__)

BASE = "https://app.hillsboroughcounty.org/DevelopmentServices/PermitReports"
SEARCH_URL = f"{BASE}/Search/GetResults"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

SEARCH_TYPES_TO_TRY = ("Inspections", "LHNC", "Electrical")

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "hcfl_hvac_prefixes.json"


def load_hvac_prefixes(config_path: Path | None = None) -> list[str]:
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        log.warning("HVAC prefix config missing: %s — scraper would allowlist nothing.", path)
        return []
    data = json.loads(path.read_text())
    return list(data.get("hvac_prefixes", []))


@dataclass
class PermitStub:
    """Minimal info from a search-results row."""
    permit_number: str
    address: str
    street_searched: str

    @property
    def prefix(self) -> str | None:
        if len(self.permit_number) >= 3 and self.permit_number[:3].isalpha():
            return self.permit_number[:3].upper()
        return None


@dataclass
class PermitDetail:
    """Full permit data parsed from the detail page."""
    permit_number: str
    source_permit_id: str
    address: str | None
    description: str | None
    status: str | None
    opened_date: date | None
    parcel: str | None
    # Every extracted label:value pair, for debugging and future enrichment.
    raw_fields: dict[str, str] = field(default_factory=dict)
    # The search-type tab this detail was found under (Inspections vs LHNC...).
    search_type: str | None = None

    def to_permit_row(self, county_id: str) -> dict[str, Any]:
        # Shape a row ready for INSERT into the `permits` table.
        return {
            "county_id": county_id,
            "accela_record_id": self.permit_number,  # satisfy legacy UNIQUE
            "source": "hcfl_legacy_scraper",
            "source_permit_id": self.source_permit_id,
            "permit_type": self.raw_fields.get("Permit Type") or "Legacy HCFL Mechanical",
            "description": self.description,
            "status": self.status,
            "opened_date": self.opened_date.isoformat() if self.opened_date else None,
            "property_address": self.address,
            "parcel_number": _normalize_parcel(self.parcel),
            "raw_data": {
                "source": "hcfl_legacy_scraper",
                "permit_number": self.permit_number,
                "search_type": self.search_type,
                "parsed_fields": self.raw_fields,
            },
        }


# Labels we extract from the detail page, in the order they typically
# appear. The regex below anchors on these EXACT strings (case
# insensitive) to delimit value segments. This is more reliable than
# a generic "any Word:" pattern because HCFL pages contain many
# title-case phrases in addresses, footers, and inspection tables that
# would be mis-identified as labels.
_TARGET_LABELS = [
    "Project No.",
    "Description",
    "Address",
    "City",
    "Parcel",
    "Permit Issue Date",
    "Permit Status",
    "Permit Type",
    "Status",
    "Applied Date",
    "Project Name",
    "Applicant",
    "Owner",
    "Contractor",
    "Job Value",
]

_TARGET_LABEL_REGEX = re.compile(
    r"(?P<label>"
    + "|".join(re.escape(lbl) for lbl in _TARGET_LABELS)
    + r")\s*:\s*",
    re.IGNORECASE,
)

# Values for these short-ish fields get truncated at the first
# whitespace+uppercase-word boundary to avoid footer bleed.
# e.g. "CANCEL Date Inspection..." → "CANCEL"
_SINGLE_TOKEN_FIELDS = {"permit status", "status"}

# Footer tokens that commonly bleed into the last captured value.
# When we see one, truncate the value before it.
_FOOTER_STOPPERS_RE = re.compile(
    r"\s+(Date\s+Inspection|Inspector\s*/\s*Initial|Phone:|Driving\s+Directions"
    r"|Board\s+of\s+County|Contact\s+Us\b|The\s+mission)",
    re.IGNORECASE,
)

_DATE_PATTERNS = [
    ("%m/%d/%Y", re.compile(r"\b(\d{1,2}/\d{1,2}/\d{4})\b")),
    ("%m-%d-%Y", re.compile(r"\b(\d{1,2}-\d{1,2}-\d{4})\b")),
    ("%Y-%m-%d", re.compile(r"\b(\d{4}-\d{1,2}-\d{1,2})\b")),
]


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    for fmt, rx in _DATE_PATTERNS:
        m = rx.search(s)
        if m:
            try:
                return datetime.strptime(m.group(1), fmt).date()
            except ValueError:
                continue
    return None


def _normalize_parcel(p: str | None) -> str | None:
    # Reduce to alphanumeric uppercase so HCFL's "056362.0556" matches HCPAO's "0563620556".
    if not p:
        return None
    norm = ''.join(c for c in p.upper() if c.isalnum())
    return norm or None


class HcflLegacyScraper:
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        rate_limiter: PoliteRateLimiter | None = None,
        hvac_prefixes: list[str] | None = None,
    ):
        self._client = client  # injectable for tests
        self._owns_client = client is None
        self._rate_limiter = rate_limiter or PoliteRateLimiter()
        self._hvac_prefixes = set(hvac_prefixes) if hvac_prefixes is not None else set(load_hvac_prefixes())

    def _build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={
                "User-Agent": UA,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": BASE,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=30.0,
            follow_redirects=True,
        )

    async def __aenter__(self):
        if self._client is None:
            self._client = self._build_client()
        return self

    async def __aexit__(self, *exc_info):
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def hvac_prefixes(self) -> set[str]:
        return self._hvac_prefixes

    async def search_street(self, street: str) -> list[PermitStub] | dict[str, str]:
        if self._client is None:
            self._client = self._build_client()
            self._owns_client = True

        await self._rate_limiter.wait_before_request()

        try:
            resp = await self._client.get(
                SEARCH_URL,
                params={
                    "searchBy": "oStreet",
                    "searchTerm": street,
                    "searchType": "Inspections",
                },
            )
        except httpx.HTTPError as exc:
            log.warning("Search HTTP error for %s: %s", street, exc)
            return {"error": f"http_error: {exc!r}"}

        if resp.status_code in (429, 500, 502, 503, 504):
            log.warning("Search got %d for %s", resp.status_code, street)
            return {"error": f"http_{resp.status_code}"}

        if resp.status_code != 200:
            return {"error": f"http_{resp.status_code}"}

        try:
            return self.parse_search_results(resp.text, street)
        except Exception as exc:
            # Parser failures are NOT expected conditions — log loudly.
            log.exception("Parser crashed on search HTML for %s", street)
            return {"error": f"parser_crash: {exc!r}"}

    def parse_search_results(self, html: str, street: str) -> list[PermitStub]:
        soup = BeautifulSoup(html, "html.parser")
        stubs: list[PermitStub] = []
        for row in soup.select("table.results tbody tr"):
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            link = row.find("a")
            if not link:
                continue
            permit_number = link.get_text(strip=True)
            if not permit_number:
                continue
            address = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            stubs.append(
                PermitStub(
                    permit_number=permit_number,
                    address=address,
                    street_searched=street,
                )
            )
        return stubs

    def filter_hvac(self, stubs: list[PermitStub]) -> list[PermitStub]:
        if not self._hvac_prefixes:
            log.warning("No HVAC prefix allowlist — scraper would filter everything out.")
            return []
        return [s for s in stubs if s.prefix and s.prefix in self._hvac_prefixes]

    async def fetch_permit_detail(self, permit_number: str) -> PermitDetail | dict[str, str]:
        if self._client is None:
            self._client = self._build_client()
            self._owns_client = True

        last_error: str | None = None
        for search_type in SEARCH_TYPES_TO_TRY:
            await self._rate_limiter.wait_before_request()
            url = f"{BASE}/Permit/{permit_number}/{search_type}"
            try:
                resp = await self._client.get(url)
            except httpx.HTTPError as exc:
                last_error = f"http_error: {exc!r}"
                log.warning("Detail fetch error %s (%s): %s", permit_number, search_type, exc)
                continue

            if resp.status_code in (429, 500, 502, 503, 504):
                last_error = f"http_{resp.status_code}"
                log.warning("Detail got %d for %s (%s)", resp.status_code, permit_number, search_type)
                continue

            if resp.status_code != 200:
                last_error = f"http_{resp.status_code}"
                continue

            # HCFL returns 200 with "Your search returned 0 result(s)." for
            # wrong search-type tab. Detect and try next tab.
            if permit_number not in resp.text:
                last_error = "permit_not_found_in_tab"
                continue

            try:
                return self.parse_permit_detail(resp.text, permit_number, search_type)
            except Exception as exc:
                log.exception("Parser crashed on detail HTML for %s", permit_number)
                return {"error": f"parser_crash: {exc!r}"}

        return {"error": last_error or "not_found_in_any_search_type"}

    def parse_permit_detail(
        self,
        html: str,
        permit_number: str,
        search_type: str | None = None,
    ) -> PermitDetail:
        soup = BeautifulSoup(html, "html.parser")
        page_text = soup.get_text(" ", strip=True)

        raw_fields = self._extract_labeled_fields(page_text)

        address = raw_fields.get("Address") or None
        description = raw_fields.get("Description") or None
        status = raw_fields.get("Permit Status") or raw_fields.get("Status") or None
        parcel = raw_fields.get("Parcel") or None

        # Opened date: prefer Permit Issue Date; fall back to Applied Date.
        opened_date = (
            _parse_date(raw_fields.get("Permit Issue Date"))
            or _parse_date(raw_fields.get("Applied Date"))
        )

        return PermitDetail(
            permit_number=permit_number,
            source_permit_id=permit_number,
            address=address,
            description=description,
            status=status,
            opened_date=opened_date,
            parcel=parcel,
            raw_fields=raw_fields,
            search_type=search_type,
        )

    def _extract_labeled_fields(self, page_text: str) -> dict[str, str]:
        # Find every target-label match and capture the text until the
        # next target-label match starts. That value is then cleaned:
        #   - whitespace normalized
        #   - footer tokens (Phone:, Board of County, ...) stripped
        #   - Status-like fields truncated to their first capitalized word
        #   - hard cap at 300 chars to prevent runaway values
        matches = list(_TARGET_LABEL_REGEX.finditer(page_text))
        out: dict[str, str] = {}
        for i, m in enumerate(matches):
            # Canonicalize the matched label back to its TARGET form
            matched = m.group("label")
            # Case-insensitive lookup against _TARGET_LABELS for display
            canonical = next(
                (lbl for lbl in _TARGET_LABELS if lbl.lower() == matched.lower()),
                matched,
            )
            value_start = m.end()
            value_end = matches[i + 1].start() if i + 1 < len(matches) else len(page_text)
            raw_value = page_text[value_start:value_end].strip()
            raw_value = re.sub(r"\s+", " ", raw_value)

            # Strip footer content that bled into the last value.
            footer = _FOOTER_STOPPERS_RE.search(raw_value)
            if footer:
                raw_value = raw_value[: footer.start()].rstrip()

            # Single-token normalization for Status fields.
            if canonical.lower() in _SINGLE_TOKEN_FIELDS and raw_value:
                raw_value = raw_value.split()[0]

            # Hard cap
            if len(raw_value) > 300:
                raw_value = raw_value[:300].rstrip()

            # Store first hit; later duplicates are ignored
            if canonical not in out:
                out[canonical] = raw_value
        return out

    def is_hvac_permit(self, stub: PermitStub, detail: PermitDetail | None = None) -> bool:
        # Two-stage check: prefix allowlist (cheap) and, if we have detail,
        # description regex (safety net for mis-prefixed permits).
        if not stub.prefix or stub.prefix not in self._hvac_prefixes:
            return False
        if detail is None:
            return True
        return is_hvac_description(detail.description)
