"""Pull the full HVAC permit history from Accela for HCFL — run LOCALLY.

Why this exists: Accela's Azure Front Door WAF blocks our Railway egress
(both IPv4 pool reputation and IPv6 edge drops). The same Accela API
calls work fine from a laptop. This script runs from your Mac, hits
Accela directly, and writes permits to the same Supabase table Railway
writes to. Result: Railway never touches Accela, data lands in the
identical schema, downstream code (property aggregator, scoring, map)
doesn't know the difference.

Usage:
    cd backend
    source venv/bin/activate
    python -m scripts.local_accela_pull                   # full history 2021-01-01 → today
    python -m scripts.local_accela_pull --start 2021-01-01 --end 2026-04-24
    python -m scripts.local_accela_pull --restart          # ignore checkpoint, start fresh

The script chunks by month, upserts idempotently (conflict on
county_id+source+source_permit_id → no-op), and checkpoints progress
to /tmp/accela_pull_checkpoint.json so Ctrl-C is recoverable.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
from supabase import create_client

from app.services.accela_client import AccelaClient
from app.services.encryption import encryption_service

HCFL_COUNTY_ID = "07e876b9-938e-4f53-b0dc-7bb9ce7e9cdd"

# HCFL has two residential HVAC type labels. The primary is the standard
# mechanical-trade permit; "Mechanical - Exempt" covers small-dollar
# like-for-like changeouts (under HCFL's cost threshold for full review)
# and catches ~260/year of genuine residential HVAC work including
# mini-splits that the main type misses. Both pulled in this script.
PERMIT_TYPES_HVAC = [
    "Building/Residential/Trade/Mechanical",
    "Building/Residential/Trade/Mechanical - Exempt",
]
CHECKPOINT_PATH = Path("/tmp/accela_pull_checkpoint.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("local_accela_pull")


def month_chunks(start: date, end: date):
    """Yield (chunk_start, chunk_end) date pairs, one per calendar month."""
    cur = start.replace(day=1)
    while cur <= end:
        if cur.month == 12:
            next_month = cur.replace(year=cur.year + 1, month=1, day=1)
        else:
            next_month = cur.replace(month=cur.month + 1, day=1)
        chunk_end = min(next_month - timedelta(days=1), end)
        chunk_start = max(cur, start)
        yield chunk_start, chunk_end
        cur = next_month


def load_checkpoint() -> dict:
    if CHECKPOINT_PATH.exists():
        return json.loads(CHECKPOINT_PATH.read_text())
    return {"chunks_done": [], "total_saved": 0, "total_pulled": 0}


def save_checkpoint(cp: dict) -> None:
    CHECKPOINT_PATH.write_text(json.dumps(cp, indent=2))


def enrich(permit: dict) -> dict:
    """Extract the fields the permits-table wants; stash the rest in raw_data."""
    addresses = permit.get("addresses") or []
    owners = permit.get("owners") or []
    parcels = permit.get("parcels") or []

    primary_address = (
        next((a for a in addresses if a.get("isPrimary")), None)
        or (addresses[0] if addresses else None)
    )
    primary_owner = next((o for o in owners if o.get("isPrimary")), None) or (owners[0] if owners else None)
    primary_parcel = parcels[0] if parcels else None

    property_address = None
    if primary_address:
        parts = [
            primary_address.get("addressLine1"),
            primary_address.get("city"),
        ]
        state = primary_address.get("state")
        if isinstance(state, dict):
            state = state.get("value") or state.get("text")
        parts.append(state)
        parts.append(primary_address.get("postalCode"))
        property_address = ", ".join(p for p in parts if p)

    type_obj = permit.get("type", {})
    permit_type = type_obj.get("value") if isinstance(type_obj, dict) else None

    opened_date = permit.get("openedDate", "")
    if opened_date and " " in opened_date:
        opened_date = opened_date.split(" ", 1)[0]

    status_obj = permit.get("status", {})
    status = status_obj.get("value") if isinstance(status_obj, dict) else status_obj

    return {
        "county_id": HCFL_COUNTY_ID,
        "accela_record_id": permit.get("id"),
        "source": "accela_api",
        "source_permit_id": permit.get("id"),
        "raw_data": permit,
        "permit_type": permit_type,
        "description": permit.get("description"),
        "opened_date": opened_date or None,
        "status": status,
        "job_value": permit.get("jobValue") or None,
        "property_address": property_address,
        "year_built": (primary_parcel or {}).get("yearBuilt") if primary_parcel else None,
        "square_footage": (
            (primary_parcel or {}).get("squareFootage")
            or (primary_parcel or {}).get("gisObjects", [{}])[0].get("squareFootage") if primary_parcel else None
        ),
        "property_value": (primary_parcel or {}).get("value") if primary_parcel else None,
        "owner_name": (primary_owner or {}).get("fullName") or (
            " ".join(p for p in [(primary_owner or {}).get("firstName"), (primary_owner or {}).get("lastName")] if p)
            if primary_owner else None
        ),
        "owner_phone": (primary_owner or {}).get("phone1") or (primary_owner or {}).get("phone") if primary_owner else None,
        "owner_email": (primary_owner or {}).get("email") or (primary_owner or {}).get("emailAddress") if primary_owner else None,
    }


async def pull(start: date, end: date, restart: bool) -> None:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    # Load Accela creds: app_id/app_secret from app_settings, refresh_token from counties.
    app_row = db.table("app_settings").select("*").eq("key", "accela").execute().data[0]
    app_id = app_row["app_id"]
    app_secret = encryption_service.decrypt(app_row["app_secret"])

    county_row = db.table("counties").select("*").eq("id", HCFL_COUNTY_ID).execute().data[0]
    refresh_token = county_row["refresh_token"]
    county_code = county_row["county_code"]

    client = AccelaClient(
        app_id=app_id,
        app_secret=app_secret,
        county_code=county_code,
        refresh_token=refresh_token,
        access_token=county_row.get("accela_access_token") or "",
        token_expires_at=county_row.get("token_expires_at") or "",
    )

    cp = {"chunks_done": [], "total_saved": 0, "total_pulled": 0} if restart else load_checkpoint()
    done_set = set(cp["chunks_done"])

    chunks = list(month_chunks(start, end))
    log.info(
        "Pull plan: %d monthly chunks from %s to %s · already done: %d",
        len(chunks), start, end, len(done_set),
    )

    for chunk_start, chunk_end in chunks:
        # Checkpoint key now includes the type set so adding a new type
        # forces reprocessing without requiring --restart on the user.
        key = f"{chunk_start}:{chunk_end}:{'+'.join(PERMIT_TYPES_HVAC)}"
        if key in done_set:
            continue

        log.info("── chunk %s → %s ──", chunk_start, chunk_end)
        chunk_pulled = chunk_saved = 0

        batch_buffer: list[dict] = []

        # Pull each HVAC type separately — Accela's API takes a single
        # type per call, so we iterate.
        for ptype in PERMIT_TYPES_HVAC:
            async for batch in client.get_permits_stream(
                date_from=str(chunk_start),
                date_to=str(chunk_end),
                batch_size=100,
                permit_type=ptype,
            ):
                chunk_pulled += len(batch)
                batch_buffer.extend(enrich(p) for p in batch)

            # Flush every 200 rows to keep upserts small.
            while len(batch_buffer) >= 200:
                page = batch_buffer[:200]
                batch_buffer = batch_buffer[200:]
                try:
                    resp = db.table("permits").upsert(
                        page,
                        on_conflict="county_id,source,source_permit_id",
                        ignore_duplicates=False,
                    ).execute()
                    chunk_saved += len(resp.data or [])
                except Exception as exc:
                    log.warning("  upsert batch failed: %s (will retry row-by-row)", exc)
                    for row in page:
                        try:
                            db.table("permits").upsert(
                                row,
                                on_conflict="county_id,source,source_permit_id",
                                ignore_duplicates=False,
                            ).execute()
                            chunk_saved += 1
                        except Exception as row_exc:
                            log.warning(
                                "  single-row upsert failed for %s: %s",
                                row.get("source_permit_id"), row_exc,
                            )

        # Flush tail.
        if batch_buffer:
            try:
                resp = db.table("permits").upsert(
                    batch_buffer,
                    on_conflict="county_id,source,source_permit_id",
                    ignore_duplicates=False,
                ).execute()
                chunk_saved += len(resp.data or [])
            except Exception as exc:
                log.warning("  tail upsert failed: %s", exc)
                for row in batch_buffer:
                    try:
                        db.table("permits").upsert(
                            row,
                            on_conflict="county_id,source,source_permit_id",
                            ignore_duplicates=False,
                        ).execute()
                        chunk_saved += 1
                    except Exception:
                        pass

        cp["chunks_done"].append(key)
        cp["total_pulled"] += chunk_pulled
        cp["total_saved"] += chunk_saved
        save_checkpoint(cp)

        log.info(
            "  chunk done · pulled=%d saved=%d · cumulative: %d pulled / %d saved",
            chunk_pulled, chunk_saved, cp["total_pulled"], cp["total_saved"],
        )

    log.info("━━━ COMPLETE ━━━")
    log.info("Total pulled: %d · Total saved (new upserts): %d", cp["total_pulled"], cp["total_saved"])
    log.info("Checkpoint file: %s", CHECKPOINT_PATH)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pull full HCFL HVAC history from Accela (local).")
    parser.add_argument("--start", default="2021-01-01", help="Start date YYYY-MM-DD (Accela HCFL coverage begins 2021-01-19).")
    parser.add_argument("--end", default=date.today().isoformat(), help="End date YYYY-MM-DD (default: today).")
    parser.add_argument("--restart", action="store_true", help="Ignore checkpoint and start fresh.")
    args = parser.parse_args()

    start = datetime.fromisoformat(args.start).date()
    end = datetime.fromisoformat(args.end).date()
    asyncio.run(pull(start, end, args.restart))


if __name__ == "__main__":
    main()
