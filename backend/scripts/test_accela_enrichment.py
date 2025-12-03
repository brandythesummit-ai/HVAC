"""
Test script to verify Accela API enrichment calls (addresses, owners, parcels).
This helps diagnose the "garbage in" problem where enrichment data is empty.
"""
import asyncio
import sys
import os
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import get_db

db = get_db()
from app.services.encryption import encryption_service
from app.services.accela_client import AccelaClient


async def test_enrichment():
    """Test Accela API enrichment endpoints for addresses, owners, parcels."""

    print("=" * 70)
    print("ACCELA ENRICHMENT API TEST")
    print("=" * 70)
    print("Goal: Determine if enrichment APIs return data or empty arrays")
    print("=" * 70)

    # Get county and app settings
    county_id = "40c7d6e3-fd9e-48f1-9d3e-4d372d6001cc"

    # Fetch county
    county_result = db.table("counties").select("*").eq("id", county_id).execute()
    if not county_result.data:
        print("ERROR: County not found")
        return

    county = county_result.data[0]
    print(f"\nCounty: {county['name']}")
    print(f"County Code: {county['county_code']}")

    # Fetch app settings
    app_result = db.table("app_settings").select("*").eq("key", "accela").execute()
    if not app_result.data:
        print("ERROR: App settings not found")
        return

    app_settings = app_result.data[0]
    app_id = app_settings['app_id']
    app_secret = encryption_service.decrypt(app_settings['app_secret'])

    print(f"App ID: {app_id}")

    # Create Accela client
    client = AccelaClient(
        app_id=app_id,
        app_secret=app_secret,
        county_code=county['county_code'],
        refresh_token=county['refresh_token']
    )

    # Test record IDs - get a few from the database
    permits_result = db.table("permits").select("accela_record_id, owner_name, property_address").eq("county_id", county_id).limit(3).execute()

    if not permits_result.data:
        print("ERROR: No permits found in database")
        return

    print(f"\nFound {len(permits_result.data)} permits to test")

    # Test each permit
    for i, permit in enumerate(permits_result.data):
        record_id = permit['accela_record_id']
        print(f"\n{'='*70}")
        print(f"TEST {i+1}: Record ID: {record_id}")
        print(f"Database has: owner_name={permit['owner_name']}, address={permit['property_address']}")
        print("="*70)

        # 1. Test GET /v4/records/{id} - base record
        print(f"\n1. GET /v4/records/{record_id}")
        try:
            # This isn't a standard method, so we'll use _make_request directly
            base_record = await client._make_request(
                "GET",
                f"/v4/records/{record_id}",
                request_type="enrichment"
            )
            result_data = base_record.get("result", [])
            if result_data:
                print(f"   ✅ Got base record data")
                # Print key fields
                if isinstance(result_data, list) and result_data:
                    record = result_data[0]
                else:
                    record = result_data
                print(f"   Fields: {list(record.keys())[:10]}...")  # First 10 fields
            else:
                print(f"   ❌ Empty result")
                print(f"   Full response: {json.dumps(base_record, indent=2)[:500]}")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

        # 2. Test GET /v4/records/{id}/addresses
        print(f"\n2. GET /v4/records/{record_id}/addresses")
        try:
            addresses = await client.get_addresses(record_id)
            if addresses:
                print(f"   ✅ Got {len(addresses)} address(es)")
                print(f"   First address: {json.dumps(addresses[0], indent=2)[:300]}")
            else:
                print(f"   ❌ Empty array returned (no addresses)")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

        # 3. Test GET /v4/records/{id}/owners
        print(f"\n3. GET /v4/records/{record_id}/owners")
        try:
            owners = await client.get_owners(record_id)
            if owners:
                print(f"   ✅ Got {len(owners)} owner(s)")
                print(f"   First owner: {json.dumps(owners[0], indent=2)[:300]}")
            else:
                print(f"   ❌ Empty array returned (no owners)")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

        # 4. Test GET /v4/records/{id}/parcels
        print(f"\n4. GET /v4/records/{record_id}/parcels")
        try:
            parcels = await client.get_parcels(record_id)
            if parcels:
                print(f"   ✅ Got {len(parcels)} parcel(s)")
                print(f"   First parcel: {json.dumps(parcels[0], indent=2)[:300]}")
            else:
                print(f"   ❌ Empty array returned (no parcels)")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("""
If all enrichment calls return empty arrays:
  → Problem is API-side (county config, OAuth scope, or API limitation)

If enrichment calls return data:
  → Problem is code-side (parsing/extraction logic)

Next steps depend on findings above.
""")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_enrichment())
