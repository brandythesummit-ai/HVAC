"""
Test script to verify Accela API date filtering behavior.
Tests whether the API respects openedDateFrom/openedDateTo parameters.
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import get_db

db = get_db()
from app.services.encryption import encryption_service
from app.services.accela_client import AccelaClient


async def test_date_filtering():
    """Test Accela API date filtering with different date ranges."""

    print("=" * 60)
    print("ACCELA DATE FILTER TEST")
    print("=" * 60)

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

    # Test different date ranges
    test_ranges = [
        ("1995-01-01", "1995-12-31", "Old historical (1995)"),
        ("2000-01-01", "2000-12-31", "Historical (2000)"),
        ("2010-01-01", "2010-12-31", "Medium age (2010)"),
        ("2020-01-01", "2020-12-31", "Recent (2020)"),
        ("2021-11-01", "2021-12-31", "Where permits exist (Nov-Dec 2021)"),
        ("2024-01-01", "2024-12-31", "Very recent (2024)"),
    ]

    print("\n" + "=" * 60)
    print("TESTING DATE RANGES")
    print("=" * 60)

    for date_from, date_to, description in test_ranges:
        print(f"\n{'='*40}")
        print(f"Testing: {description}")
        print(f"Date range: {date_from} to {date_to}")
        print("="*40)

        try:
            result = await client.get_permits(
                date_from=date_from,
                date_to=date_to,
                limit=10  # Just get a small sample
            )

            permits = result.get('permits', [])
            print(f"Returned: {len(permits)} permits")

            if permits:
                # Check what dates were actually returned
                dates_found = set()
                for permit in permits[:5]:  # Check first 5
                    opened_date = permit.get('openedDate', 'N/A')
                    dates_found.add(opened_date[:10] if opened_date else 'N/A')

                print(f"Sample dates returned: {sorted(dates_found)}")

                # Check if dates match requested range
                in_range = all(
                    date_from <= d[:10] <= date_to
                    for d in dates_found
                    if d != 'N/A' and len(d) >= 10
                )

                if in_range:
                    print("STATUS: Dates MATCH requested range")
                else:
                    print("STATUS: Dates DO NOT MATCH requested range!")
                    print(f"   Expected: {date_from} to {date_to}")
                    print(f"   Got: {sorted(dates_found)}")
            else:
                print("STATUS: No permits returned")

        except Exception as e:
            print(f"ERROR: {e}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_date_filtering())
