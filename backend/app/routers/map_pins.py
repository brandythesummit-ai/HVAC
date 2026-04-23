"""Dedicated map-pin endpoint optimized for the parcels-first scale.

Before the pivot, the Map fetched from /api/leads with a 12K limit. That
worked when there were ~12K leads total. With 450K residential parcels,
the lead×properties inner join plus bbox filter exceeds Supabase's
statement timeout even for small viewports.

This endpoint queries `properties` directly (no lead join) and returns
only the fields a map pin needs: id, lat, lng, tier, score, owner,
address, year_built. The Map's DetailSheet fetches the full lead row
separately via GET /api/leads/:id when the user clicks a pin.

Always bbox-scoped: the client must provide ne_lat, ne_lng, sw_lat,
sw_lng. Unbounded queries would try to return 450K rows.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import logging

from app.database import get_db

router = APIRouter(prefix="/api", tags=["map"])
logger = logging.getLogger(__name__)


@router.get("/map-pins", response_model=dict)
async def map_pins(
    bbox_ne_lat: float = Query(...),
    bbox_ne_lng: float = Query(...),
    bbox_sw_lat: float = Query(...),
    bbox_sw_lng: float = Query(...),
    lead_tier: Optional[str] = Query(
        None,
        description="Comma-separated tier filter, e.g. HOT,WARM",
    ),
    owner_occupied: Optional[bool] = Query(None),
    year_built_min: Optional[int] = Query(None),
    year_built_max: Optional[int] = Query(None),
    limit: int = Query(10000, ge=1, le=20000),
):
    """Return residential-parcel pins inside the bbox.

    The returned rows are `properties`, not `leads`. One property maps
    to at most one lead in our schema, so the frontend can still match
    up state (INTERESTED/KNOCKED/...) by `property_id` → lead lookup.
    """
    db = get_db()

    # Sanity: reject inverted boxes early — caller bug, not a DB problem.
    if bbox_ne_lat <= bbox_sw_lat or bbox_ne_lng <= bbox_sw_lng:
        raise HTTPException(status_code=400, detail="Inverted bbox")

    q = (
        db.table("properties")
        .select(
            "id, normalized_address, latitude, longitude, "
            "lead_tier, lead_score, year_built, owner_name, "
            "owner_occupied, total_hvac_permits, most_recent_hvac_date, "
            "total_property_value, heated_sqft, bedrooms_count, bathrooms_count, city, zip_code"
        )
        .eq("is_residential", True)
        .gte("latitude", bbox_sw_lat).lte("latitude", bbox_ne_lat)
        .gte("longitude", bbox_sw_lng).lte("longitude", bbox_ne_lng)
    )

    if lead_tier:
        tiers = [t.strip().upper() for t in lead_tier.split(",") if t.strip()]
        if len(tiers) == 1:
            q = q.eq("lead_tier", tiers[0])
        elif tiers:
            q = q.in_("lead_tier", tiers)

    if owner_occupied is True:
        q = q.eq("owner_occupied", True)
    elif owner_occupied is False:
        q = q.eq("owner_occupied", False)

    if year_built_min is not None:
        q = q.gte("year_built", year_built_min)
    if year_built_max is not None:
        q = q.lte("year_built", year_built_max)

    # PostgREST caps at ~1000 per request — paginate up to the caller's
    # limit so the Map can grab a full viewport in one logical fetch.
    PAGE = 1000
    collected: list = []
    offset = 0
    try:
        while offset < limit:
            page_size = min(PAGE, limit - offset)
            page = q.range(offset, offset + page_size - 1).execute()
            rows = page.data or []
            collected.extend(rows)
            if len(rows) < page_size:
                break
            offset += page_size
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}

    return {
        "success": True,
        "data": {
            "pins": collected,
            "count": len(collected),
            "truncated": len(collected) >= limit,
            "bbox": {
                "ne_lat": bbox_ne_lat, "ne_lng": bbox_ne_lng,
                "sw_lat": bbox_sw_lat, "sw_lng": bbox_sw_lng,
            },
        },
        "error": None,
    }
