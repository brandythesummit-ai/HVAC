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

    # Extract dates
    opened_date = permit.get("openedDate")
    if opened_date:
        try:
            extracted["opened_date"] = datetime.fromisoformat(opened_date.replace('Z', '+00:00')).date().isoformat()
        except:
            extracted["opened_date"] = None

    # Extract job value
    if "value" in permit:
        try:
            extracted["job_value"] = float(permit["value"])
        except (ValueError, TypeError):
            extracted["job_value"] = None

    # Extract address
    if addresses:
        addr = addresses[0]
        parts = [
            addr.get("streetStart", ""),
            addr.get("streetName", ""),
            addr.get("city", ""),
            addr.get("state", ""),
            addr.get("zip", "")
        ]
        extracted["property_address"] = " ".join(filter(None, parts))

    # Extract owner info
    if owners:
        owner = owners[0]
        extracted["owner_name"] = owner.get("fullName", "")
        extracted["owner_phone"] = owner.get("phone", "")
        extracted["owner_email"] = owner.get("email", "")

    # Extract parcel data (property info)
    if parcels:
        parcel = parcels[0]
        try:
            extracted["year_built"] = int(parcel.get("yearBuilt", 0)) or None
        except (ValueError, TypeError):
            extracted["year_built"] = None

        try:
            extracted["square_footage"] = int(parcel.get("landArea", 0)) or None
        except (ValueError, TypeError):
            extracted["square_footage"] = None

        try:
            extracted["property_value"] = float(parcel.get("landValue", 0)) or None
        except (ValueError, TypeError):
            extracted["property_value"] = None

        try:
            extracted["lot_size"] = float(parcel.get("lotSize", 0)) or None
        except (ValueError, TypeError):
            extracted["lot_size"] = None

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

        print(f"🔍 [PULL PERMITS] Created Accela client, pulling permits...")

        # Pull permits
        permits = await client.get_permits(
            date_from=request.date_from,
            date_to=request.date_to,
            limit=request.limit,
            status=request.status
        )

        print(f"✅ [PULL PERMITS] Retrieved {len(permits)} permits from Accela")

        # Filter for Mechanical permits
        hvac_permits = [p for p in permits if "Mechanical" in p.get("type", {}).get("value", "")]
        print(f"🔍 [PULL PERMITS] Filtered to {len(hvac_permits)} HVAC permits")

        # Enrich each permit
        saved_permits = []
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

            # Check if permit already exists
            existing = db.table("permits").select("id").eq("accela_record_id", record_id).execute()

            if existing.data:
                # Update existing
                update_result = db.table("permits").update(permit_data).eq("accela_record_id", record_id).execute()
                saved_permits.append(update_result.data[0] if update_result.data else None)
            else:
                # Insert new
                insert_result = db.table("permits").insert(permit_data).execute()
                saved_permits.append(insert_result.data[0] if insert_result.data else None)

        # Auto-create leads for each saved permit
        created_leads = []
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
                except Exception as lead_error:
                    print(f"⚠️  [PULL PERMITS] Failed to create lead for permit {permit['id']}: {str(lead_error)}")

        print(f"✅ [PULL PERMITS] Created {len(created_leads)} new leads")

        # Update county last_pull_at and store updated tokens
        update_data = {
            "last_pull_at": datetime.utcnow().isoformat()
        }

        # Update access token if it was refreshed
        if client._access_token:
            update_data["access_token"] = client._access_token
        if client._token_expires_at:
            update_data["token_expires_at"] = client._token_expires_at

        db.table("counties").update(update_data).eq("id", county_id).execute()

        saved_count = len([p for p in saved_permits if p])
        print(f"✅ [PULL PERMITS] Complete! Total: {len(permits)}, HVAC: {len(hvac_permits)}, Saved: {saved_count}, Leads: {len(created_leads)}")

        return {
            "success": True,
            "data": {
                "total_pulled": len(permits),
                "hvac_permits": len(hvac_permits),
                "saved": saved_count,
                "leads_created": len(created_leads),
                "permits": saved_permits,
                "leads": created_leads
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
