"""Run the HCFL legacy PermitReports scraper from the local machine.

Mirrors the production job_processor's `_process_hcfl_legacy_backfill`
loop but without the job-queue overhead. Picks up unscraped streets
from `hcfl_streets`, scrapes each, upserts permits, stamps `scraped_at`.

Why local: same mental model as `local_accela_pull.py`. Railway still
works for the scraper (HCFL's PermitReports isn't behind the Azure WAF
that blocks Accela traffic), but running it locally lets us:
  - avoid Railway compute cost for a one-off historical backfill
  - restart/pause without DB-level job cancellation gymnastics
  - tail progress in the terminal

Resume is automatic: unscraped streets come from the DB, not a local
checkpoint file. Ctrl-C is safe — any in-flight streets just get
retried on next run.

Usage:
    cd backend
    source venv/bin/activate
    python -m scripts.local_hcfl_scraper                    # default settings
    python -m scripts.local_hcfl_scraper --batch 500 --concurrency 3 --permit-concurrency 3
    python -m scripts.local_hcfl_scraper --dry-run          # don't write to DB

Expected runtime: ~10,500 unscraped streets × ~4 seconds/street ≈ 12 hours
at concurrency=2 × permit_concurrency=3. Scales linearly with concurrency
until HCFL rate-limits.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
from supabase import create_client
from supabase.client import ClientOptions

from app.services.hcfl_legacy_scraper import HcflLegacyScraper, PermitDetail

HCFL_COUNTY_ID = "07e876b9-938e-4f53-b0dc-7bb9ce7e9cdd"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("local_hcfl_scraper")


async def _scrape_one_street(
    scraper: HcflLegacyScraper,
    street_row: dict,
    county_id: str,
    db,
    dry_run: bool,
    permit_concurrency: int,
) -> dict:
    street_name = street_row["street_name"]
    street_id = street_row["id"]

    search_result = await scraper.search_street(street_name)
    if isinstance(search_result, dict) and "error" in search_result:
        raise RuntimeError(f"search failed: {search_result['error']}")

    all_stubs = search_result or []
    hvac_stubs = scraper.filter_hvac(all_stubs)

    permits_ingested = 0
    permits_skipped = 0

    async def _process_one(stub, sub_scraper):
        nonlocal permits_ingested, permits_skipped
        detail_result = await sub_scraper.fetch_permit_detail(stub.permit_number)
        if isinstance(detail_result, dict) and "error" in detail_result:
            log.warning("  detail fetch %s failed: %s", stub.permit_number, detail_result["error"])
            return
        detail: PermitDetail = detail_result
        if not sub_scraper.is_hvac_permit(stub, detail):
            permits_skipped += 1
            return
        if dry_run:
            permits_ingested += 1
            return
        row = detail.to_permit_row(county_id=county_id)
        try:
            db.table("permits").upsert(
                row,
                on_conflict="county_id,source,source_permit_id",
                ignore_duplicates=False,
            ).execute()
            permits_ingested += 1
        except Exception as exc:
            log.warning("  upsert %s failed: %s", stub.permit_number, exc)

    if hvac_stubs:
        if permit_concurrency <= 1:
            for stub in hvac_stubs:
                await _process_one(stub, scraper)
        else:
            partitions: list[list] = [[] for _ in range(permit_concurrency)]
            for i, stub in enumerate(hvac_stubs):
                partitions[i % permit_concurrency].append(stub)

            async def _drain(partition):
                async with HcflLegacyScraper(hvac_prefixes=list(scraper.hvac_prefixes)) as sub:
                    for stub in partition:
                        try:
                            await _process_one(stub, sub)
                        except Exception as exc:
                            log.warning("  partition task %s raised: %s", stub.permit_number, exc)

            await asyncio.gather(*(_drain(p) for p in partitions if p), return_exceptions=True)

    if not dry_run:
        db.table("hcfl_streets").update({
            "scraped_at": datetime.utcnow().isoformat(),
            "permit_count_at_scrape": len(all_stubs),
            "hvac_permit_count": permits_ingested,
            "last_error": None,
        }).eq("id", street_id).execute()

    return {
        "street": street_name,
        "all_stubs": len(all_stubs),
        "ingested": permits_ingested,
        "skipped": permits_skipped,
    }


# UUID boundary prefixes — partition the ID keyspace into N equal-size buckets.
# UUID v4 has high-entropy hex so each range gets ~1/N of rows.
SHARD_BOUNDARIES = {
    2: ["80000000-0000-0000-0000-000000000000"],
    3: [
        "55555555-5555-5555-5555-555555555555",
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    ],
    4: [
        "40000000-0000-0000-0000-000000000000",
        "80000000-0000-0000-0000-000000000000",
        "c0000000-0000-0000-0000-000000000000",
    ],
}


def _apply_shard(query, shard_index: int, shard_count: int):
    """Apply an id-range filter that partitions streets into N buckets.
    shard_count=1 → no filter. Supports 2, 3, 4 shards."""
    if shard_count <= 1:
        return query
    if shard_count not in SHARD_BOUNDARIES:
        raise ValueError(f"Unsupported shard_count {shard_count}; must be 1-4")
    boundaries = SHARD_BOUNDARIES[shard_count]
    if shard_index == 0:
        return query.lt("id", boundaries[0])
    if shard_index == shard_count - 1:
        return query.gte("id", boundaries[-1])
    # Middle shard: both bounds
    return query.gte("id", boundaries[shard_index - 1]).lt("id", boundaries[shard_index])


async def run(
    db,
    batch_size: int,
    concurrency: int,
    permit_concurrency: int,
    max_street_retries: int,
    dry_run: bool,
    shard_index: int,
    shard_count: int,
) -> None:
    # Pull total work count once for progress reporting.
    count_q = (
        db.table("hcfl_streets")
        .select("id", count="exact", head=True)
        .is_("scraped_at", "null")
        .lt("retry_count", max_street_retries)
    )
    count_q = _apply_shard(count_q, shard_index, shard_count)
    total_remaining = count_q.execute().count
    shard_label = f"shard={shard_index}/{shard_count}" if shard_count > 1 else "no-shard"
    log.info(
        "Starting local HCFL scraper · %s · %d streets in this shard · concurrency=%d × permit_concurrency=%d · dry_run=%s",
        shard_label, total_remaining, concurrency, permit_concurrency, dry_run,
    )

    totals = {"streets_done": 0, "streets_failed": 0, "permits_ingested": 0, "permits_skipped": 0}
    t_start = time.time()

    while True:
        batch_q = (
            db.table("hcfl_streets")
            .select("id, street_name, retry_count, scrape_priority")
            .is_("scraped_at", "null")
            .lt("retry_count", max_street_retries)
        )
        batch_q = _apply_shard(batch_q, shard_index, shard_count)
        streets = (
            batch_q.order("scrape_priority")
            .order("street_name")
            .limit(batch_size)
            .execute()
            .data
        ) or []
        if not streets:
            log.info("No more unscraped streets — done.")
            break

        async def _worker(street_row):
            street_name = street_row["street_name"]
            try:
                async with HcflLegacyScraper() as scraper:
                    result = await _scrape_one_street(
                        scraper, street_row, HCFL_COUNTY_ID, db, dry_run, permit_concurrency,
                    )
                    totals["streets_done"] += 1
                    totals["permits_ingested"] += result["ingested"]
                    totals["permits_skipped"] += result["skipped"]
                    elapsed = time.time() - t_start
                    rate = totals["streets_done"] / elapsed if elapsed > 0 else 0
                    eta_min = (total_remaining - totals["streets_done"]) / rate / 60 if rate > 0 else 0
                    log.info(
                        "  ✓ %s: %d stubs, %d HVAC ingested, %d skipped · total=%d permits · %.1fs/street · ETA %.0fmin",
                        street_name, result["all_stubs"], result["ingested"], result["skipped"],
                        totals["permits_ingested"], 1/rate if rate else 0, eta_min,
                    )
            except Exception as exc:
                totals["streets_failed"] += 1
                log.warning("  ✗ %s failed: %s", street_name, exc)
                if not dry_run:
                    try:
                        db.table("hcfl_streets").update({
                            "retry_count": (street_row.get("retry_count") or 0) + 1,
                            "last_error": str(exc)[:500],
                        }).eq("id", street_row["id"]).execute()
                    except Exception as db_exc:
                        log.warning("  retry-count update failed: %s", db_exc)

        for chunk_start in range(0, len(streets), concurrency):
            chunk = streets[chunk_start : chunk_start + concurrency]
            await asyncio.gather(*(_worker(s) for s in chunk), return_exceptions=True)

    elapsed = time.time() - t_start
    log.info(
        "━━━ COMPLETE ━━━ streets_done=%d streets_failed=%d permits_ingested=%d permits_skipped=%d in %.0fmin",
        totals["streets_done"], totals["streets_failed"], totals["permits_ingested"], totals["permits_skipped"],
        elapsed / 60,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Local HCFL legacy PermitReports scraper.")
    parser.add_argument("--batch", type=int, default=500,
                        help="Streets fetched per DB query (default: 500).")
    parser.add_argument("--concurrency", type=int, default=2,
                        help="Streets scraped in parallel (default: 2).")
    parser.add_argument("--permit-concurrency", type=int, default=3,
                        help="Permit-detail fetches in parallel per street (default: 3).")
    parser.add_argument("--max-retries", type=int, default=3,
                        help="Skip streets whose retry_count meets/exceeds this (default: 3).")
    parser.add_argument("--shard", type=str, default="1/1",
                        help="Partition workload across N parallel processes, format 'INDEX/COUNT' (e.g. '0/2' or '1/2'). Default '1/1' = no sharding.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scrape but don't write to DB.")
    args = parser.parse_args()

    try:
        shard_parts = args.shard.split("/")
        shard_index = int(shard_parts[0])
        shard_count = int(shard_parts[1])
        if shard_count not in (1, 2, 3, 4) or not (0 <= shard_index < shard_count):
            raise ValueError
    except (ValueError, IndexError):
        parser.error("--shard must be 'INDEX/COUNT' where COUNT is 1-4 (e.g. '0/3', '2/3')")

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    opts = ClientOptions(postgrest_client_timeout=120)
    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"], options=opts)

    asyncio.run(run(
        db,
        batch_size=args.batch,
        concurrency=args.concurrency,
        permit_concurrency=args.permit_concurrency,
        max_street_retries=args.max_retries,
        dry_run=args.dry_run,
        shard_index=shard_index,
        shard_count=shard_count,
    ))


if __name__ == "__main__":
    main()
