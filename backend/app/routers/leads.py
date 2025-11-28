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
    limit: int = 50,
    offset: int = 0,
    db=Depends(get_db)
):
    """List leads with filters."""
    try:
        query = db.table("leads").select("*, permits(*)")

        if county_id:
            query = query.eq("county_id", county_id)

        if sync_status:
            query = query.eq("summit_sync_status", sync_status)

        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

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
    """Convert permits to leads."""
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
    """Sync leads to Summit.AI CRM."""
    try:
        # Get leads to sync
        query = db.table("leads").select("*, permits(*)")

        if request.lead_ids:
            query = query.in_("id", request.lead_ids)
        else:
            # Sync all pending
            query = query.eq("summit_sync_status", "pending")

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
            permit = lead.get("permits")
            if not permit:
                continue

            try:
                # Prepare contact data
                owner_name = permit.get("owner_name", "")
                name_parts = owner_name.split() if owner_name else ["", ""]

                contact_data = {
                    "firstName": name_parts[0] if len(name_parts) > 0 else "",
                    "lastName": name_parts[-1] if len(name_parts) > 1 else "",
                    "email": permit.get("owner_email", ""),
                    "phone": permit.get("owner_phone", ""),
                    "address1": permit.get("property_address", ""),
                    "customField": {
                        "permit_id": permit.get("accela_record_id", ""),
                        "permit_date": permit.get("opened_date", ""),
                        "year_built": permit.get("year_built"),
                        "square_footage": permit.get("square_footage"),
                        "property_value": permit.get("property_value"),
                    },
                    "tags": ["hvac-lead"]
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
