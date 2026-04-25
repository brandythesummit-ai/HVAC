"""Map snapshot endpoints — once-per-session bulk pin fetch.

The frontend fetches /api/map-snapshot once per session, holds the
result in memory + IndexedDB, and does all bbox/tier filtering locally.
This eliminates the per-pan network round-trip that the bbox-scoped
/api/map-pins still has.

Three endpoints:
  - GET /api/map-snapshot         → full pin payload (~5-7MB gzipped)
  - GET /api/map-snapshot/version → cheap freshness check (~50 bytes)
  - POST /api/map-snapshot/refresh → rebuild the materialized view
                                    (called after permit ingest)

The data lives in a Postgres materialized view (map_snapshot_mv). Reads
are ~500ms; refresh is ~10s but happens out-of-band. See migration 062
for the SQL side.
"""
from fastapi import APIRouter, Response
import logging

from app.database import get_db

router = APIRouter(prefix="/api", tags=["map"])
logger = logging.getLogger(__name__)

# Browser cache as a defensive layer in case the client's IndexedDB cache
# fails. 1hr is fine since the client also has its own once-per-session
# semantics; this only kicks in for repeated reloads inside the window.
_SNAPSHOT_CACHE_CONTROL = "private, max-age=3600"
_VERSION_CACHE_CONTROL = "private, max-age=60"


@router.get("/map-snapshot", response_model=dict)
async def get_map_snapshot(response: Response):
    """Return the full HOT/WARM pin snapshot for client-side caching."""
    db = get_db()
    try:
        res = db.rpc("map_snapshot_v1", {}).execute()
    except Exception as e:
        logger.exception("map_snapshot_v1 RPC failed")
        return {"success": False, "data": None, "error": str(e)}

    payload = res.data or {"version": None, "pins": []}
    response.headers["Cache-Control"] = _SNAPSHOT_CACHE_CONTROL
    if payload.get("version"):
        response.headers["X-Snapshot-Version"] = payload["version"]

    return {
        "success": True,
        "data": {
            "version": payload.get("version"),
            "pins": payload.get("pins") or [],
            "count": len(payload.get("pins") or []),
        },
        "error": None,
    }


@router.get("/map-snapshot/version", response_model=dict)
async def get_map_snapshot_version(response: Response):
    """Return just the snapshot version. Used by the client to decide
    whether to refetch the (much larger) full snapshot."""
    db = get_db()
    try:
        res = db.rpc("map_snapshot_version_v1", {}).execute()
    except Exception as e:
        logger.exception("map_snapshot_version_v1 RPC failed")
        return {"success": False, "data": None, "error": str(e)}

    payload = res.data or {"version": None}
    response.headers["Cache-Control"] = _VERSION_CACHE_CONTROL
    return {
        "success": True,
        "data": {"version": payload.get("version")},
        "error": None,
    }


@router.post("/map-snapshot/refresh", response_model=dict)
async def refresh_map_snapshot():
    """Rebuild the snapshot materialized view. Call after permit ingest
    jobs land, or expose to admins via the UI for manual sync."""
    db = get_db()
    try:
        res = db.rpc("refresh_map_snapshot", {}).execute()
    except Exception as e:
        logger.exception("refresh_map_snapshot RPC failed")
        return {"success": False, "data": None, "error": str(e)}

    return {"success": True, "data": res.data, "error": None}
