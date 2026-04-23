"""Phase 3: re-link existing permits to HCPAO-sourced parcels.

Before the pivot: every permit seeded its own property row via address
string match. Now that ~450K residential parcels exist in `properties`
keyed on FOLIO, we need to attach the 41K existing permits (22K legacy
scraper + 19K Accela API) to the correct parcel-based property.

Design choice: iterate PARCELS, not permits. For each residential
parcel, find all permits whose `property_address` normalizes to the
parcel's `normalized_address` and compute:
  - most_recent_hvac_permit_id = permit with latest opened_date
  - most_recent_hvac_date = that permit's opened_date
  - total_hvac_permits = count of matching permits

This approach is idempotent — running twice produces the same result
because the counters are computed from scratch each pass (no read-modify-
write on the counter). Permits that don't match any parcel (e.g., the
6394 phantom "Hillsborough County, FL" Accela records) stay in `permits`
as the historical record but don't drive any lead.

Also performs the phantom-property cleanup:
  - Delete lead.property_id = phantom
  - Delete phantom property row itself
  - Permit rows linked to phantom stay in `permits` — they're still valid
    historical records, they just won't contribute to any parcel's counters.

Usage:
    cd backend && source venv/bin/activate
    python -m scripts.relink_permits_to_parcels
        [--county-id UUID]
        [--batch-size N]      # parcels per iteration (default 1000)
        [--dry-run]           # no writes; just report what would happen
"""
from __future__ import annotations

import argparse
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
logger = logging.getLogger("relink_permits")

HCFL_COUNTY_ID = "07e876b9-938e-4f53-b0dc-7bb9ce7e9cdd"


def drop_phantom_property(db, county_id: str, dry_run: bool) -> int:
    """Remove the 'HILLSBOROUGH COUNTY FL' bucket that aggregated all
    permits whose Accela address was just the county name.

    Returns the number of permits that were linked to this phantom.
    """
    phantom = (
        db.table("properties")
        .select("id, normalized_address, total_hvac_permits")
        .eq("county_id", county_id)
        .eq("normalized_address", "HILLSBOROUGH COUNTY FL")
        .execute()
    )
    if not phantom.data:
        logger.info("No phantom property found (already cleaned up?)")
        return 0

    row = phantom.data[0]
    permits_attached = row.get("total_hvac_permits") or 0
    logger.info(
        "Found phantom property %s with %d attached permits",
        row["id"], permits_attached,
    )

    if dry_run:
        logger.info("(dry-run) would delete phantom lead and property row")
        return permits_attached

    # CASCADE on leads.property_id → properties handles lead removal.
    db.table("properties").delete().eq("id", row["id"]).execute()
    logger.info("  deleted phantom property + cascaded lead")
    return permits_attached


def iter_residential_parcels(db, county_id: str, batch_size: int):
    """Paginate through parcel-sourced residential properties.

    Uses keyset pagination on id to survive Supabase's 1000-row default.
    """
    offset = 0
    while True:
        resp = (
            db.table("properties")
            .select("id, normalized_address, most_recent_hvac_permit_id, "
                    "most_recent_hvac_date, total_hvac_permits")
            .eq("county_id", county_id)
            .eq("source", "hcpao_parcel")
            .eq("is_residential", True)
            .order("id")
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            break
        yield rows
        if len(rows) < batch_size:
            break
        offset += batch_size


def find_matching_permits(db, county_id: str, normalized_address: str):
    """Return all permits whose property_address matches this parcel.

    Permits are stored with a raw property_address string. We uppercase
    and compare. The `(county_id, property_address)` index makes this fast
    (per migration 022).
    """
    resp = (
        db.table("permits")
        .select("id, opened_date, source, accela_record_id")
        .eq("county_id", county_id)
        .ilike("property_address", normalized_address)
        .execute()
    )
    return resp.data or []


def compute_parcel_link_update(
    parcel: dict, permits: list[dict]
) -> dict | None:
    """Compute the property-row update payload from the matched permits.

    Returns None if no change is needed (idempotent no-op).
    """
    dated = [p for p in permits if p.get("opened_date")]
    if not dated:
        # No usable permits — clear any stale link but only if it was set.
        if parcel.get("most_recent_hvac_permit_id") or (parcel.get("total_hvac_permits") or 0) > 0:
            return {
                "most_recent_hvac_permit_id": None,
                "most_recent_hvac_date": None,
                "total_hvac_permits": 0,
            }
        return None

    most_recent = max(dated, key=lambda p: p["opened_date"])
    new_permit_id = most_recent["id"]
    new_date = most_recent["opened_date"]
    new_count = len(dated)

    # Only write if something actually changed — keeps the
    # `properties_touch_updated_at` trigger from bumping timestamps
    # for no-op re-runs.
    if (
        parcel.get("most_recent_hvac_permit_id") == new_permit_id
        and (parcel.get("most_recent_hvac_date") or "")[:10] == new_date[:10]
        and (parcel.get("total_hvac_permits") or 0) == new_count
    ):
        return None

    return {
        "most_recent_hvac_permit_id": new_permit_id,
        "most_recent_hvac_date": new_date,
        "total_hvac_permits": new_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--county-id", default=HCFL_COUNTY_ID)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass

    from supabase import create_client
    sup_url = os.environ.get("SUPABASE_URL")
    sup_key = (
        os.environ.get("SUPABASE_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    )
    if not sup_url or not sup_key:
        raise SystemExit("SUPABASE_URL and SUPABASE_KEY required")
    db = create_client(sup_url, sup_key)

    # Step 1: drop phantom bucket.
    phantom_count = drop_phantom_property(db, args.county_id, args.dry_run)
    logger.info("Phantom cleanup: %d permits were linked to phantom", phantom_count)

    # Step 2: iterate residential parcels + link permits.
    parcels_seen = 0
    parcels_linked = 0
    parcels_unchanged = 0
    parcels_with_permits = 0
    total_permits_linked = 0

    for batch in iter_residential_parcels(db, args.county_id, args.batch_size):
        parcels_seen += len(batch)
        for parcel in batch:
            addr = parcel.get("normalized_address")
            if not addr:
                continue
            permits = find_matching_permits(db, args.county_id, addr)
            update = compute_parcel_link_update(parcel, permits)
            if update is None:
                parcels_unchanged += 1
                continue

            if update.get("most_recent_hvac_permit_id"):
                parcels_with_permits += 1
                total_permits_linked += update.get("total_hvac_permits", 0)

            if args.dry_run:
                continue

            db.table("properties").update(update).eq("id", parcel["id"]).execute()
            parcels_linked += 1

        if parcels_seen % 5000 == 0:
            logger.info(
                "  progress: seen=%d linked=%d unchanged=%d with_permits=%d",
                parcels_seen, parcels_linked, parcels_unchanged, parcels_with_permits,
            )

    logger.info(
        "DONE. parcels_seen=%d linked=%d unchanged=%d with_permits=%d "
        "total_permits_linked=%d phantom_permits_dropped=%d",
        parcels_seen, parcels_linked, parcels_unchanged, parcels_with_permits,
        total_permits_linked, phantom_count,
    )


if __name__ == "__main__":
    main()
