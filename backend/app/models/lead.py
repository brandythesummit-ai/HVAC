"""Lead Pydantic models."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CreateLeadsRequest(BaseModel):
    """Model for creating leads from permits."""
    permit_ids: List[str] = Field(..., description="List of permit IDs")


class UpdateLeadNotesRequest(BaseModel):
    """Model for updating lead notes."""
    notes: str = Field(..., description="Lead notes")


class SyncLeadsRequest(BaseModel):
    """Model for syncing leads to Summit.AI."""
    lead_ids: Optional[List[str]] = Field(None, description="Lead IDs (empty = sync all pending)")


class LeadResponse(BaseModel):
    """Model for lead response."""
    id: str
    permit_id: str
    county_id: str
    summit_sync_status: str = "pending"
    summit_contact_id: Optional[str] = None
    summit_synced_at: Optional[datetime] = None
    sync_error_message: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    # Include permit data
    permit: Optional[dict] = None

    class Config:
        from_attributes = True


class LeadListRequest(BaseModel):
    """Model for listing leads."""
    county_id: Optional[str] = None
    sync_status: Optional[str] = None
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)
