"""Lead management endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.lead import CreateLeadsRequest, UpdateLeadNotesRequest, SyncLeadsRequest, LeadResponse, LeadListRequest
from app.services.summit_client import SummitClient

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.get("", response_model=dict)
async def list_leads(
    county_id: str = None,
    sync_status: str = None,
    lead_tier: str = None,  # NEW: Filter by HOT, WARM, COOL, COLD
    min_score: int = None,  # NEW: Minimum lead score (0-100)
    is_qualified: bool = None,  # NEW: Filter by qualification status
    limit: int = 50,
    offset: int = 0,
    db=Depends(get_db)
):
    """
    List leads with filters.

    New property-based filters:
    - lead_tier: HOT (15+ years), WARM (10-15 years), COOL (5-10 years), COLD (<5 years)
    - min_score: Minimum lead score (0-100)
    - is_qualified: Only leads with HVAC 5+ years old

    Returns leads with property and permit data joined.
    """
    try:
        # Join with properties and permits
        query = db.table("leads").select("*, properties(*), permits(*)")

        if county_id:
            query = query.eq("county_id", county_id)

        if sync_status:
            query = query.eq("summit_sync_status", sync_status)

        # NEW: Property-based filters
        if lead_tier:
            query = query.eq("lead_tier", lead_tier.upper())

        if min_score is not None:
            query = query.gte("lead_score", min_score)

        if is_qualified is not None:
            # Filter through properties table
            # Note: This requires property_id to be populated
            query = query.not_.is_("property_id", "null")

        # Order by lead score (highest first)
        result = query.order("lead_score", desc=True).range(offset, offset + limit - 1).execute()

        return {
            "success": True,
            "data": {
                "leads": result.data,
                "count": len(result.data)
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

        # Create Summit client
        summit = SummitClient()

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
