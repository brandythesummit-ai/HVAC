"""County management endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
import secrets
import urllib.parse

from app.database import get_db
from app.models.county import CountyCreate, CountyUpdate, CountyResponse
from app.services.accela_client import AccelaClient
from app.services.encryption import encryption_service
from app.config import settings

router = APIRouter(prefix="/api/counties", tags=["counties"])


@router.post("", response_model=dict)
async def create_county(county: CountyCreate, db=Depends(get_db)):
    """Create a new county. OAuth authorization must be completed separately."""
    try:
        # Create county record (without OAuth authorization yet)
        county_data = {
            "name": county.name,
            "county_code": county.county_code,
            "status": "pending_authorization",  # Will change to "connected" after OAuth
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        }

        if county.agency_id:
            county_data["agency_id"] = county.agency_id

        result = db.table("counties").insert(county_data).execute()

        return {
            "success": True,
            "data": result.data[0] if result.data else None,
            "message": "County created. Please complete OAuth authorization.",
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

        # Mask secrets and add oauth_authorized flag
        counties = []
        for county in result.data:
            county_copy = county.copy()
            # Remove sensitive fields from response
            county_copy.pop("refresh_token", None)
            county_copy.pop("oauth_state", None)
            # Add oauth_authorized flag
            county_copy["oauth_authorized"] = bool(county.get("refresh_token"))
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

        county = result.data[0].copy()
        # Remove sensitive fields
        county.pop("refresh_token", None)
        county.pop("oauth_state", None)
        # Add oauth_authorized flag
        county["oauth_authorized"] = bool(result.data[0].get("refresh_token"))

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
        if county.county_code is not None:
            update_data["county_code"] = county.county_code
        if county.refresh_token is not None:
            update_data["refresh_token"] = encryption_service.encrypt(county.refresh_token)
        if county.token_expires_at is not None:
            update_data["token_expires_at"] = county.token_expires_at.isoformat()
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


# OAuth endpoints

@router.post("/{county_id}/oauth/authorize", response_model=dict)
async def get_oauth_authorization_url(county_id: str, db=Depends(get_db)):
    """Generate OAuth authorization URL for a county."""
    try:
        # Get county
        result = db.table("counties").select("*").eq("id", county_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="County not found")

        county = result.data[0]

        # Get global Accela app credentials
        app_settings = db.table("app_settings").select("*").eq("key", "accela").execute()
        if not app_settings.data or not app_settings.data[0].get("app_id"):
            raise HTTPException(
                status_code=400,
                detail="Accela app credentials not configured. Please configure in Settings."
            )

        app_id = app_settings.data[0]["app_id"]

        # Generate CSRF state token
        state = secrets.token_urlsafe(32)

        # Store state in county record
        db.table("counties").update({"oauth_state": state}).eq("id", county_id).execute()

        # Build authorization URL
        # Format: https://{agency}.accela.com/oauth2/authorize?client_id={app_id}&response_type=code&redirect_uri={callback_url}&state={state}&agency_name={county_code}
        callback_url = f"{settings.api_url}/api/counties/oauth/callback"

        params = {
            "client_id": app_id,
            "response_type": "code",
            "redirect_uri": callback_url,
            "state": state,
            "agency_name": county["county_code"]
        }

        # Note: The base URL depends on the agency, typically https://apis.accela.com
        base_url = "https://apis.accela.com/oauth2/authorize"
        auth_url = f"{base_url}?{urllib.parse.urlencode(params)}"

        return {
            "success": True,
            "data": {
                "authorization_url": auth_url,
                "state": state
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


@router.get("/oauth/callback", response_model=dict)
async def oauth_callback(code: str, state: str, db=Depends(get_db)):
    """Handle OAuth callback from Accela."""
    try:
        # Find county by state token
        result = db.table("counties").select("*").eq("oauth_state", state).execute()

        if not result.data:
            raise HTTPException(status_code=400, detail="Invalid state token or authorization expired")

        county = result.data[0]

        # Get global Accela app credentials
        app_settings = db.table("app_settings").select("*").eq("key", "accela").execute()
        if not app_settings.data:
            raise HTTPException(status_code=500, detail="Accela app credentials not found")

        app_id = app_settings.data[0]["app_id"]
        app_secret_encrypted = app_settings.data[0]["app_secret"]
        app_secret = encryption_service.decrypt(app_secret_encrypted)

        # Exchange authorization code for refresh token
        client = AccelaClient(
            app_id=app_id,
            app_secret=app_secret,
            county_code=county["county_code"]
        )

        token_response = await client.exchange_code_for_token(
            code=code,
            redirect_uri=f"{settings.api_url}/api/counties/oauth/callback"
        )

        if not token_response.get("success"):
            raise HTTPException(status_code=400, detail=token_response.get("error", "Token exchange failed"))

        # Store encrypted refresh token
        refresh_token_encrypted = encryption_service.encrypt(token_response["refresh_token"])

        update_data = {
            "refresh_token": refresh_token_encrypted,
            "token_expires_at": token_response.get("expires_at"),
            "status": "connected",
            "oauth_state": None  # Clear state token
        }

        db.table("counties").update(update_data).eq("id", county["id"]).execute()

        return {
            "success": True,
            "data": {
                "message": "OAuth authorization successful",
                "county_id": county["id"],
                "county_name": county["name"]
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
