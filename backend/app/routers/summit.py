"""Summit.AI configuration and testing endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.services.summit_client import SummitClient
from app.config import settings

router = APIRouter(prefix="/api/summit", tags=["summit"])


class SummitConfigRequest(BaseModel):
    """Model for Summit.AI configuration."""
    api_key: str
    location_id: str


@router.get("/config", response_model=dict)
async def get_summit_config():
    """Get current Summit.AI configuration (masked)."""
    try:
        return {
            "success": True,
            "data": {
                "api_key": "••••••••" if settings.summit_api_key else "",
                "location_id": settings.summit_location_id,
                "configured": bool(settings.summit_api_key and settings.summit_location_id)
            },
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


@router.put("/config", response_model=dict)
async def update_summit_config(config: SummitConfigRequest, db=Depends(get_db)):
    """Update Summit.AI configuration."""
    try:
        # In a real app, you'd store this in the database or update environment
        # For now, we'll just validate the config by testing the connection

        client = SummitClient(api_key=config.api_key, location_id=config.location_id)
        test_result = await client.test_connection()

        if not test_result.get("success"):
            raise HTTPException(status_code=400, detail=test_result.get("message"))

        # Store in agency record (assuming single agency for now)
        agency_result = db.table("agencies").select("*").limit(1).execute()

        if agency_result.data:
            # Update existing
            db.table("agencies").update({
                "summit_api_key": config.api_key,
                "summit_location_id": config.location_id
            }).eq("id", agency_result.data[0]["id"]).execute()
        else:
            # Create new agency
            db.table("agencies").insert({
                "name": "Default Agency",
                "summit_api_key": config.api_key,
                "summit_location_id": config.location_id
            }).execute()

        return {
            "success": True,
            "data": {
                "message": "Summit.AI configuration updated successfully"
            },
            "error": None
        }

    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


@router.post("/test", response_model=dict)
async def test_summit_connection(config: Optional[SummitConfigRequest] = None):
    """Test Summit.AI connection."""
    try:
        if config:
            client = SummitClient(api_key=config.api_key, location_id=config.location_id)
        else:
            client = SummitClient()

        test_result = await client.test_connection()

        return {
            "success": test_result["success"],
            "data": test_result,
            "error": None if test_result["success"] else test_result.get("message")
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


@router.get("/sync-status", response_model=dict)
async def get_sync_status(db=Depends(get_db)):
    """Get overall sync status."""
    try:
        # Count leads by status
        pending = db.table("leads").select("id", count="exact").eq("summit_sync_status", "pending").execute()
        synced = db.table("leads").select("id", count="exact").eq("summit_sync_status", "synced").execute()
        failed = db.table("leads").select("id", count="exact").eq("summit_sync_status", "failed").execute()

        return {
            "success": True,
            "data": {
                "pending": pending.count if hasattr(pending, 'count') else 0,
                "synced": synced.count if hasattr(synced, 'count') else 0,
                "failed": failed.count if hasattr(failed, 'count') else 0
            },
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }
