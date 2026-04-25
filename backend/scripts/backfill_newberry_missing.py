"""Pull the 3 HVAC permits HCFL has for NEWBERRY that we dropped.

These three showed up in the HCFL search-results table but never made
it into our `permits` table — most likely the original scraper run hit
a transient fetch-detail error and the per-permit error path returned
without upserting. This script re-fetches them via the same scraper
service, upserts, and triggers the relink RPC so properties pick up
the new most_recent_hvac_date.

Run:
    cd backend && source venv/bin/activate && python -m scripts.backfill_newberry_missing
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

from app.services.hcfl_legacy_scraper import HcflLegacyScraper

HCFL_COUNTY_ID = "07e876b9-938e-4f53-b0dc-7bb9ce7e9cdd"
MISSING = ["NMC19545", "NME49807", "NMC04229"]


async def main() -> None:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    async with HcflLegacyScraper() as scraper:
        for permit_number in MISSING:
            print(f"\n>>> {permit_number}")
            detail_result = await scraper.fetch_permit_detail(permit_number)
            if isinstance(detail_result, dict) and "error" in detail_result:
                print(f"    FETCH ERROR: {detail_result['error']}")
                continue
            detail = detail_result
            print(f"    fetched: {detail.address} | desc={detail.description!r:.80}")
            row = detail.to_permit_row(county_id=HCFL_COUNTY_ID)
            try:
                resp = (
                    db.table("permits")
                    .upsert(
                        row,
                        on_conflict="county_id,source,source_permit_id",
                        ignore_duplicates=False,
                    )
                    .execute()
                )
                if resp and resp.data:
                    print(f"    upserted: id={resp.data[0].get('id')}")
                else:
                    print("    upsert returned no data (but didn't raise)")
            except Exception as exc:
                print(f"    UPSERT ERROR: {exc}")

    # Refresh the property <-> permit links so hvac_age_years / lead_tier
    # pick up the newly-inserted dates.
    print("\n>>> Relinking permits for HCFL county")
    relink = db.rpc(
        "relink_hvac_permits_to_properties",
        {"p_county_id": HCFL_COUNTY_ID},
    ).execute()
    print(f"    relink: {relink.data}")


if __name__ == "__main__":
    asyncio.run(main())
