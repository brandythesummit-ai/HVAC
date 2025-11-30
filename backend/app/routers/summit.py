"""Summit.AI configuration and testing endpoints with Private Integration static token."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging

from app.database import get_db
from app.services.summit_client import SummitClient
from app.services.railway_sync import sync_summit_credentials

logger = logging.getLogger(__name__)
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
    """
    Update Summit.AI Private Integration configuration.

    Steps:
    1. Test connection with provided credentials
    2. Save to database if connection successful
    3. Sync to Railway environment variables
    """
    try:
        # Step 1: Test connection FIRST before saving
        logger.info("Testing Summit.AI connection before saving...")
        test_client = SummitClient(
            access_token=config.access_token,
            location_id=config.location_id
        )

        test_result = await test_client.test_connection()

        if not test_result["success"]:
            logger.error(f"Summit.AI connection test failed: {test_result.get('message')}")
            raise HTTPException(
                status_code=400,
                detail=f"Connection test failed: {test_result.get('message', 'Unknown error')}"
            )

        logger.info("Summit.AI connection test successful")

        # Step 2: Save to database (only if test passed)
        agency_result = db.table("agencies").select("*").limit(1).execute()

        if agency_result.data:
            # Update existing
            db.table("agencies").update({
                "summit_access_token": config.access_token,
                "summit_location_id": config.location_id
            }).eq("id", agency_result.data[0]["id"]).execute()
            logger.info("Updated existing agency with Summit.AI credentials")
        else:
            # Create new agency
            db.table("agencies").insert({
                "name": "Default Agency",
                "summit_access_token": config.access_token,
                "summit_location_id": config.location_id
            }).execute()
            logger.info("Created new agency with Summit.AI credentials")

        # Step 3: Sync to Railway environment variables
        logger.info("Syncing Summit.AI credentials to Railway...")
        sync_result = await sync_summit_credentials(
            access_token=config.access_token,
            location_id=config.location_id
        )

        if sync_result["synced"]:
            logger.info("Successfully synced Summit.AI credentials to Railway")
            return {
                "message": "Summit.AI configuration saved and synced to environment",
                "connection_test": "successful",
                "railway_sync": "successful"
            }
        else:
            logger.warning(f"Railway sync not available: {sync_result.get('message')}")
            return {
                "message": "Summit.AI configuration saved to database (Railway sync not configured)",
                "connection_test": "successful",
                "railway_sync": "skipped"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating Summit.AI config: {str(e)}")
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
