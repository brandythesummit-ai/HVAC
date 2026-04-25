"""Targeted HCFL scrape of a specific list of street names.

Bypasses the job-processor and hash-partition logic entirely. Takes an
explicit list of street names, scrapes each one end-to-end, writes
permits + properties + leads via the same production code path, and
stamps scraped_at on the hcfl_streets row.

Use this to audit the pipeline against a known neighborhood before
resuming the full backfill.

Usage:
    cd backend && source venv/bin/activate
    python -m scripts.scrape_targeted_streets \\
        --streets "NEWBERRY" "SUMMER SPRINGS" "PANTHER TRACE" "CATTAIL SHORE"
        [--county-id UUID]
        [--permit-concurrency N]   # default 3 — gentler than full scraper
        [--force]                  # re-scrape even if scraped_at is set
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
logger = logging.getLogger("scrape_targeted")

HCFL_COUNTY_ID = "07e876b9-938e-4f53-b0dc-7bb9ce7e9cdd"


async def run(
    county_id: str,
    street_names: list[str],
    permit_concurrency: int,
    force: bool,
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
        logger.error("SUPABASE_URL and SUPABASE_KEY required")
        sys.exit(1)

    db = create_client(sup_url, sup_key)
    aggregator = PropertyAggregator(db)

    # Resolve each street name to its hcfl_streets row.
    normalized_names = [n.upper().strip() for n in street_names]
    streets_resp = (
        db.table("hcfl_streets")
        .select("id, street_name, retry_count, scrape_priority, scraped_at")
        .in_("street_name", normalized_names)
        .execute()
    )
    rows = streets_resp.data or []
    found_names = {r["street_name"] for r in rows}
    missing = set(normalized_names) - found_names
    if missing:
        logger.warning("Not in hcfl_streets: %s", ", ".join(sorted(missing)))
    if not rows:
        logger.error("No matching streets found. Nothing to scrape.")
        sys.exit(1)

    # Gate by --force so a re-run doesn't silently re-scrape already-done work.
    to_process = []
    for r in rows:
        if r.get("scraped_at") and not force:
            logger.info(
                "%s already scraped at %s (use --force to override)",
                r["street_name"], r["scraped_at"],
            )
        else:
            to_process.append(r)
    if not to_process:
        logger.info("All requested streets already scraped. Exiting.")
        return

    logger.info(
        "Scraping %d street(s) with permit_concurrency=%d",
        len(to_process), permit_concurrency,
    )

    total_permits = 0
    total_hvac = 0
    total_failed = 0

    for street_row in to_process:
        street_name = street_row["street_name"]
        street_id = street_row["id"]
        try:
            async with HcflLegacyScraper() as scraper:
                logger.info("=== Searching street: %s ===", street_name)
                search_result = await scraper.search_street(street_name)
                if isinstance(search_result, dict) and "error" in search_result:
                    raise RuntimeError(f"search failed: {search_result['error']}")
                all_stubs = search_result or []
                hvac_stubs = scraper.filter_hvac(all_stubs)
                logger.info(
                    "  %d total permits on %s, %d match HVAC prefix",
                    len(all_stubs), street_name, len(hvac_stubs),
                )

                permits_ingested = 0

                async def _process_one(stub, sub_scraper):
                    nonlocal permits_ingested
                    detail_result = await sub_scraper.fetch_permit_detail(stub.permit_number)
                    if isinstance(detail_result, dict) and "error" in detail_result:
                        logger.warning("  detail fetch failed for %s: %s",
                                       stub.permit_number, detail_result["error"])
                        return
                    detail = detail_result
                    if not sub_scraper.is_hvac_permit(stub, detail):
                        return
                    row = detail.to_permit_row(county_id=county_id)
                    try:
                        resp = db.table("permits").upsert(
                            row,
                            on_conflict="county_id,source,source_permit_id",
                            ignore_duplicates=False,
                        ).execute()
                        permits_ingested += 1
                    except Exception as exc:
                        logger.warning("  upsert failed for %s: %s",
                                       stub.permit_number, exc)
                        return
                    if resp and resp.data:
                        try:
                            await aggregator.process_permit(resp.data[0], county_id)
                        except Exception as exc:
                            logger.warning("  aggregator failed for %s: %s",
                                           stub.permit_number, exc)

                if hvac_stubs and permit_concurrency > 1:
                    partitions = [[] for _ in range(permit_concurrency)]
                    for i, stub in enumerate(hvac_stubs):
                        partitions[i % permit_concurrency].append(stub)

                    async def _drain(partition):
                        async with HcflLegacyScraper(
                            hvac_prefixes=list(scraper.hvac_prefixes),
                        ) as sub:
                            for stub in partition:
                                try:
                                    await _process_one(stub, sub)
                                except Exception as exc:
                                    logger.warning("  task failed for %s: %s",
                                                   stub.permit_number, exc)

                    await asyncio.gather(
                        *(_drain(p) for p in partitions if p),
                        return_exceptions=True,
                    )
                else:
                    for stub in hvac_stubs:
                        await _process_one(stub, scraper)

                db.table("hcfl_streets").update({
                    "scraped_at": "now()",
                    "permit_count_at_scrape": len(all_stubs),
                    "hvac_permit_count": permits_ingested,
                    "last_error": None,
                }).eq("id", street_id).execute()

                total_permits += len(all_stubs)
                total_hvac += permits_ingested
                logger.info(
                    "  [OK] %s: %d total permits scanned, %d HVAC ingested",
                    street_name, len(all_stubs), permits_ingested,
                )
        except Exception as exc:
            total_failed += 1
            logger.exception("  [FAIL] %s: %s", street_name, exc)
            try:
                db.table("hcfl_streets").update({
                    "retry_count": (street_row.get("retry_count") or 0) + 1,
                    "last_error": str(exc)[:500],
                }).eq("id", street_id).execute()
            except Exception:
                pass

    logger.info(
        "=== DONE. streets=%d ok, %d failed. Total permits scanned=%d, HVAC ingested=%d",
        len(to_process) - total_failed, total_failed, total_permits, total_hvac,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--county-id", default=HCFL_COUNTY_ID)
    parser.add_argument("--streets", nargs="+", required=True,
                        help="Street names to scrape (uppercase, no suffix)")
    parser.add_argument("--permit-concurrency", type=int, default=3)
    parser.add_argument("--force", action="store_true",
                        help="Re-scrape even if scraped_at is set")
    args = parser.parse_args()

    asyncio.run(run(
        args.county_id,
        args.streets,
        args.permit_concurrency,
        args.force,
    ))


if __name__ == "__main__":
    main()
