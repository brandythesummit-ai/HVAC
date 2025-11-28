"""Summit.AI configuration and testing endpoints with Private Integration static token."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.database import get_db
from app.services.summit_client import SummitClient

router = APIRouter(prefix="/api/summit", tags=["summit"])


class SummitConfigRequest(BaseModel):
    """Model for Summit.AI Private Integration configuration."""
    access_token: str
    location_id: str


@router.get("/config", response_model=dict)
async def get_summit_config(db=Depends(get_db)):
    """Get current Summit.AI Private Integration configuration (masked)."""
    try:
        # Get from database
        agency_result = db.table("agencies").select("*").limit(1).execute()

        if agency_result.data:
            agency = agency_result.data[0]
            access_token = agency.get("summit_access_token", "")
            # Mask token (show only last 4 characters)
            masked_token = ""
            if access_token:
                masked_token = "••••" + access_token[-4:] if len(access_token) > 4 else "••••"

            return {
                "access_token": masked_token,
                "location_id": agency.get("summit_location_id", ""),
                "configured": bool(access_token and agency.get("summit_location_id"))
            }
        else:
            return {
                "access_token": "",
                "location_id": "",
                "configured": False
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config", response_model=dict)
async def update_summit_config(config: SummitConfigRequest, db=Depends(get_db)):
    """Update Summit.AI Private Integration configuration."""
    try:
        # Store in agency record (assuming single agency for now)
        agency_result = db.table("agencies").select("*").limit(1).execute()

        if agency_result.data:
            # Update existing
            db.table("agencies").update({
                "summit_access_token": config.access_token,
                "summit_location_id": config.location_id
            }).eq("id", agency_result.data[0]["id"]).execute()
        else:
            # Create new agency
            db.table("agencies").insert({
                "name": "Default Agency",
                "summit_access_token": config.access_token,
                "summit_location_id": config.location_id
            }).execute()

        return {
            "message": "Summit.AI Private Integration configuration saved successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test", response_model=dict)
async def test_summit_connection(db=Depends(get_db)):
    """Test Summit.AI connection with Private Integration token."""
    try:
        # Get credentials from database
        agency_result = db.table("agencies").select("*").limit(1).execute()

        if not agency_result.data:
            raise HTTPException(status_code=400, detail="No agency configured")

        agency = agency_result.data[0]

        # Create client with stored token
        client = SummitClient(
            access_token=agency.get("summit_access_token"),
            location_id=agency.get("summit_location_id")
        )

        test_result = await client.test_connection()

        if not test_result["success"]:
            raise HTTPException(status_code=400, detail=test_result.get("message"))

        return test_result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync-status", response_model=dict)
async def get_sync_status(db=Depends(get_db)):
    """Get overall sync status."""
    try:
        # Count leads by status
        pending = db.table("leads").select("id", count="exact").eq("summit_sync_status", "pending").execute()
        synced = db.table("leads").select("id", count="exact").eq("summit_sync_status", "synced").execute()
        failed = db.table("leads").select("id", count="exact").eq("summit_sync_status", "failed").execute()

        return {
            "pending": pending.count if hasattr(pending, 'count') else 0,
            "synced": synced.count if hasattr(synced, 'count') else 0,
            "failed": failed.count if hasattr(failed, 'count') else 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
