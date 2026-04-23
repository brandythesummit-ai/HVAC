"""Geocode property rows without coordinates.

Populates properties.latitude + properties.longitude by batching the
US Census geocoder — free, unlimited, US-government service.

Batch size: 10,000 per request (US Census batch API limit is 10k).
For 11,839 properties this runs in 2 batches, typically under 2 min.

Usage:
    cd backend && source venv/bin/activate
    python -m scripts.geocode_properties
        [--limit N]     # cap for testing
        [--dry-run]     # no writes
        [--retry-failed] # re-geocode properties where geocoded_at is set
                        # but latitude IS NULL (previous failures)

Idempotent: rows with geocoded_at already set are skipped by default.
Rows without geocoded_at are always retried.

Source: https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.pdf
Endpoint: /geocoder/locations/addressbatch
Response format: CSV, columns:
  Unique ID, Input Address, Match Flag, Match Type, Matched Address,
  Coordinates (lon,lat), TIGER Line ID, Side
"""
from __future__ import annotations

import argparse
import csv
import io
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("geocode_properties")

CENSUS_BATCH_URL = (
    "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
)
CENSUS_BATCH_SIZE = 10_000  # Census hard cap
BENCHMARK = "Public_AR_Current"


def fetch_ungeocoded_properties(client, limit: int | None = None, retry_failed: bool = False):
    # Supabase defaults to 1000 rows per request. Paginate with range()
    # until the server returns a short page (< PAGE_SIZE) indicating EOF.
    # Without pagination, this silently caps at 1000 and misses ~11K
    # properties in production.
    PAGE_SIZE = 1000
    out = []
    offset = 0
    while True:
        # county_id is NOT NULL on properties and PostgREST's upsert (even
        # when it will UPDATE on conflict) requires the full row to satisfy
        # INSERT constraints. We select it here so we can round-trip it into
        # the upsert payload.
        q = client.table("properties").select(
            "id, county_id, normalized_address, street_number, street_name, street_suffix, city, state, zip_code",
        )
        if retry_failed:
            q = q.is_("latitude", "null")
        else:
            q = q.is_("geocoded_at", "null")
        q = q.range(offset, offset + PAGE_SIZE - 1)
        resp = q.execute()
        chunk = resp.data or []
        out.extend(chunk)
        log.info("Fetched page offset=%d rows=%d (total so far %d)", offset, len(chunk), len(out))
        if len(chunk) < PAGE_SIZE:
            break
        if limit and len(out) >= limit:
            out = out[:limit]
            break
        offset += PAGE_SIZE
    return out


def build_address_line(prop: dict) -> str | None:
    # Prefer a structured address if we have the parts; fall back to normalized.
    parts = []
    if prop.get("street_number"):
        parts.append(str(prop["street_number"]))
    if prop.get("street_name"):
        parts.append(prop["street_name"])
    if prop.get("street_suffix"):
        parts.append(prop["street_suffix"])
    street = " ".join(parts) if parts else (prop.get("normalized_address") or "")
    return street.strip() or None


def run_census_batch(addresses: list[tuple[str, str, str, str, str]]) -> dict[str, dict]:
    """Send a batch to US Census, parse the CSV response.

    addresses: list of (id, street, city, state, zip)
    Returns {id: {"lat": float, "lng": float}} for matched rows.
    Unmatched rows are silently omitted.
    """
    # Build the CSV body. Census requires NO header row.
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in addresses:
        writer.writerow(row)
    csv_body = buf.getvalue()

    files = {"addressFile": ("input.csv", csv_body, "text/csv")}
    data = {"benchmark": BENCHMARK}

    log.info("POST %d addresses to Census batch geocoder", len(addresses))
    with httpx.Client(timeout=180.0) as client:
        resp = client.post(CENSUS_BATCH_URL, files=files, data=data)
        resp.raise_for_status()

    # Response is CSV with no header. Parse defensively — Census can
    # quote fields that contain commas.
    reader = csv.reader(io.StringIO(resp.text))
    results: dict[str, dict] = {}
    parsed = 0
    matched = 0
    for row in reader:
        parsed += 1
        if len(row) < 6:
            continue
        row_id, _input_addr, match_flag, _match_type, _matched_addr, coords = row[:6]
        if match_flag != "Match":
            continue
        # Coordinates like "-82.5,27.9"
        if not coords or "," not in coords:
            continue
        try:
            lng_s, lat_s = coords.split(",", 1)
            results[row_id] = {
                "lat": float(lat_s),
                "lng": float(lng_s),
            }
            matched += 1
        except (ValueError, IndexError):
            continue
    log.info("Census parsed %d rows, matched %d", parsed, matched)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv
        dotenv_path = Path(__file__).parent.parent / ".env"
        if dotenv_path.exists():
            load_dotenv(dotenv_path)
    except ImportError:
        log.debug("python-dotenv not installed; skipping .env autoload")

    from supabase import create_client
    sup_url = os.environ.get("SUPABASE_URL")
    sup_key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not sup_url or not sup_key:
        log.error("SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)
    client = create_client(sup_url, sup_key)

    log.info("Fetching ungeocoded properties (retry_failed=%s)…", args.retry_failed)
    properties = fetch_ungeocoded_properties(client, args.limit, args.retry_failed)
    log.info("Found %d properties to geocode", len(properties))
    if not properties:
        log.info("Nothing to do")
        return

    # Build Census rows. Census wants (id, street, city, state, zip).
    # Drop rows where we can't form an address line.
    index_to_prop: dict[str, dict] = {}
    batch: list[tuple[str, str, str, str, str]] = []
    for p in properties:
        street = build_address_line(p)
        if not street:
            continue
        row_id = p["id"]
        index_to_prop[row_id] = p
        batch.append((
            row_id,
            street,
            p.get("city") or "",
            p.get("state") or "FL",
            p.get("zip_code") or "",
        ))
    log.info("%d properties have valid address lines", len(batch))

    now_iso = datetime.now(timezone.utc).isoformat()
    total_matched = 0
    total_missed = 0

    # Chunk into Census-sized batches
    for i in range(0, len(batch), CENSUS_BATCH_SIZE):
        chunk = batch[i : i + CENSUS_BATCH_SIZE]
        log.info("Batch %d/%d (%d rows)",
                 (i // CENSUS_BATCH_SIZE) + 1,
                 (len(batch) + CENSUS_BATCH_SIZE - 1) // CENSUS_BATCH_SIZE,
                 len(chunk))
        try:
            results = run_census_batch(chunk)
        except httpx.HTTPError as exc:
            log.error("Census batch failed: %s", exc)
            continue

        # Apply results to DB via upsert in batches of 500. One row-PATCH
        # per property hits Supabase with 10K+ individual HTTP/2 streams
        # and Cloudflare terminates the connection after ~20K. Upsert-
        # batches drop that to a handful of requests.
        # PostgREST upsert is conceptually INSERT...ON CONFLICT DO UPDATE,
        # so the payload must satisfy every NOT NULL column even when the
        # operation will really be UPDATE. The properties schema requires:
        # id, county_id, normalized_address (created_at/updated_at have
        # defaults). We round-trip those from the SELECT so the upsert
        # can succeed without re-reading them.
        matched_rows = []
        missed_rows = []
        for row_id, _street, _city, _state, _zip in chunk:
            prop = index_to_prop.get(row_id, {})
            county_id = prop.get("county_id")
            normalized_address = prop.get("normalized_address")
            if row_id in results:
                matched_rows.append({
                    "id": row_id,
                    "county_id": county_id,
                    "normalized_address": normalized_address,
                    "latitude": results[row_id]["lat"],
                    "longitude": results[row_id]["lng"],
                    "geocoded_at": now_iso,
                    "geocode_source": "us_census",
                })
                total_matched += 1
            else:
                missed_rows.append({
                    "id": row_id,
                    "county_id": county_id,
                    "normalized_address": normalized_address,
                    "geocoded_at": now_iso,
                    "geocode_source": "us_census_no_match",
                })
                total_missed += 1

        if not args.dry_run:
            BATCH = 500
            for batch_rows, label in ((matched_rows, "matched"), (missed_rows, "missed")):
                for j in range(0, len(batch_rows), BATCH):
                    client.table("properties").upsert(
                        batch_rows[j : j + BATCH],
                        on_conflict="id",
                    ).execute()
                log.info("Persisted %d %s rows", len(batch_rows), label)

    log.info("Done. Matched %d, missed %d (of %d attempted)",
             total_matched, total_missed, total_matched + total_missed)


if __name__ == "__main__":
    main()
