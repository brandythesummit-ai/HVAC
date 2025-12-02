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
    # Platform detection fields
    platform: Optional[str] = None
    platform_confidence: Optional[str] = None
    permit_portal_url: Optional[str] = None
    building_dept_website: Optional[str] = None
    platform_detection_notes: Optional[str] = None


class CountyResponse(BaseModel):
    """Model for county response."""
    id: str
    name: str
    county_code: Optional[str] = None  # Made optional since some counties don't have it yet
    status: Optional[str] = None
    last_pull_at: Optional[datetime] = None
    token_expires_at: Optional[datetime] = None
    oauth_authorized: bool = False  # True if refresh_token exists
    is_active: bool = True
    created_at: datetime
    # State/geographic fields
    state: Optional[str] = None
    state_full_name: Optional[str] = None
    # Platform detection fields
    platform: Optional[str] = None
    platform_confidence: Optional[str] = None
    permit_portal_url: Optional[str] = None
    building_dept_website: Optional[str] = None
    platform_detection_notes: Optional[str] = None

    class Config:
        from_attributes = True


class PlatformUpdate(BaseModel):
    """Model for manually updating county platform information."""
    platform: str = Field(..., description="Platform type (Accela, EnerGov, eTRAKiT, Tyler, OpenGov, Custom, Unknown)")
    platform_confidence: Optional[str] = Field("Confirmed", description="Confidence level (Confirmed, Likely, Unknown)")
    county_code: Optional[str] = Field(None, description="Agency code for Accela (e.g., 'HCFL')")
    permit_portal_url: Optional[str] = Field(None, description="URL to permit portal")
    building_dept_website: Optional[str] = Field(None, description="URL to building department website")
    platform_detection_notes: Optional[str] = Field(None, description="Notes about platform detection or configuration")


# OAuth flow models

class OAuthInitiateRequest(BaseModel):
    """Model for initiating OAuth flow."""
    county_id: str = Field(..., description="County ID to authorize")


class OAuthCallbackRequest(BaseModel):
    """Model for OAuth callback."""
    code: str = Field(..., description="Authorization code from Accela")
    state: str = Field(..., description="CSRF state token")
