"""County Pydantic models."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CountyCreate(BaseModel):
    """Model for creating a county."""
    name: str = Field(..., description="County name (e.g., 'Nassau County')")
    county_code: str = Field(..., description="Accela county/agency code (e.g., 'ISLANDERNC')")
    agency_id: Optional[str] = Field(None, description="Agency ID (optional)")


class CountyUpdate(BaseModel):
    """Model for updating a county."""
    name: Optional[str] = None
    county_code: Optional[str] = None
    refresh_token: Optional[str] = None  # Encrypted
    token_expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class CountyResponse(BaseModel):
    """Model for county response."""
    id: str
    name: str
    county_code: str
    status: Optional[str] = None
    last_pull_at: Optional[datetime] = None
    token_expires_at: Optional[datetime] = None
    oauth_authorized: bool = False  # True if refresh_token exists
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


# OAuth flow models

class OAuthInitiateRequest(BaseModel):
    """Model for initiating OAuth flow."""
    county_id: str = Field(..., description="County ID to authorize")


class OAuthCallbackRequest(BaseModel):
    """Model for OAuth callback."""
    code: str = Field(..., description="Authorization code from Accela")
    state: str = Field(..., description="CSRF state token")
