"""One-shot backfill: aggregate legacy-scraper permits into properties.

The initial legacy backfill upserted rows into `permits` but never
invoked `PropertyAggregator.process_permit`, so every legacy HVAC date
is invisible to the `properties` table. That makes the most-recent
HVAC date for every property fall in the Accela window (2019-03-07 to
2021-12-31), collapsing the lead-tier distribution to COOL/COLD.

This script walks every legacy permit row that has both an
`opened_date` and a `property_address`, calls `process_permit` on each,
and lets the aggregator's load-order-independent reducer do the rest:
older permits than the current `most_recent_hvac_date` just bump the
counter, newer permits become the new date.

Safe to re-run. Idempotent. Streams 1k rows per page to stay within
Supabase's default pagination window.

Usage:
    cd backend && source venv/bin/activate
    python -m scripts.aggregate_legacy_permits
        [--county-id UUID]   # narrow to a single county (default: all)
        [--limit N]          # stop after N permits (for smoke tests)
        [--dry-run]          # fetch + report, no writes
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("aggregate_legacy_permits")

PAGE_SIZE = 1000


async def run(county_id: str | None, limit: int | None, dry_run: bool) -> None:
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass

    from supabase import create_client
    from app.services.property_aggregator import PropertyAggregator

    sup_url = os.environ.get("SUPABASE_URL")
    sup_key = (
        os.environ.get("SUPABASE_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    )
    if not sup_url or not sup_key:
        log.error("SUPABASE_URL and SUPABASE_KEY required")
        sys.exit(1)

    db = create_client(sup_url, sup_key)
    aggregator = PropertyAggregator(db)

    # Paginated walk over legacy permits with both date + address.
    offset = 0
    total_seen = 0
    total_aggregated = 0
    total_errors = 0
    total_skipped = 0

    while True:
        q = (
            db.table("permits")
            .select(
                "id, county_id, property_address, opened_date, "
                "owner_phone, owner_email, property_value, year_built, "
                "square_footage, lot_size, bedrooms, bathrooms, job_value, "
                "status, permit_type, description, raw_data"
            )
            .eq("source", "hcfl_legacy_scraper")
            .not_.is_("opened_date", "null")
            .not_.is_("property_address", "null")
            .order("opened_date")  # deterministic replay order
            .range(offset, offset + PAGE_SIZE - 1)
        )
        if county_id:
            q = q.eq("county_id", county_id)

        resp = q.execute()
        rows = resp.data or []

        if not rows:
            break

        log.info(
            "Page offset=%d size=%d (aggregated=%d, errors=%d, skipped=%d)",
            offset, len(rows), total_aggregated, total_errors, total_skipped,
        )

        for row in rows:
            total_seen += 1
            if dry_run:
                continue

            try:
                property_id, lead_id, was_created = await aggregator.process_permit(
                    row, row["county_id"],
                )
                if property_id:
                    total_aggregated += 1
                else:
                    total_skipped += 1
            except Exception as exc:
                total_errors += 1
                log.warning("Aggregate failed for permit %s: %s", row.get("id"), exc)

            if limit and total_seen >= limit:
                break

        if limit and total_seen >= limit:
            break
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    log.info(
        "Done. seen=%d aggregated=%d skipped=%d errors=%d (dry_run=%s)",
        total_seen, total_aggregated, total_skipped, total_errors, dry_run,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--county-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    asyncio.run(run(args.county_id, args.limit, args.dry_run))


if __name__ == "__main__":
    main()
