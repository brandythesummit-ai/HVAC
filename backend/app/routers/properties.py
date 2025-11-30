"""
Properties Router

API endpoints for property-level data and lead scoring.
Properties aggregate permits by address and track the most recent HVAC installation.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, date
from supabase import Client

from app.database import get_db

router = APIRouter(prefix="/api/properties", tags=["Properties"])


class PropertyResponse(BaseModel):
    """Response model for a property."""
    id: str
    county_id: str
    normalized_address: str
    street_number: Optional[str] = None
    street_name: Optional[str] = None
    street_suffix: Optional[str] = None
    unit_number: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    most_recent_hvac_permit_id: Optional[str] = None
    most_recent_hvac_date: Optional[date] = None
    hvac_age_years: Optional[int] = None
    lead_score: Optional[int] = None
    lead_tier: Optional[str] = None
    is_qualified: Optional[bool] = None
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    owner_email: Optional[str] = None
    parcel_number: Optional[str] = None
    year_built: Optional[int] = None
    lot_size_sqft: Optional[int] = None
    land_value: Optional[float] = None
    improved_value: Optional[float] = None
    total_property_value: Optional[float] = None
    total_hvac_permits: int = 1
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PropertyListResponse(BaseModel):
    """Response model for property list."""
    properties: List[PropertyResponse]
    total: int
    page: int
    page_size: int


@router.get("/counties/{county_id}/properties", response_model=PropertyListResponse)
async def list_properties(
    county_id: str,
    lead_tier: Optional[str] = Query(None, description="Filter by lead tier: HOT, WARM, COOL, COLD"),
    is_qualified: Optional[bool] = Query(None, description="Filter by qualified status (5+ years)"),
    min_score: Optional[int] = Query(None, description="Minimum lead score (0-100)", ge=0, le=100),
    max_score: Optional[int] = Query(None, description="Maximum lead score (0-100)", ge=0, le=100),
    city: Optional[str] = Query(None, description="Filter by city"),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(50, description="Items per page", ge=1, le=500),
    db: Client = Depends(get_db)
):
    """
    List properties for a county with filtering and pagination.

    Filters:
    - lead_tier: HOT (15+ years), WARM (10-15 years), COOL (5-10 years), COLD (<5 years)
    - is_qualified: Only properties with HVAC 5+ years old
    - min_score/max_score: Lead score range (0-100)
    - city: Filter by city name

    Returns properties ordered by lead_score (highest first).
    """
    # Verify county exists
    county_result = db.table('counties').select('id').eq('id', county_id).execute()
    if not county_result.data:
        raise HTTPException(status_code=404, detail="County not found")

    # Build query
    query = db.table('properties').select('*', count='exact').eq('county_id', county_id)

    # Apply filters
    if lead_tier:
        query = query.eq('lead_tier', lead_tier.upper())

    if is_qualified is not None:
        query = query.eq('is_qualified', is_qualified)

    if min_score is not None:
        query = query.gte('lead_score', min_score)

    if max_score is not None:
        query = query.lte('lead_score', max_score)

    if city:
        query = query.ilike('city', f"%{city}%")

    # Order by lead score (highest first)
    query = query.order('lead_score', desc=True)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.range(offset, offset + page_size - 1)

    result = query.execute()

    return {
        "properties": result.data or [],
        "total": result.count or 0,
        "page": page,
        "page_size": page_size
    }


@router.get("/properties/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: str,
    db: Client = Depends(get_db)
):
    """
    Get a specific property by ID.

    Returns complete property details including:
    - Address components
    - HVAC age and installation date
    - Lead scoring (score, tier, is_qualified)
    - Owner information
    - Property metadata (year_built, value, lot_size, etc.)
    - Total HVAC permits count
    """
    result = db.table('properties').select('*').eq('id', property_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Property not found")

    return result.data[0]


@router.get("/properties/{property_id}/permits")
async def get_property_permits(
    property_id: str,
    db: Client = Depends(get_db)
):
    """
    Get all HVAC permits for a property.

    Returns the permit history for a property, showing:
    - All HVAC installations over time
    - Which permit is most recent (used for lead scoring)
    - Complete permit details for each installation
    """
    # Verify property exists
    property_result = db.table('properties').select('normalized_address, county_id').eq('id', property_id).execute()

    if not property_result.data:
        raise HTTPException(status_code=404, detail="Property not found")

    property_record = property_result.data[0]

    # Get all permits for this address
    # NOTE: This requires matching by normalized_address
    # We'll need to search permits table for matching addresses
    permits_result = db.table('permits') \
        .select('*') \
        .eq('county_id', property_record['county_id']) \
        .order('opened_date', desc=True) \
        .execute()

    # Filter permits by normalized address
    # (This is a client-side filter since we don't store normalized_address in permits table)
    from app.services.address_normalizer import AddressNormalizer

    matching_permits = []
    target_address = property_record['normalized_address']

    for permit in permits_result.data or []:
        if permit.get('property_address'):
            normalized = AddressNormalizer.normalize(permit['property_address'])
            if normalized == target_address:
                matching_permits.append(permit)

    return {
        "property_id": property_id,
        "normalized_address": property_record['normalized_address'],
        "total_permits": len(matching_permits),
        "permits": matching_permits
    }


@router.get("/counties/{county_id}/properties/stats")
async def get_property_stats(
    county_id: str,
    db: Client = Depends(get_db)
):
    """
    Get property statistics for a county.

    Returns:
    - Total properties
    - Properties by lead tier (HOT, WARM, COOL, COLD)
    - Qualified vs. unqualified breakdown
    - Average HVAC age
    - Average lead score
    """
    # Verify county exists
    county_result = db.table('counties').select('id, county_name').eq('id', county_id).execute()
    if not county_result.data:
        raise HTTPException(status_code=404, detail="County not found")

    # Get all properties for county
    properties_result = db.table('properties').select('*').eq('county_id', county_id).execute()
    properties = properties_result.data or []

    if not properties:
        return {
            "county_id": county_id,
            "county_name": county_result.data[0]['county_name'],
            "total_properties": 0,
            "by_tier": {"HOT": 0, "WARM": 0, "COOL": 0, "COLD": 0},
            "qualified": 0,
            "unqualified": 0,
            "average_hvac_age": 0,
            "average_lead_score": 0
        }

    # Calculate stats
    by_tier = {"HOT": 0, "WARM": 0, "COOL": 0, "COLD": 0}
    qualified = 0
    unqualified = 0
    total_hvac_age = 0
    total_lead_score = 0

    for prop in properties:
        tier = prop.get('lead_tier')
        if tier in by_tier:
            by_tier[tier] += 1

        if prop.get('is_qualified'):
            qualified += 1
        else:
            unqualified += 1

        if prop.get('hvac_age_years') is not None:
            total_hvac_age += prop['hvac_age_years']

        if prop.get('lead_score') is not None:
            total_lead_score += prop['lead_score']

    total = len(properties)

    return {
        "county_id": county_id,
        "county_name": county_result.data[0]['county_name'],
        "total_properties": total,
        "by_tier": by_tier,
        "qualified": qualified,
        "unqualified": unqualified,
        "average_hvac_age": round(total_hvac_age / total, 1) if total > 0 else 0,
        "average_lead_score": round(total_lead_score / total, 1) if total > 0 else 0
    }
