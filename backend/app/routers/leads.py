"""Lead management endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import logging

from app.database import get_db
from app.models.lead import CreateLeadsRequest, UpdateLeadNotesRequest, SyncLeadsRequest, LeadResponse, LeadListRequest
from app.services.summit_client import SummitClient
from app.services.lead_status_machine import (
    InvalidTransitionError,
    compute_transition,
)

router = APIRouter(prefix="/api/leads", tags=["leads"])
logger = logging.getLogger(__name__)


class UpdateLeadStatusRequest(BaseModel):
    new_status: str = Field(..., description="Target status from the lead state machine")
    note: Optional[str] = Field(None, description="Optional rationale for the transition")


@router.get("", response_model=dict)
async def list_leads(
    # County and sync filters
    county_id: str = None,
    sync_status: str = None,

    # Lead tier and scoring filters. lead_tier accepts either a single
    # tier (HOT) or a comma-separated list (HOT,WARM) — parsed below.
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

    # FilterBar (post-pivot UI) filters. Comma-separated lists are
    # parsed into Python lists and mapped to PostgREST `in.(...)`.
    status: str = None,
    date_from: str = None,  # permit most_recent_hvac_date lower bound
    date_to: str = None,
    zip: str = None,
    owner_occupied: bool = None,
    permit_type: str = None,
    search: str = None,  # free-text over address + owner_name

    # Bbox viewport filter — required when the Map queries at low zoom
    # to avoid scanning all 400K residential parcels. Supply all four
    # or none; partial bbox is ignored.
    bbox_ne_lat: float = None,
    bbox_ne_lng: float = None,
    bbox_sw_lat: float = None,
    bbox_sw_lng: float = None,

    # Residential-only gate (parcels-first default TRUE).
    residential_only: bool = True,

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
    - limit: Results per page (default 50, max 20000 for map view)
    - offset: Pagination offset

    Returns leads with property and permit data joined, plus total count.
    """
    try:
        # Validate limit. Map view needs the full dataset (~12K leads)
        # to plot pins without paginated fetching; cap at 20000 to prevent
        # accidental unbounded queries.
        if limit > 20000:
            limit = 20000

        # Parse comma-separated lists from FilterBar multi-selects.
        tier_list = [t.strip().upper() for t in lead_tier.split(",") if t.strip()] if lead_tier else None
        status_list = [s.strip().upper() for s in status.split(",") if s.strip()] if status else None

        def apply_filters(q):
            """Apply every filter to the given query-builder. Same semantics
            for the main query and the count query — single source of truth."""
            if county_id:
                q = q.eq("county_id", county_id)
            if sync_status:
                q = q.eq("summit_sync_status", sync_status)
            if tier_list:
                q = q.in_("lead_tier", tier_list) if len(tier_list) > 1 else q.eq("lead_tier", tier_list[0])
            if status_list:
                q = q.in_("lead_status", status_list) if len(status_list) > 1 else q.eq("lead_status", status_list[0])
            if min_score is not None:
                q = q.gte("lead_score", min_score)
            if max_score is not None:
                q = q.lte("lead_score", max_score)
            if is_qualified is True:
                q = q.not_.is_("property_id", "null")
            elif is_qualified is False:
                q = q.is_("property_id", "null")
            if min_hvac_age is not None:
                q = q.gte("properties.hvac_age_years", min_hvac_age)
            if max_hvac_age is not None:
                q = q.lte("properties.hvac_age_years", max_hvac_age)
            if contact_completeness:
                q = q.eq("properties.contact_completeness", contact_completeness.lower())
            if affluence_tier:
                q = q.eq("properties.affluence_tier", affluence_tier.lower())
            if recommended_pipeline:
                q = q.eq("properties.recommended_pipeline", recommended_pipeline.lower())
            if min_pipeline_confidence is not None:
                q = q.gte("properties.pipeline_confidence", min_pipeline_confidence)
            if min_property_value is not None:
                q = q.gte("properties.total_property_value", min_property_value)
            if max_property_value is not None:
                q = q.lte("properties.total_property_value", max_property_value)
            if has_phone is True:
                q = q.not_.is_("properties.owner_phone", "null")
            elif has_phone is False:
                q = q.is_("properties.owner_phone", "null")
            if has_email is True:
                q = q.not_.is_("properties.owner_email", "null")
            elif has_email is False:
                q = q.is_("properties.owner_email", "null")
            if year_built_min is not None:
                q = q.gte("properties.year_built", year_built_min)
            if year_built_max is not None:
                q = q.lte("properties.year_built", year_built_max)
            if city:
                q = q.ilike("properties.city", f"%{city}%")
            if state:
                q = q.eq("properties.state", state.upper())
            # FilterBar additions
            if date_from:
                q = q.gte("properties.most_recent_hvac_date", date_from)
            if date_to:
                q = q.lte("properties.most_recent_hvac_date", date_to)
            if zip:
                q = q.eq("properties.zip_code", zip)
            # owner_occupied / permit_type: the FilterBar sends these, but
            # the properties schema doesn't track either today. Accepted
            # silently so the URL stays clean until Signal B / permit-level
            # tagging lands. Ignoring in filter = no-op, no false matches.
            if search:
                # Free-text across normalized_address and owner_name via PostgREST `or`.
                esc = search.replace(",", " ").replace("(", "").replace(")", "")
                q = q.or_(
                    f"normalized_address.ilike.%{esc}%,owner_name.ilike.%{esc}%",
                    reference_table="properties",
                )

            # Bbox viewport filter for the map. All 4 corners must be
            # present; otherwise skipped (the list view doesn't care).
            if (bbox_ne_lat is not None and bbox_ne_lng is not None
                    and bbox_sw_lat is not None and bbox_sw_lng is not None):
                q = q.gte("properties.latitude", bbox_sw_lat)
                q = q.lte("properties.latitude", bbox_ne_lat)
                q = q.gte("properties.longitude", bbox_sw_lng)
                q = q.lte("properties.longitude", bbox_ne_lng)

            if residential_only:
                q = q.eq("properties.is_residential", True)
            return q

        # PostgREST filter-on-foreign-table semantics: with a plain to-one
        # join `properties(*)`, filters like `gte('properties.hvac_age_years', 20)`
        # are applied but don't *prune* rows — they just affect the embedded
        # fields. Using the `!inner` qualifier promotes the join to an INNER
        # join so the filter actually constrains the result set. Without
        # this, age/zip/date filters are no-ops.
        needs_inner_join = any([
            min_hvac_age is not None,
            max_hvac_age is not None,
            contact_completeness,
            affluence_tier,
            recommended_pipeline,
            min_pipeline_confidence is not None,
            min_property_value is not None,
            max_property_value is not None,
            has_phone is not None,
            has_email is not None,
            year_built_min is not None,
            year_built_max is not None,
            city,
            state,
            date_from,
            date_to,
            zip,
            search,
            residential_only,
            bbox_ne_lat is not None,
        ])
        properties_projection = "properties!inner(*)" if needs_inner_join else "properties(*)"
        count_properties_projection = (
            "properties!inner(id)" if needs_inner_join else "properties(id)"
        )

        query = apply_filters(db.table("leads").select(f"*, {properties_projection}"))

        # Count query: `planned` uses Postgres planner row estimates
        # instead of a full scan. At ~500K lead rows, `exact` counts
        # hit Supabase's statement timeout. `planned` is ~accurate
        # enough for the UI's "N total" display; if the client needs
        # exactness (rare) they can request it via count_mode param.
        try:
            count_query = apply_filters(
                db.table("leads").select(f"id, {count_properties_projection}", count="planned")
            )
            count_result = count_query.execute()
            total_count = count_result.count if hasattr(count_result, 'count') and count_result.count is not None else 0
        except Exception:
            # If the planner estimate path errors (rare), fall back to
            # omitting the total count. The listing still works.
            total_count = 0

        # Multi-factor sorting: tier → score
        # Order: HOT before WARM before COOL before COLD
        # Within tier: highest score first
        # Note: Cannot order by related table columns (properties.*) in Supabase
        ordered = query.order("lead_tier", desc=False).order("lead_score", desc=True)

        # PostgREST caps any single request at ~1000 rows. When the caller
        # asks for more (e.g., MapPage requests 12K leads so every pin
        # plots), we page through internally and concatenate. Without this
        # the Map would silently truncate at ~1000 pins.
        SUPABASE_PAGE = 1000
        collected: list = []
        rel_offset = 0
        while rel_offset < limit:
            page_size = min(SUPABASE_PAGE, limit - rel_offset)
            abs_start = offset + rel_offset
            abs_end = abs_start + page_size - 1
            page = ordered.range(abs_start, abs_end).execute()
            chunk = page.data or []
            collected.extend(chunk)
            if len(chunk) < page_size:
                break  # end of dataset reached
            rel_offset += page_size

        return {
            "success": True,
            "data": {
                "leads": collected,
                "count": len(collected),
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


@router.get("/by-property/{property_id}", response_model=dict)
async def get_lead_by_property(property_id: str, db=Depends(get_db)):
    """Fetch the lead for a given property_id, with full property context.

    MapPage pins carry a property_id (not a lead_id), so clicks need a
    property→lead resolver. In parcels-first each residential property
    has exactly one lead row; we return that row with properties joined.
    """
    try:
        result = (
            db.table("leads")
            .select("*, property:properties(*)")
            .eq("property_id", property_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Lead not found for property")
        lead = result.data[0]
        prop = lead.pop("property", None) or {}
        merged = {**prop, **lead}
        return {"success": True, "data": merged, "error": None}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_lead_by_property failed")
        return {"success": False, "data": None, "error": str(e)}


@router.get("/{lead_id}", response_model=dict)
async def get_lead(lead_id: str, db=Depends(get_db)):
    """Fetch a single lead with its full property + permit context.

    Used by the DetailSheet to show all available fields when a buddy
    taps a pin or row.
    """
    try:
        result = (
            db.table("leads")
            .select("*, property:properties(*)")
            .eq("id", lead_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Lead not found")
        lead = result.data[0]
        # Flatten property fields onto the lead for convenience
        prop = lead.pop("property", None) or {}
        merged = {**prop, **lead}
        return {"success": True, "data": merged, "error": None}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_lead failed")
        return {"success": False, "data": None, "error": str(e)}


@router.patch("/{lead_id}/status", response_model=dict)
async def update_lead_status(
    lead_id: str,
    request: UpdateLeadStatusRequest,
    db=Depends(get_db),
):
    """Transition a lead through the M12 state machine.

    Server-computes cooldown timestamps and whether to push to GHL.
    Invalid transitions return 400 with a descriptive message.
    """
    try:
        lookup = db.table("leads").select("lead_status").eq("id", lead_id).execute()
        if not lookup.data:
            raise HTTPException(status_code=404, detail="Lead not found")
        current_status = lookup.data[0].get("lead_status") or "NEW"

        cooldown_rows = db.table("lead_status_cooldowns").select("key, days").execute()
        cooldowns = {r["key"]: r["days"] for r in (cooldown_rows.data or [])}

        try:
            result = compute_transition(current_status, request.new_status, cooldowns)
        except InvalidTransitionError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        update_payload = result.to_update_dict()
        if request.note:
            update_payload["status_note"] = request.note

        updated = db.table("leads").update(update_payload).eq("id", lead_id).execute()
        if not updated.data:
            raise HTTPException(status_code=500, detail="Failed to update lead status")

        # TODO(M22 follow-up): if result.should_push_to_ghl, invoke the
        # GHL Contact+Opportunity upsert from M13 here. V1 surfaces the
        # flag via the response so the frontend can optionally trigger a
        # manual Push-to-GHL button; full auto-push wired up in deploy.
        return {
            "success": True,
            "data": {
                **updated.data[0],
                "should_push_to_ghl": result.should_push_to_ghl,
            },
            "error": None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("update_lead_status failed")
        return {
            "success": False,
            "data": None,
            "error": str(e),
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
