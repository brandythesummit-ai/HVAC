"""Run the HCFL legacy scraper locally, in parallel with Railway.

Doubles effective throughput by having two independent workers: the
Railway worker claims streets in ascending scrape_priority/street_name
order (the production `_process_hcfl_legacy_backfill` default), while
this local worker claims in descending order. They meet in the middle
of the remaining queue with near-zero overlap.

Overlap protection relies on the `(county_id, source, source_permit_id)`
UNIQUE constraint on permits — if both workers grab the same street in
the midpoint, the second upsert just no-ops. Worst-case penalty is a
handful of redundant HCFL calls; no data corruption.

Usage:
    cd backend && source venv/bin/activate
    python -m scripts.run_scraper_locally
        [--county-id UUID]        # default: HCFL
        [--batch-size N]          # streets per iteration (default 50)
        [--concurrency N]         # outer parallelism (default 4)
        [--permit-concurrency N]  # inner permit-fetch parallelism (default 4)
        [--max-iterations N]      # stop after N batches (default: unlimited)
        [--max-street-retries N]  # same as Railway (default 3)

Stops when no unscraped streets remain.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_scraper_locally")

HCFL_COUNTY_ID = "07e876b9-938e-4f53-b0dc-7bb9ce7e9cdd"


async def run(
    county_id: str,
    batch_size: int,
    concurrency: int,
    permit_concurrency: int,
    max_iterations: Optional[int],
    max_street_retries: int,
) -> None:
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass

    from supabase import create_client
    from app.services.hcfl_legacy_scraper import HcflLegacyScraper
    from app.services.property_aggregator import PropertyAggregator

    sup_url = os.environ.get("SUPABASE_URL")
    sup_key = (
        os.environ.get("SUPABASE_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    )
    if not sup_url or not sup_key:
        logger.error("SUPABASE_URL and SUPABASE_KEY required in env")
        sys.exit(1)

    db = create_client(sup_url, sup_key)
    aggregator = PropertyAggregator(db)

    iteration = 0
    total_permits_ingested = 0
    total_streets_done = 0
    total_streets_failed = 0

    while True:
        if max_iterations is not None and iteration >= max_iterations:
            logger.info("Hit --max-iterations=%d, stopping", max_iterations)
            break
        iteration += 1

        # Descending priority/street_name order — inverse of Railway's ASC.
        # Local worker chews from the TAIL of the unscraped queue while
        # Railway chews from the HEAD. They meet in the middle with
        # zero-to-minimal overlap.
        streets_resp = (
            db.table("hcfl_streets")
            .select("id, street_name, retry_count, scrape_priority")
            .is_("scraped_at", "null")
            .lt("retry_count", max_street_retries)
            .order("scrape_priority", desc=True)
            .order("street_name", desc=True)
            .limit(batch_size)
            .execute()
        )
        streets = streets_resp.data or []
        if not streets:
            logger.info("No unscraped streets remaining. Done.")
            break

        logger.info(
            "Iteration %d: picked up %d streets (reverse priority)",
            iteration, len(streets),
        )

        # Mirror the Railway worker's per-street logic. Re-implementing
        # inline rather than calling the job-processor path because that
        # path is coupled to the background_jobs record and its state
        # transitions — we want a dumber, lockless concurrent worker.
        async def _scrape_one(street_row):
            nonlocal total_permits_ingested
            street_name = street_row["street_name"]
            street_id = street_row["id"]
            try:
                async with HcflLegacyScraper() as scraper:
                    search_result = await scraper.search_street(street_name)
                    if isinstance(search_result, dict) and "error" in search_result:
                        raise RuntimeError(f"search failed: {search_result['error']}")
                    all_stubs = search_result or []
                    hvac_stubs = scraper.filter_hvac(all_stubs)

                    permits_ingested = 0

                    async def _process_one_permit(stub, sub_scraper):
                        nonlocal permits_ingested
                        detail_result = await sub_scraper.fetch_permit_detail(stub.permit_number)
                        if isinstance(detail_result, dict) and "error" in detail_result:
                            return
                        detail = detail_result
                        if not sub_scraper.is_hvac_permit(stub, detail):
                            return
                        row = detail.to_permit_row(county_id=county_id)
                        try:
                            upsert_resp = db.table("permits").upsert(
                                row,
                                on_conflict="county_id,source,source_permit_id",
                                ignore_duplicates=False,
                            ).execute()
                            permits_ingested += 1
                        except Exception as exc:
                            logger.warning(
                                "Upsert failed for %s: %s",
                                stub.permit_number, exc,
                            )
                            return

                        if upsert_resp and upsert_resp.data:
                            saved_row = upsert_resp.data[0]
                            try:
                                await aggregator.process_permit(saved_row, county_id)
                            except Exception as agg_exc:
                                logger.warning(
                                    "Aggregator failed for %s: %s",
                                    stub.permit_number, agg_exc,
                                )

                    if hvac_stubs and permit_concurrency > 1:
                        partitions = [[] for _ in range(permit_concurrency)]
                        for i, stub in enumerate(hvac_stubs):
                            partitions[i % permit_concurrency].append(stub)

                        async def _drain(partition):
                            async with HcflLegacyScraper(
                                hvac_prefixes=list(scraper.hvac_prefixes),
                            ) as sub_scraper:
                                for stub in partition:
                                    try:
                                        await _process_one_permit(stub, sub_scraper)
                                    except Exception as exc:
                                        logger.warning(
                                            "Partition task failed for %s: %s",
                                            stub.permit_number, exc,
                                        )

                        await asyncio.gather(
                            *(_drain(p) for p in partitions if p),
                            return_exceptions=True,
                        )
                    else:
                        for stub in hvac_stubs:
                            try:
                                await _process_one_permit(stub, scraper)
                            except Exception as exc:
                                logger.warning(
                                    "Permit task failed for %s: %s",
                                    stub.permit_number, exc,
                                )

                    db.table("hcfl_streets").update({
                        "scraped_at": "now()",
                        "permit_count_at_scrape": len(all_stubs),
                        "hvac_permit_count": permits_ingested,
                        "last_error": None,
                    }).eq("id", street_id).execute()
                    total_permits_ingested += permits_ingested
                    logger.info(
                        "[OK] %s: %d total, %d HVAC ingested",
                        street_name, len(all_stubs), permits_ingested,
                    )
                    return True
            except Exception as exc:
                logger.exception("[FAIL] %s: %s", street_name, exc)
                try:
                    db.table("hcfl_streets").update({
                        "retry_count": (street_row.get("retry_count") or 0) + 1,
                        "last_error": str(exc)[:500],
                    }).eq("id", street_id).execute()
                except Exception as db_exc:
                    logger.warning("Failed to record retry: %s", db_exc)
                return False

        # Outer concurrency across streets.
        for chunk_start in range(0, len(streets), concurrency):
            chunk = streets[chunk_start : chunk_start + concurrency]
            results = await asyncio.gather(
                *(_scrape_one(s) for s in chunk),
                return_exceptions=True,
            )
            for result in results:
                if result is True:
                    total_streets_done += 1
                else:
                    total_streets_failed += 1

        logger.info(
            "Iteration %d done. Running totals: streets=%d (%d failed), permits=%d",
            iteration, total_streets_done, total_streets_failed, total_permits_ingested,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--county-id", default=HCFL_COUNTY_ID)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--permit-concurrency", type=int, default=4)
    parser.add_argument("--max-iterations", type=int, default=None)
    parser.add_argument("--max-street-retries", type=int, default=3)
    args = parser.parse_args()

    asyncio.run(run(
        args.county_id,
        args.batch_size,
        args.concurrency,
        args.permit_concurrency,
        args.max_iterations,
        args.max_street_retries,
    ))


if __name__ == "__main__":
    main()
