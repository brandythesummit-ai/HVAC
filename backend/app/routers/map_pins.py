"""Dedicated map-pin endpoint optimized for the parcels-first scale.

Before the pivot, the Map fetched from /api/leads with a 12K limit. That
worked when there were ~12K leads total. With 450K residential parcels,
the lead×properties inner join plus bbox filter exceeds Supabase's
statement timeout even for small viewports.

This endpoint calls a SECURITY DEFINER Postgres function
(map_pins_in_bbox) that returns all matching residential parcels as a
single jsonb blob. Migration 039 introduced this RPC because the prior
PostgREST-paginated path required 10 round-trips for a 10K-limit fetch
(1000 rows per page) and took ~4s end-to-end; the RPC lands in ~1.4s.

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
    """Return residential-parcel pins inside the bbox via RPC."""
    db = get_db()

    # Sanity: reject inverted boxes early — caller bug, not a DB problem.
    if bbox_ne_lat <= bbox_sw_lat or bbox_ne_lng <= bbox_sw_lng:
        raise HTTPException(status_code=400, detail="Inverted bbox")

    # Default to HOT+WARM only when no tier filter is supplied. COLD/COOL
    # are noise for the V1 field-sales use case; caller can override by
    # passing an explicit tier list.
    if lead_tier:
        tiers = [t.strip().upper() for t in lead_tier.split(",") if t.strip()] or None
    else:
        tiers = ["HOT", "WARM"]

    try:
        res = db.rpc(
            "map_pins_in_bbox",
            {
                "p_ne_lat": bbox_ne_lat,
                "p_ne_lng": bbox_ne_lng,
                "p_sw_lat": bbox_sw_lat,
                "p_sw_lng": bbox_sw_lng,
                "p_lead_tiers": tiers,
                "p_owner_occupied": owner_occupied,
                "p_year_built_min": year_built_min,
                "p_year_built_max": year_built_max,
                "p_limit": limit,
            },
        ).execute()
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}

    pins = res.data or []
    return {
        "success": True,
        "data": {
            "pins": pins,
            "count": len(pins),
            "truncated": len(pins) >= limit,
            "bbox": {
                "ne_lat": bbox_ne_lat, "ne_lng": bbox_ne_lng,
                "sw_lat": bbox_sw_lat, "sw_lng": bbox_sw_lng,
            },
        },
        "error": None,
    }
