"""County Pydantic models."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CountyCreate(BaseModel):
    """Model for creating a county."""
    name: str = Field(..., description="County name")
    accela_environment: str = Field(..., description="Accela environment (PROD, TEST, etc.)")
    accela_app_id: str = Field(..., description="Accela application ID")
    accela_app_secret: str = Field(..., description="Accela application secret")
    agency_id: Optional[str] = Field(None, description="Agency ID (optional)")


class CountyUpdate(BaseModel):
    """Model for updating a county."""
    name: Optional[str] = None
    accela_environment: Optional[str] = None
    accela_app_id: Optional[str] = None
    accela_app_secret: Optional[str] = None
    is_active: Optional[bool] = None


class CountyResponse(BaseModel):
    """Model for county response."""
    id: str
    name: str
    accela_environment: str
    accela_app_id: str
    status: Optional[str] = None
    last_pull_at: Optional[datetime] = None
    token_expires_at: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class CountyTestRequest(BaseModel):
    """Model for testing county connection."""
    accela_environment: str
    accela_app_id: str
    accela_app_secret: str
