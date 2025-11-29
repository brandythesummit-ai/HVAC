"""Global application settings endpoints (Accela credentials, etc.)."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.database import get_db
from app.services.encryption import encryption_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


class AccelaSettings(BaseModel):
    """Model for global Accela API credentials."""
    app_id: str = Field(..., description="Accela Application ID")
    app_secret: str = Field(..., description="Accela Application Secret")


@router.get("/accela", response_model=dict)
async def get_accela_settings(db=Depends(get_db)):
    """Get global Accela credentials (app_secret is masked)."""
    try:
        # Query app_settings table
        result = db.table("app_settings").select("*").eq("key", "accela").execute()

        if result.data:
            settings = result.data[0]
            app_secret = settings.get("app_secret", "")

            # Mask secret (show only last 4 characters)
            masked_secret = ""
            if app_secret:
                # Decrypt to get length, then mask
                decrypted = encryption_service.decrypt(app_secret)
                masked_secret = "••••" + decrypted[-4:] if len(decrypted) > 4 else "••••"

            return {
                "app_id": settings.get("app_id", ""),
                "app_secret": masked_secret,
                "configured": bool(settings.get("app_id") and app_secret)
            }
        else:
            return {
                "app_id": "",
                "app_secret": "",
                "configured": False
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Accela settings: {str(e)}")


@router.put("/accela", response_model=dict)
async def update_accela_settings(settings: AccelaSettings, db=Depends(get_db)):
    """Update global Accela credentials (app_secret will be encrypted)."""
    try:
        # Encrypt app_secret before storing
        encrypted_secret = encryption_service.encrypt(settings.app_secret)

        # Check if settings exist
        existing = db.table("app_settings").select("*").eq("key", "accela").execute()

        if existing.data:
            # Update existing
            result = db.table("app_settings").update({
                "app_id": settings.app_id,
                "app_secret": encrypted_secret
            }).eq("key", "accela").execute()
        else:
            # Insert new
            result = db.table("app_settings").insert({
                "key": "accela",
                "app_id": settings.app_id,
                "app_secret": encrypted_secret
            }).execute()

        return {"success": True, "message": "Accela credentials updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update Accela settings: {str(e)}")


@router.delete("/accela", response_model=dict)
async def delete_accela_settings(db=Depends(get_db)):
    """Delete global Accela credentials."""
    try:
        result = db.table("app_settings").delete().eq("key", "accela").execute()
        return {"success": True, "message": "Accela credentials deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete Accela settings: {str(e)}")
