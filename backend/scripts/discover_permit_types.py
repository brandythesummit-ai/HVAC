"""
Discover available permit types for a county from Accela API.

Usage:
    python -m scripts.discover_permit_types <county_id>

Example:
    python -m scripts.discover_permit_types 3788febd-97bd-4dba-a94c-151967a0e91f
"""
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from supabase import create_client
from app.services.encryption import EncryptionService
from app.config import settings

encryption = EncryptionService()


async def get_access_token(county_id: str) -> tuple[str, str, str]:
    """Get access token for a county."""
    db = create_client(settings.supabase_url, settings.supabase_key)

    # Get county info
    county_result = db.table('counties').select('*').eq('id', county_id).execute()
    if not county_result.data:
        raise ValueError(f"County {county_id} not found")

    county = county_result.data[0]
    county_code = county.get('county_code')

    if not county_code:
        raise ValueError(f"County {county['name']} has no county_code configured")

    if not county.get('refresh_token'):
        raise ValueError(f"County {county['name']} has no OAuth credentials")

    # Get app settings
    app_result = db.table('app_settings').select('*').eq('key', 'accela').execute()
    if not app_result.data:
        raise ValueError("Accela app settings not found")

    app_settings = app_result.data[0]
    app_id = app_settings.get('app_id')
    app_secret = encryption.decrypt(app_settings.get('app_secret'))

    # Decrypt refresh token
    refresh_token = encryption.decrypt(county['refresh_token'])

    # Exchange refresh token for access token
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://auth.accela.com/oauth2/token",
            data={
                "grant_type": "refresh_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "refresh_token": refresh_token,
                "agency_name": county_code,
                "environment": "PROD"
            }
        )
        response.raise_for_status()
        token_data = response.json()

    return token_data['access_token'], app_id, county_code


async def discover_permit_types(county_id: str):
    """Discover all permit types by sampling Building records."""
    print(f"\n🔍 Discovering permit types for county: {county_id}\n")

    # Get access token
    access_token, app_id, county_code = await get_access_token(county_id)
    print(f"✅ Got access token for agency: {county_code}")

    # Fetch recent Building records to discover available types
    print("\n📥 Fetching sample of Building records...")

    async with httpx.AsyncClient(timeout=60) as client:
        # Search for Building records from recent period
        search_body = {
            "module": "Building"
        }

        response = await client.post(
            "https://apis.accela.com/v4/search/records",
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-accela-appid": app_id,
                "Content-Type": "application/json"
            },
            params={"limit": 200, "offset": 0},
            json=search_body
        )

        if response.status_code != 200:
            print(f"❌ Search API Error: {response.status_code}")
            print(response.text)
            return

        data = response.json()
        records = data.get('result', [])

        print(f"✅ Got {len(records)} sample records")

        # Extract unique permit types
        type_counts = {}
        for record in records:
            record_type = record.get('type', {})
            type_value = record_type.get('value', 'Unknown')
            type_text = record_type.get('text', type_value)

            if type_value not in type_counts:
                type_counts[type_value] = {
                    'count': 0,
                    'text': type_text,
                    'sample_id': record.get('customId', 'N/A')
                }
            type_counts[type_value]['count'] += 1

        # Display all types sorted by count
        print("\n" + "=" * 80)
        print("ALL PERMIT TYPES FOUND IN SAMPLE (sorted by frequency)")
        print("=" * 80)

        hvac_candidates = []

        for type_value, info in sorted(type_counts.items(), key=lambda x: -x[1]['count']):
            print(f"\n  [{info['count']:3d}] {type_value}")
            print(f"        Text: {info['text']}")
            print(f"        Sample: {info['sample_id']}")

            # Check if it's HVAC-related
            lower_val = type_value.lower() if type_value else ''
            lower_text = info['text'].lower() if info['text'] else ''

            hvac_keywords = ['mechanical', 'hvac', 'air', 'heat', 'cool', 'conditioning', 'furnace', 'ac', 'a/c']
            if any(kw in lower_val or kw in lower_text for kw in hvac_keywords):
                hvac_candidates.append({
                    'value': type_value,
                    'text': info['text'],
                    'count': info['count']
                })

        # Highlight HVAC candidates
        if hvac_candidates:
            print("\n" + "=" * 80)
            print("🔥 HVAC-RELATED TYPES (likely candidates for permit_type)")
            print("=" * 80)
            for t in hvac_candidates:
                print(f"\n  ⭐ VALUE: {t['value']}")
                print(f"     TEXT:  {t['text']}")
                print(f"     COUNT: {t['count']} in sample")
        else:
            print("\n⚠️  No obvious HVAC-related types found. Review types above manually.")
            print("    Look for: Mechanical, Trade, HVAC, Residential Mechanical, etc.")

        print("\n" + "=" * 80)
        print("To set the permit_type for this county, run:")
        print("=" * 80)
        print(f"""
UPDATE counties
SET permit_type = '<TYPE_VALUE_HERE>'
WHERE id = '{county_id}';
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.discover_permit_types <county_id>")
        print("\nTo find county IDs, check the database or use the API.")
        sys.exit(1)

    county_id = sys.argv[1]
    asyncio.run(discover_permit_types(county_id))
