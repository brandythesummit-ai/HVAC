"""County management endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime, timedelta
import secrets
import urllib.parse

from app.database import get_db
from app.models.county import CountyCreate, CountyUpdate, CountyResponse
from app.services.accela_client import AccelaClient
from app.services.encryption import encryption_service
from app.config import settings

router = APIRouter(prefix="/api/counties", tags=["counties"])


def assign_pull_schedule(db, county_id: str):
    """Assign a weekly pull schedule to a new county, staggering across the week."""
    # Count existing schedules per day of week
    schedules = db.table("county_pull_schedules").select("schedule_day_of_week").execute()

    # Find day of week with fewest counties (load balancing)
    day_counts = {i: 0 for i in range(7)}  # 0=Sunday to 6=Saturday
    for schedule in schedules.data:
        day = schedule["schedule_day_of_week"]
        day_counts[day] += 1

    # Assign to day with minimum count
    assigned_day = min(day_counts, key=day_counts.get)

    # Calculate next pull time (next occurrence of assigned day at 2 AM UTC)
    now = datetime.utcnow()
    days_ahead = (assigned_day - now.weekday()) % 7
    if days_ahead == 0 and now.hour >= 2:
        days_ahead = 7
    next_pull = (now + timedelta(days=days_ahead)).replace(hour=2, minute=0, second=0, microsecond=0)

    # Insert schedule
    db.table("county_pull_schedules").insert({
        "county_id": county_id,
        "schedule_day_of_week": assigned_day,
        "schedule_hour": 2,
        "next_pull_at": next_pull.isoformat(),
        "auto_pull_enabled": True,
        "incremental_pull_enabled": True
    }).execute()


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
        county_id = result.data[0]["id"] if result.data else None

        # Auto-trigger 30-year historical pull (will start after OAuth is complete)
        job_data = {
            "county_id": county_id,
            "job_type": "initial_pull",
            "status": "pending",
            "parameters": {"years": 30},
            "created_at": datetime.utcnow().isoformat(),
        }
        job_result = db.table("background_jobs").insert(job_data).execute()
        job_id = job_result.data[0]["id"] if job_result.data else None

        # Update county with job reference
        if job_id:
            db.table("counties").update({
                "initial_pull_job_id": job_id
            }).eq("id", county_id).execute()

        # Assign weekly pull schedule (staggered across week)
        assign_pull_schedule(db, county_id)

        return {
            "success": True,
            "data": result.data[0] if result.data else None,
            "message": "County created. Initial 30-year pull scheduled. Please complete OAuth authorization.",
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


@router.get("/{county_id}/metrics", response_model=dict)
async def get_county_metrics(county_id: str, db=Depends(get_db)):
    """Get metrics for a county (total permits, new leads, etc.)."""
    try:
        # Get county to verify it exists
        county_result = db.table("counties").select("*").eq("id", county_id).execute()
        if not county_result.data:
            raise HTTPException(status_code=404, detail="County not found")

        # Get total permits count
        permits_result = db.table("permits").select("id", count="exact").eq("county_id", county_id).execute()
        total_permits = permits_result.count or 0

        # Get pending leads (not yet synced to Summit)
        pending_leads_result = db.table("leads").select("id", count="exact").eq("county_id", county_id).eq("summit_sync_status", "pending").execute()
        pending_leads = pending_leads_result.count or 0

        # Get synced to Summit count
        synced_result = db.table("leads").select("id", count="exact").eq("county_id", county_id).eq("summit_sync_status", "synced").execute()
        synced_to_summit = synced_result.count or 0

        return {
            "success": True,
            "data": {
                "total_permits": total_permits,
                "new_leads": pending_leads,
                "sent_to_summit": synced_to_summit,
                "sent_to_ghl": synced_to_summit  # DEPRECATED: Remove after frontend updated
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
    """
    Delete a county record only.
    Permits and leads are preserved (county_id set to null) so they remain in the system.
    """
    try:
        # Verify county exists
        county_result = db.table("counties").select("*").eq("id", county_id).execute()
        if not county_result.data:
            raise HTTPException(status_code=404, detail="County not found")

        # Step 1: Preserve permits by setting their county_id to null
        db.table("permits").update({"county_id": None}).eq("county_id", county_id).execute()

        # Step 2: Preserve leads by setting their county_id to null
        db.table("leads").update({"county_id": None}).eq("county_id", county_id).execute()

        # Step 3: Delete the county
        result = db.table("counties").delete().eq("id", county_id).execute()

        return {
            "success": True,
            "data": {"message": "County deleted successfully. Permits and leads preserved."},
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


@router.get("/{county_id}/pull-status", response_model=dict)
async def get_county_pull_status(county_id: str, db=Depends(get_db)):
    """Get pull status and schedule for a county."""
    try:
        # Get county data
        county = db.table("counties")\
            .select("initial_pull_completed, initial_pull_job_id, last_incremental_pull_at")\
            .eq("id", county_id)\
            .single()\
            .execute()

        if not county.data:
            raise HTTPException(status_code=404, detail="County not found")

        # Get pull schedule
        schedule_result = db.table("county_pull_schedules")\
            .select("*")\
            .eq("county_id", county_id)\
            .execute()

        schedule = schedule_result.data[0] if schedule_result.data else None

        # Get active job progress (if any)
        job_progress = None
        if county.data.get("initial_pull_job_id"):
            job_result = db.table("background_jobs")\
                .select("status, progress_percent, permits_pulled")\
                .eq("id", county.data["initial_pull_job_id"])\
                .execute()

            if job_result.data and job_result.data[0]["status"] in ["pending", "running"]:
                job_progress = job_result.data[0].get("progress_percent", 0)

        # Get last incremental pull stats
        last_pull_result = db.table("pull_history")\
            .select("permits_pulled, created_at")\
            .eq("county_id", county_id)\
            .eq("pull_type", "incremental")\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()

        last_pull = last_pull_result.data[0] if last_pull_result.data else None

        return {
            "success": True,
            "data": {
                "initial_pull_completed": county.data.get("initial_pull_completed", False),
                "initial_pull_progress": job_progress,
                "next_pull_at": schedule["next_pull_at"] if schedule else None,
                "last_pull_at": last_pull["created_at"] if last_pull else None,
                "last_pull_permits": last_pull["permits_pulled"] if last_pull else 0,
                "auto_pull_enabled": schedule["auto_pull_enabled"] if schedule else False
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


# OAuth endpoints

@router.post("/{county_id}/oauth/password-setup", response_model=dict)
async def setup_county_with_password(
    county_id: str,
    credentials: dict,
    db=Depends(get_db)
):
    """
    Setup county OAuth using password grant flow (simpler than authorization code).

    User enters their Accela credentials once, backend exchanges for tokens.
    Refresh tokens are used for ongoing access - user never needs to enter password again.

    Request body:
    {
        "username": "user@example.com",
        "password": "userpassword",
        "scope": "records"  // optional, defaults to "records"
    }
    """
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
        app_secret_encrypted = app_settings.data[0]["app_secret"]
        app_secret = encryption_service.decrypt(app_secret_encrypted)

        # Extract credentials
        username = credentials.get("username")
        password = credentials.get("password")
        scope = credentials.get("scope", "records")

        if not username or not password:
            raise HTTPException(
                status_code=400,
                detail="username and password are required"
            )

        # Exchange credentials for tokens using password grant
        client = AccelaClient(
            app_id=app_id,
            app_secret=app_secret,
            county_code=county["county_code"]
        )

        token_response = await client.exchange_password_for_token(
            username=username,
            password=password,
            scope=scope
        )

        if not token_response.get("success"):
            raise HTTPException(
                status_code=400,
                detail=token_response.get("error", "Token exchange failed")
            )

        # Store encrypted refresh token
        refresh_token_encrypted = encryption_service.encrypt(token_response["refresh_token"])

        update_data = {
            "refresh_token": refresh_token_encrypted,
            "token_expires_at": token_response.get("expires_at"),
            "status": "connected"
        }

        db.table("counties").update(update_data).eq("id", county_id).execute()

        return {
            "success": True,
            "data": {
                "message": "County connected successfully using password grant",
                "county_id": county_id,
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
            "agency_name": county["county_code"],
            "environment": "PROD"
        }

        # Accela OAuth authorization endpoint
        base_url = "https://auth.accela.com/oauth2/authorize"
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
async def oauth_callback(
    code: str,
    state: str,
    agency_name: str = None,
    environment: str = None,
    db=Depends(get_db)
):
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
