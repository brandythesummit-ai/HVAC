"""County management endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime

from app.database import get_db
from app.models.county import CountyCreate, CountyUpdate, CountyResponse, CountyTestRequest
from app.services.accela_client import AccelaClient
from app.services.encryption import encryption_service

router = APIRouter(prefix="/api/counties", tags=["counties"])


@router.post("", response_model=dict)
async def create_county(county: CountyCreate, db=Depends(get_db)):
    """Create a new county with Accela credentials and test connection."""
    try:
        # Test connection first
        client = AccelaClient(
            environment=county.accela_environment,
            app_id=county.accela_app_id,
            app_secret=encryption_service.encrypt(county.accela_app_secret)
        )

        test_result = await client.test_connection()
        if not test_result.get("success"):
            raise HTTPException(status_code=400, detail=test_result.get("message"))

        # Create county record
        county_data = {
            "name": county.name,
            "accela_environment": county.accela_environment,
            "accela_app_id": county.accela_app_id,
            "accela_app_secret": encryption_service.encrypt(county.accela_app_secret),
            "accela_access_token": client._access_token,
            "token_expires_at": client._token_expires_at,
            "status": "connected",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        }

        if county.agency_id:
            county_data["agency_id"] = county.agency_id

        result = db.table("counties").insert(county_data).execute()

        return {
            "success": True,
            "data": result.data[0] if result.data else None,
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


@router.get("", response_model=dict)
async def list_counties(db=Depends(get_db)):
    """List all counties with their status."""
    try:
        result = db.table("counties").select("*").order("created_at", desc=True).execute()

        # Mask secrets in response
        counties = []
        for county in result.data:
            county_copy = county.copy()
            county_copy["accela_app_secret"] = "••••••••" if county.get("accela_app_secret") else None
            county_copy["accela_access_token"] = "••••••••" if county.get("accela_access_token") else None
            counties.append(county_copy)

        return {
            "success": True,
            "data": counties,
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


@router.get("/{county_id}", response_model=dict)
async def get_county(county_id: str, db=Depends(get_db)):
    """Get county details."""
    try:
        result = db.table("counties").select("*").eq("id", county_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="County not found")

        county = result.data[0]
        # Mask secrets
        county["accela_app_secret"] = "••••••••" if county.get("accela_app_secret") else None
        county["accela_access_token"] = "••••••••" if county.get("accela_access_token") else None

        return {
            "success": True,
            "data": county,
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


@router.put("/{county_id}", response_model=dict)
async def update_county(county_id: str, county: CountyUpdate, db=Depends(get_db)):
    """Update county information."""
    try:
        # Build update data
        update_data = {}
        if county.name is not None:
            update_data["name"] = county.name
        if county.accela_environment is not None:
            update_data["accela_environment"] = county.accela_environment
        if county.accela_app_id is not None:
            update_data["accela_app_id"] = county.accela_app_id
        if county.accela_app_secret is not None:
            update_data["accela_app_secret"] = encryption_service.encrypt(county.accela_app_secret)
        if county.is_active is not None:
            update_data["is_active"] = county.is_active

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        result = db.table("counties").update(update_data).eq("id", county_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="County not found")

        return {
            "success": True,
            "data": result.data[0],
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


@router.delete("/{county_id}", response_model=dict)
async def delete_county(county_id: str, db=Depends(get_db)):
    """Delete a county."""
    try:
        result = db.table("counties").delete().eq("id", county_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="County not found")

        return {
            "success": True,
            "data": {"message": "County deleted successfully"},
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


@router.post("/{county_id}/test", response_model=dict)
async def test_county_connection(county_id: str, db=Depends(get_db)):
    """Test Accela connection for a county."""
    try:
        # Get county
        result = db.table("counties").select("*").eq("id", county_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="County not found")

        county = result.data[0]

        # Create client and test
        client = AccelaClient(
            environment=county["accela_environment"],
            app_id=county["accela_app_id"],
            app_secret=county["accela_app_secret"],
            access_token=county.get("accela_access_token", ""),
            token_expires_at=county.get("token_expires_at", "")
        )

        test_result = await client.test_connection()

        # Update status
        new_status = "connected" if test_result["success"] else "error"
        db.table("counties").update({
            "status": new_status,
            "token_expires_at": test_result.get("token_expires_at")
        }).eq("id", county_id).execute()

        return {
            "success": test_result["success"],
            "data": test_result,
            "error": None if test_result["success"] else test_result.get("message")
        }

    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


@router.post("/test-credentials", response_model=dict)
async def test_credentials(request: CountyTestRequest):
    """Test Accela credentials without saving."""
    try:
        client = AccelaClient(
            environment=request.accela_environment,
            app_id=request.accela_app_id,
            app_secret=encryption_service.encrypt(request.accela_app_secret)
        )

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
