"""Lead management endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
import logging

from app.database import get_db
from app.models.lead import CreateLeadsRequest, UpdateLeadNotesRequest, SyncLeadsRequest, LeadResponse, LeadListRequest
from app.services.summit_client import SummitClient

router = APIRouter(prefix="/api/leads", tags=["leads"])
logger = logging.getLogger(__name__)


@router.get("", response_model=dict)
async def list_leads(
    # County and sync filters
    county_id: str = None,
    sync_status: str = None,

    # Lead tier and scoring filters
    lead_tier: str = None,
    min_score: int = None,
    max_score: int = None,
    is_qualified: bool = None,

    # HVAC age filters
    min_hvac_age: int = None,
    max_hvac_age: int = None,

    # Pipeline intelligence filters
    contact_completeness: str = None,  # complete, partial, minimal
    affluence_tier: str = None,  # ultra_high, high, medium, standard
    recommended_pipeline: str = None,  # hot_call, premium_mailer, nurture_drip, retargeting_ads, cold_storage
    min_pipeline_confidence: int = None,

    # Property value filters
    min_property_value: float = None,
    max_property_value: float = None,

    # Contact info filters
    has_phone: bool = None,
    has_email: bool = None,

    # Property details filters
    year_built_min: int = None,
    year_built_max: int = None,
    city: str = None,
    state: str = None,

    # Pagination
    limit: int = 50,
    offset: int = 0,

    db=Depends(get_db)
):
    """
    List leads with comprehensive filtering.

    Filters:
    - county_id: Filter by county UUID
    - sync_status: pending, synced, failed
    - lead_tier: HOT, WARM, COOL, COLD
    - min_score/max_score: Lead score range (0-100)
    - min_hvac_age/max_hvac_age: HVAC system age range in years
    - contact_completeness: complete (phone+email), partial (phone OR email), minimal (neither)
    - affluence_tier: ultra_high ($500K+), high ($350K+), medium ($200K+), standard
    - recommended_pipeline: hot_call, premium_mailer, nurture_drip, retargeting_ads, cold_storage
    - min_pipeline_confidence: Minimum confidence score (50-95)
    - min_property_value/max_property_value: Property value range
    - has_phone/has_email: Filter by contact info availability
    - year_built_min/year_built_max: Year built range
    - city/state: Geographic filters
    - limit: Results per page (default 50, max 200)
    - offset: Pagination offset

    Returns leads with property and permit data joined, plus total count.
    """
    try:
        # Validate limit
        if limit > 200:
            limit = 200

        # Build the base query for filtering
        query = db.table("leads").select("*, properties(*), permits(*)")

        # County filter
        if county_id:
            query = query.eq("county_id", county_id)

        # Sync status filter
        if sync_status:
            query = query.eq("summit_sync_status", sync_status)

        # Lead tier filter
        if lead_tier:
            query = query.eq("lead_tier", lead_tier.upper())

        # Score range filters
        if min_score is not None:
            query = query.gte("lead_score", min_score)
        if max_score is not None:
            query = query.lte("lead_score", max_score)

        # Qualification filter
        if is_qualified is True:
            query = query.not_.is_("property_id", "null")
        elif is_qualified is False:
            query = query.is_("property_id", "null")
        # If is_qualified is None, don't apply any filter

        # HVAC age filters (filter through properties)
        if min_hvac_age is not None:
            query = query.gte("properties.hvac_age_years", min_hvac_age)
        if max_hvac_age is not None:
            query = query.lte("properties.hvac_age_years", max_hvac_age)

        # Contact completeness filter
        if contact_completeness:
            query = query.eq("properties.contact_completeness", contact_completeness.lower())

        # Affluence tier filter
        if affluence_tier:
            query = query.eq("properties.affluence_tier", affluence_tier.lower())

        # Recommended pipeline filter
        if recommended_pipeline:
            query = query.eq("properties.recommended_pipeline", recommended_pipeline.lower())

        # Pipeline confidence filter
        if min_pipeline_confidence is not None:
            query = query.gte("properties.pipeline_confidence", min_pipeline_confidence)

        # Property value range filters
        if min_property_value is not None:
            query = query.gte("properties.total_property_value", min_property_value)
        if max_property_value is not None:
            query = query.lte("properties.total_property_value", max_property_value)

        # Contact info filters
        if has_phone is not None:
            if has_phone:
                query = query.not_.is_("properties.owner_phone", "null")
            else:
                query = query.is_("properties.owner_phone", "null")

        if has_email is not None:
            if has_email:
                query = query.not_.is_("properties.owner_email", "null")
            else:
                query = query.is_("properties.owner_email", "null")

        # Year built range filters
        if year_built_min is not None:
            query = query.gte("properties.year_built", year_built_min)
        if year_built_max is not None:
            query = query.lte("properties.year_built", year_built_max)

        # Geographic filters
        if city:
            query = query.ilike("properties.city", f"%{city}%")
        if state:
            query = query.eq("properties.state", state.upper())

        # Get total count first (before pagination)
        # Build a count-only query with same filters including property join
        count_query = db.table("leads").select("id, properties(id)", count="exact")

        # Apply ALL the same filters to the count query
        if county_id:
            count_query = count_query.eq("county_id", county_id)
        if sync_status:
            count_query = count_query.eq("summit_sync_status", sync_status)
        if lead_tier:
            count_query = count_query.eq("lead_tier", lead_tier.upper())
        if min_score is not None:
            count_query = count_query.gte("lead_score", min_score)
        if max_score is not None:
            count_query = count_query.lte("lead_score", max_score)
        if is_qualified is True:
            count_query = count_query.not_.is_("property_id", "null")
        elif is_qualified is False:
            count_query = count_query.is_("property_id", "null")
        # If is_qualified is None, don't apply any filter

        # HVAC age filters
        if min_hvac_age is not None:
            count_query = count_query.gte("properties.hvac_age_years", min_hvac_age)
        if max_hvac_age is not None:
            count_query = count_query.lte("properties.hvac_age_years", max_hvac_age)

        # Contact completeness filter
        if contact_completeness:
            count_query = count_query.eq("properties.contact_completeness", contact_completeness.lower())

        # Affluence tier filter
        if affluence_tier:
            count_query = count_query.eq("properties.affluence_tier", affluence_tier.lower())

        # Recommended pipeline filter
        if recommended_pipeline:
            count_query = count_query.eq("properties.recommended_pipeline", recommended_pipeline.lower())

        # Pipeline confidence filter
        if min_pipeline_confidence is not None:
            count_query = count_query.gte("properties.pipeline_confidence", min_pipeline_confidence)

        # Property value range filters
        if min_property_value is not None:
            count_query = count_query.gte("properties.total_property_value", min_property_value)
        if max_property_value is not None:
            count_query = count_query.lte("properties.total_property_value", max_property_value)

        # Contact info filters
        if has_phone is not None:
            if has_phone:
                count_query = count_query.not_.is_("properties.owner_phone", "null")
            else:
                count_query = count_query.is_("properties.owner_phone", "null")
        if has_email is not None:
            if has_email:
                count_query = count_query.not_.is_("properties.owner_email", "null")
            else:
                count_query = count_query.is_("properties.owner_email", "null")

        # Year built range filters
        if year_built_min is not None:
            count_query = count_query.gte("properties.year_built", year_built_min)
        if year_built_max is not None:
            count_query = count_query.lte("properties.year_built", year_built_max)

        # Geographic filters
        if city:
            count_query = count_query.ilike("properties.city", f"%{city}%")
        if state:
            count_query = count_query.eq("properties.state", state.upper())

        count_result = count_query.execute()
        total_count = count_result.count if hasattr(count_result, 'count') and count_result.count is not None else 0

        # Multi-factor sorting: tier → score
        # Order: HOT before WARM before COOL before COLD
        # Within tier: highest score first
        # Note: Cannot order by related table columns (properties.*) in Supabase
        result = query.order("lead_tier", desc=False) \
                      .order("lead_score", desc=True) \
                      .range(offset, offset + limit - 1) \
                      .execute()

        return {
            "success": True,
            "data": {
                "leads": result.data,
                "count": len(result.data),
                "total": total_count,
                "limit": limit,
                "offset": offset
            },
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


@router.post("/create-from-permits", response_model=dict)
async def create_leads_from_permits(request: CreateLeadsRequest, db=Depends(get_db)):
    """
    Convert permits to leads.

    DEPRECATED: Leads are now created automatically by the PropertyAggregator
    when permits are processed. This endpoint is kept for backward compatibility
    but will be removed in a future version.
    """
    try:
        created_leads = []

        for permit_id in request.permit_ids:
            # Get permit
            permit_result = db.table("permits").select("*").eq("id", permit_id).execute()

            if not permit_result.data:
                continue

            permit = permit_result.data[0]

            # Check if lead already exists
            existing = db.table("leads").select("id").eq("permit_id", permit_id).execute()

            if existing.data:
                # Already a lead, skip
                continue

            # Create lead
            lead_data = {
                "permit_id": permit_id,
                "county_id": permit["county_id"],
                "summit_sync_status": "pending",
                "created_at": datetime.utcnow().isoformat()
            }

            result = db.table("leads").insert(lead_data).execute()

            if result.data:
                created_leads.append(result.data[0])

        return {
            "success": True,
            "data": {
                "created": len(created_leads),
                "leads": created_leads
            },
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


@router.put("/{lead_id}/notes", response_model=dict)
async def update_lead_notes(lead_id: str, request: UpdateLeadNotesRequest, db=Depends(get_db)):
    """Update lead notes."""
    try:
        result = db.table("leads").update({
            "notes": request.notes
        }).eq("id", lead_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Lead not found")

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


@router.post("/sync-to-summit", response_model=dict)
async def sync_leads_to_summit(request: SyncLeadsRequest, db=Depends(get_db)):
    """
    Sync leads to Summit.AI CRM.

    Now uses property-based data with lead scoring information.
    """
    try:
        # Get Summit credentials from database (same as connection test)
        agency_result = db.table("agencies").select("*").limit(1).execute()

        if not agency_result.data:
            raise HTTPException(
                status_code=400,
                detail="No agency configured with Summit.AI credentials"
            )

        agency = agency_result.data[0]
        access_token = agency.get("summit_access_token")
        location_id = agency.get("summit_location_id")

        if not access_token or not location_id:
            raise HTTPException(
                status_code=400,
                detail="Summit.AI credentials not configured. Please configure in Settings."
            )

        # Get leads to sync with properties and permits
        query = db.table("leads").select("*, properties(*), permits(*)")

        if request.lead_ids:
            query = query.in_("id", request.lead_ids)
        else:
            # Sync all pending HOT and WARM leads
            query = query.eq("summit_sync_status", "pending").in_("lead_tier", ["HOT", "WARM"])

        leads_result = query.execute()

        if not leads_result.data:
            return {
                "success": True,
                "data": {
                    "synced": 0,
                    "failed": 0,
                    "results": []
                },
                "error": None
            }

        # Create Summit client with DATABASE credentials (explicit, not env vars)
        summit = SummitClient(
            access_token=access_token,
            location_id=location_id
        )

        synced_count = 0
        failed_count = 0
        sync_results = []

        for lead in leads_result.data:
            # Use property data (denormalized from most recent permit)
            property_data = lead.get("properties")
            if not property_data:
                # Fallback to permit data if no property
                property_data = lead.get("permits", {})

            try:
                # Prepare contact data with lead scoring info
                owner_name = property_data.get("owner_name", "")
                name_parts = owner_name.split() if owner_name else ["", ""]

                # Build tags based on lead tier
                tags = ["hvac-lead", f"tier-{lead.get('lead_tier', 'UNKNOWN').lower()}"]

                contact_data = {
                    "firstName": name_parts[0] if len(name_parts) > 0 else "",
                    "lastName": name_parts[-1] if len(name_parts) > 1 else "",
                    "email": property_data.get("owner_email", ""),
                    "phone": property_data.get("owner_phone", ""),
                    "address1": property_data.get("normalized_address", ""),
                    "customField": {
                        "lead_score": lead.get("lead_score"),
                        "lead_tier": lead.get("lead_tier"),
                        "hvac_age_years": property_data.get("hvac_age_years"),
                        "most_recent_hvac_date": property_data.get("most_recent_hvac_date"),
                        "qualification_reason": lead.get("qualification_reason"),
                        "year_built": property_data.get("year_built"),
                        "property_value": property_data.get("total_property_value"),
                        "total_hvac_permits": property_data.get("total_hvac_permits"),
                    },
                    "tags": tags
                }

                # Search for existing contact
                existing_contact = None
                if contact_data["phone"]:
                    existing_contact = await summit.search_contact(phone=contact_data["phone"])
                elif contact_data["email"]:
                    existing_contact = await summit.search_contact(email=contact_data["email"])

                if existing_contact:
                    # Update existing
                    contact_id = existing_contact["id"]
                    await summit.update_contact(contact_id, contact_data)
                    await summit.add_tags(contact_id, contact_data["tags"])
                else:
                    # Create new
                    result = await summit.create_contact(contact_data)
                    contact_id = result.get("contact", {}).get("id")

                # Update lead
                db.table("leads").update({
                    "summit_sync_status": "synced",
                    "summit_contact_id": contact_id,
                    "summit_synced_at": datetime.utcnow().isoformat(),
                    "sync_error_message": None
                }).eq("id", lead["id"]).execute()

                synced_count += 1
                sync_results.append({
                    "lead_id": lead["id"],
                    "status": "synced",
                    "contact_id": contact_id
                })

            except Exception as sync_error:
                # Update lead with error
                db.table("leads").update({
                    "summit_sync_status": "failed",
                    "sync_error_message": str(sync_error)
                }).eq("id", lead["id"]).execute()

                failed_count += 1
                sync_results.append({
                    "lead_id": lead["id"],
                    "status": "failed",
                    "error": str(sync_error)
                })

        return {
            "success": True,
            "data": {
                "synced": synced_count,
                "failed": failed_count,
                "results": sync_results
            },
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


@router.delete("/{lead_id}", response_model=dict)
async def delete_lead(lead_id: str, db=Depends(get_db)):
    """
    Delete a lead by ID.

    This only deletes the lead record. Associated property and permit records
    are preserved as they contain valuable historical data.

    The property may be re-qualified and generate a new lead in future permit pulls
    if it still meets qualification criteria (HVAC ≥ 5 years old).
    """
    try:
        # Check if lead exists first
        check_result = db.table("leads").select("id, property_id").eq("id", lead_id).execute()

        if not check_result.data:
            raise HTTPException(status_code=404, detail="Lead not found")

        lead_data = check_result.data[0]
        property_id = lead_data.get("property_id")

        # Delete the lead
        delete_result = db.table("leads").delete().eq("id", lead_id).execute()

        return {
            "success": True,
            "data": {
                "message": "Lead deleted successfully",
                "id": lead_id,
                "property_id": property_id,
                "note": "Property and permit records preserved. Property may re-qualify in future permit pulls."
            },
            "error": None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting lead {lead_id}: {str(e)}")
        return {
            "success": False,
            "data": None,
            "error": f"Failed to delete lead: {str(e)}"
        }
