"""Permit management endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from datetime import datetime

from app.database import get_db
from app.models.permit import PullPermitsRequest, PermitResponse, PermitListRequest
from app.services.accela_client import AccelaClient
from app.services.encryption import encryption_service

router = APIRouter(prefix="/api", tags=["permits"])


def extract_permit_data(permit: Dict[str, Any], addresses: List[Dict], owners: List[Dict], parcels: List[Dict]) -> Dict[str, Any]:
    """Extract and structure permit data from Accela response."""
    extracted = {
        "permit_type": permit.get("type", {}).get("value", ""),
        "description": permit.get("description", ""),
        "status": permit.get("status", {}).get("value", ""),
    }

    # Extract permit custom ID (e.g., HC-BTR-25-0300825)
    custom_id = permit.get("customId", "")
    if custom_id:
        extracted["custom_id"] = custom_id

    # Extract dates
    opened_date = permit.get("openedDate")
    if opened_date:
        try:
            extracted["opened_date"] = datetime.fromisoformat(opened_date.replace('Z', '+00:00')).date().isoformat()
        except:
            extracted["opened_date"] = None

    # Extract job value
    job_value = permit.get("jobValue")
    if job_value:
        try:
            extracted["job_value"] = float(job_value) if float(job_value) > 0 else None
        except (ValueError, TypeError):
            extracted["job_value"] = None

    # Extract address
    if addresses:
        addr = addresses[0]
        state = addr.get("state", "")
        # Handle state as dict with 'value' or 'text' keys, or as string
        if isinstance(state, dict):
            state = state.get("value") or state.get("text", "")

        parts = [
            str(addr.get("streetStart", "")),
            str(addr.get("streetName", "")),
            str(addr.get("city", "")),
            str(state) if state else "",
            str(addr.get("zip", ""))
        ]
        extracted["property_address"] = " ".join(filter(None, parts))

        # Extract neighborhood
        neighborhood = addr.get("neighborhood", "")
        if neighborhood:
            extracted["neighborhood"] = neighborhood

    # Extract owner info
    if owners:
        owner = owners[0]
        extracted["owner_name"] = owner.get("fullName", "")
        extracted["owner_phone"] = owner.get("phone", "")
        extracted["owner_email"] = owner.get("email", "")

    # Extract parcel data (property info)
    if parcels:
        parcel = parcels[0]

        # Note: yearBuilt doesn't exist in Accela parcel response
        # Leaving as None for now
        extracted["year_built"] = None

        # Use parcelArea (in acres) - convert to square feet
        try:
            parcel_area_acres = float(parcel.get("parcelArea", 0))
            if parcel_area_acres > 0:
                # Convert acres to square feet (1 acre = 43,560 sq ft)
                extracted["lot_size_sqft"] = int(parcel_area_acres * 43560)
            else:
                extracted["lot_size_sqft"] = None
        except (ValueError, TypeError):
            extracted["lot_size_sqft"] = None

        # Land value (lot value)
        try:
            extracted["land_value"] = float(parcel.get("landValue", 0)) or None
        except (ValueError, TypeError):
            extracted["land_value"] = None

        # Improved value (building value)
        try:
            extracted["improved_value"] = float(parcel.get("improvedValue", 0)) or None
        except (ValueError, TypeError):
            extracted["improved_value"] = None

        # Total property value (land + improvements)
        if extracted.get("land_value") and extracted.get("improved_value"):
            extracted["total_property_value"] = extracted["land_value"] + extracted["improved_value"]
        elif extracted.get("land_value"):
            extracted["total_property_value"] = extracted["land_value"]
        elif extracted.get("improved_value"):
            extracted["total_property_value"] = extracted["improved_value"]
        else:
            extracted["total_property_value"] = None

        # Parcel number
        parcel_number = parcel.get("parcelNumber", "")
        if parcel_number:
            extracted["parcel_number"] = parcel_number

        # Subdivision
        subdivision = parcel.get("subdivision", {})
        if isinstance(subdivision, dict):
            subdivision = subdivision.get("text") or subdivision.get("value", "")
        if subdivision:
            extracted["subdivision"] = subdivision

        # Legal description
        legal_desc = parcel.get("legalDescription", "")
        if legal_desc:
            extracted["legal_description"] = legal_desc

    return extracted


@router.post("/counties/{county_id}/pull-permits", response_model=dict)
async def pull_permits(county_id: str, request: PullPermitsRequest, db=Depends(get_db)):
    """Pull permits from Accela and enrich with property data."""
    try:
        print(f"🔍 [PULL PERMITS] Starting permit pull for county {county_id}")

        # Get county
        result = db.table("counties").select("*").eq("id", county_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="County not found")

        county = result.data[0]
        print(f"✅ [PULL PERMITS] Found county: {county.get('name')} ({county.get('county_code')})")

        # Verify county has refresh token
        if not county.get("refresh_token"):
            raise HTTPException(status_code=400, detail="County not authorized. Please authorize with Accela first.")

        # Get global Accela app credentials
        app_settings = db.table("app_settings").select("*").eq("key", "accela").execute()
        if not app_settings.data or not app_settings.data[0].get("app_id"):
            raise HTTPException(
                status_code=400,
                detail="Accela app credentials not configured. Please configure in Settings."
            )

        app_id = app_settings.data[0]["app_id"]
        app_secret_encrypted = app_settings.data[0]["app_secret"]
        app_secret = encryption_service.decrypt(app_secret_encrypted)

        print(f"✅ [PULL PERMITS] Retrieved app credentials")

        # Create Accela client
        client = AccelaClient(
            app_id=app_id,
            app_secret=app_secret,
            county_code=county["county_code"],
            refresh_token=county.get("refresh_token", ""),
            access_token=county.get("access_token", ""),
            token_expires_at=county.get("token_expires_at", "")
        )

        # Try API-level filtering first, fall back to client-side if needed
        hvac_type = "Residential Mechanical Trade Permit"

        print(f"🔍 [PULL PERMITS] Trying API-level type filter: {hvac_type}")

        # First attempt: API-level filtering
        accela_response = await client.get_permits(
            date_from=request.date_from,
            date_to=request.date_to,
            limit=request.limit,
            status=request.status,
            permit_type=hvac_type
        )

        all_permits = accela_response["permits"]

        print(f"✅ [PULL PERMITS] API filter returned {len(all_permits)} permits")

        # If API filtering returned 0, fall back to client-side filtering
        if len(all_permits) == 0:
            print(f"⚠️  [PULL PERMITS] API filter returned 0 - falling back to client-side filtering")

            # Pull ALL Building permits (no type filter)
            accela_response = await client.get_permits(
                date_from=request.date_from,
                date_to=request.date_to,
                limit=request.limit,
                status=request.status,
                permit_type=None  # No API filter
            )

            all_permits = accela_response["permits"]
            print(f"✅ [PULL PERMITS] Retrieved {len(all_permits)} total Building permits")

            # Client-side filter for HVAC/Mechanical
            hvac_permits = []
            for permit in all_permits:
                permit_type = permit.get("type", {})
                type_value = permit_type.get("value", "") if isinstance(permit_type, dict) else str(permit_type)

                # Match: Mechanical, HVAC, Mech (case-insensitive)
                if any(keyword.lower() in type_value.lower() for keyword in ["mechanical", "hvac", "mech"]):
                    hvac_permits.append(permit)

            print(f"✅ [PULL PERMITS] Client-side filter: {len(all_permits)} total → {len(hvac_permits)} HVAC/Mechanical")
            filtering_method = "client-side fallback"
        else:
            # API filtering worked
            hvac_permits = all_permits
            filtering_method = "API"
            print(f"✅ [PULL PERMITS] API filtering successful: {len(hvac_permits)} HVAC permits")

        query_info = accela_response["query_info"]
        debug_info = accela_response["debug_info"]

        # Enrich each permit
        saved_permits = []
        failed_saves = []
        saved_count = 0

        for permit in hvac_permits:
            record_id = permit.get("id")
            if not record_id:
                continue

            # Get enrichment data
            addresses = await client.get_addresses(record_id)
            owners = await client.get_owners(record_id)
            parcels = await client.get_parcels(record_id)

            # Extract structured data
            extracted = extract_permit_data(permit, addresses, owners, parcels)

            # Build complete permit record
            permit_data = {
                "county_id": county_id,
                "accela_record_id": record_id,
                "raw_data": {
                    "permit": permit,
                    "addresses": addresses,
                    "owners": owners,
                    "parcels": parcels
                },
                "created_at": datetime.utcnow().isoformat(),
                **extracted
            }

            # Try to save permit (insert or update if exists)
            try:
                # Check if permit already exists
                existing = db.table("permits").select("id").eq("county_id", county_id).eq("accela_record_id", record_id).execute()

                if existing.data:
                    # Update existing
                    update_result = db.table("permits").update(permit_data).eq("accela_record_id", record_id).execute()
                    if update_result.data:
                        saved_permits.append(update_result.data[0])
                        saved_count += 1
                    else:
                        saved_permits.append(None)
                        failed_saves.append({
                            "record_id": record_id,
                            "error": "Update returned no data"
                        })
                else:
                    # Insert new
                    insert_result = db.table("permits").insert(permit_data).execute()
                    if insert_result.data:
                        saved_permits.append(insert_result.data[0])
                        saved_count += 1
                    else:
                        saved_permits.append(None)
                        failed_saves.append({
                            "record_id": record_id,
                            "error": "Insert returned no data"
                        })
            except Exception as save_error:
                # Record failure
                saved_permits.append(None)
                failed_saves.append({
                    "record_id": record_id,
                    "error": str(save_error)
                })
                print(f"⚠️  [PULL PERMITS] Failed to save permit {record_id}: {str(save_error)}")

        # Auto-create leads for each saved permit
        created_leads = []
        failed_leads = []

        for permit in saved_permits:
            if not permit:
                continue

            # Check if lead already exists for this permit
            existing_lead = db.table("leads").select("id").eq("permit_id", permit["id"]).execute()

            if not existing_lead.data:
                # Create new lead with pending status
                lead_data = {
                    "permit_id": permit["id"],
                    "county_id": county_id,
                    "summit_sync_status": "pending",
                    "created_at": datetime.utcnow().isoformat()
                }

                try:
                    lead_result = db.table("leads").insert(lead_data).execute()
                    if lead_result.data:
                        created_leads.append(lead_result.data[0])
                    else:
                        failed_leads.append({
                            "permit_id": permit["id"],
                            "error": "Insert returned no data"
                        })
                except Exception as lead_error:
                    failed_leads.append({
                        "permit_id": permit["id"],
                        "error": str(lead_error)
                    })
                    print(f"⚠️  [PULL PERMITS] Failed to create lead for permit {permit['id']}: {str(lead_error)}")

        print(f"✅ [PULL PERMITS] Created {len(created_leads)} new leads")

        # Update county last_pull_at and store updated tokens
        # Update last pull timestamp
        update_data = {
            "last_pull_at": datetime.utcnow().isoformat()
        }
        db.table("counties").update(update_data).eq("id", county_id).execute()

        saved_count = len([p for p in saved_permits if p])
        print(f"✅ [PULL PERMITS] Complete! Total: {len(hvac_permits)}, HVAC: {len(hvac_permits)}, Saved: {saved_count}, Leads: {len(created_leads)}")

        # Calculate helpful metrics
        from datetime import datetime as dt
        date_from_obj = dt.fromisoformat(request.date_from)
        date_to_obj = dt.fromisoformat(request.date_to)
        date_range_days = (date_to_obj - date_from_obj).days

        # Generate suggestions if 0 results
        suggestions = []
        if len(hvac_permits) == 0:
            suggestions.append(f"No permits found with type: '{hvac_type}'")
            suggestions.append("Try widening your date range")
            if request.status:
                suggestions.append(f"Try removing the '{request.status}' status filter")
            if date_range_days < 30:
                suggestions.append("Date range is narrow (< 30 days) - try a longer period")
            suggestions.append("Verify this exact permit type exists in Accela for this county")

        return {
            "success": True,
            "data": {
                # Existing fields
                "total_pulled": len(hvac_permits),
                "hvac_permits": len(hvac_permits),
                "saved": saved_count,
                "leads_created": len(created_leads),
                "failed_saves": len(failed_saves),
                "failed_leads": len(failed_leads),
                "permits": saved_permits,
                "leads": created_leads,
                "errors": {
                    "save_failures": failed_saves,
                    "lead_failures": failed_leads
                } if (failed_saves or failed_leads) else None,

                # NEW: Diagnostic fields
                "query_info": {
                    "date_from": request.date_from,
                    "date_to": request.date_to,
                    "date_range_days": date_range_days,
                    "limit": request.limit,
                    "status_filter": request.status,
                    "permit_type_filter": hvac_type if filtering_method == "API" else "Mechanical/HVAC/Mech",
                    "filtering_method": filtering_method,
                    "county_name": county.get("name"),
                    "county_code": county.get("county_code")
                },
                "suggestions": suggestions if suggestions else None,
                "debug_info": debug_info
            },
            "error": None
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [PULL PERMITS] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


@router.get("/permits", response_model=dict)
async def list_permits(
    county_id: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 50,
    offset: int = 0,
    db=Depends(get_db)
):
    """List permits with filters."""
    try:
        query = db.table("permits").select("*")

        if county_id:
            query = query.eq("county_id", county_id)

        if date_from:
            query = query.gte("opened_date", date_from)

        if date_to:
            query = query.lte("opened_date", date_to)

        result = query.order("opened_date", desc=True).range(offset, offset + limit - 1).execute()

        return {
            "success": True,
            "data": {
                "permits": result.data,
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


@router.get("/permits/{permit_id}", response_model=dict)
async def get_permit(permit_id: str, db=Depends(get_db)):
    """Get single permit with full details."""
    try:
        result = db.table("permits").select("*").eq("id", permit_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Permit not found")

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
