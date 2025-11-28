"""Permit Pydantic models."""
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime, date


class PullPermitsRequest(BaseModel):
    """Model for pulling permits from Accela."""
    date_from: str = Field(..., description="Start date (YYYY-MM-DD)")
    date_to: str = Field(..., description="End date (YYYY-MM-DD)")
    limit: int = Field(100, description="Max results", ge=1, le=1000)
    status: Optional[str] = Field(None, description="Status filter (e.g., 'Finaled')")


class PermitResponse(BaseModel):
    """Model for permit response."""
    id: str
    county_id: str
    accela_record_id: str
    permit_type: Optional[str] = None
    description: Optional[str] = None
    opened_date: Optional[date] = None
    status: Optional[str] = None
    job_value: Optional[float] = None
    property_address: Optional[str] = None
    year_built: Optional[int] = None
    square_footage: Optional[int] = None
    property_value: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    lot_size: Optional[float] = None
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    owner_email: Optional[str] = None
    raw_data: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PermitListRequest(BaseModel):
    """Model for listing permits."""
    county_id: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)
