#!/usr/bin/env python3
"""
One-time migration script to convert existing permits to property-centric structure.
Run this once to populate the properties table and update leads with property_id.
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from app.services.property_aggregator import PropertyAggregator

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Get Supabase credentials from environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # Using anon key with RLS policies

async def migrate_permits_to_properties():
    """Process all permits through PropertyAggregator to create properties."""

    # Initialize Supabase client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Initialize PropertyAggregator
    aggregator = PropertyAggregator(db=supabase)

    print("Starting property-centric migration...")
    print("=" * 60)

    # Get all permits
    print("\n📊 Fetching all permits...")
    result = supabase.table("permits").select("*").execute()
    permits = result.data
    print(f"Found {len(permits)} permits to process")

    # Get current property count
    props_before = supabase.table("properties").select("id", count="exact").execute()
    print(f"Properties before migration: {props_before.count}")

    # Process permits in batches
    batch_size = 50
    total_processed = 0
    properties_created = 0
    leads_created = 0

    for i in range(0, len(permits), batch_size):
        batch = permits[i:i + batch_size]
        print(f"\n🔄 Processing batch {i//batch_size + 1} ({len(batch)} permits)...")

        for permit in batch:
            try:
                # Process through PropertyAggregator
                property_id, lead_id, was_created = await aggregator.process_permit(
                    permit_data=permit,
                    county_id=permit.get('county_id')
                )

                total_processed += 1

                if was_created:
                    properties_created += 1
                    leads_created += 1

                if total_processed % 100 == 0:
                    print(f"  Processed {total_processed}/{len(permits)} permits...")

            except Exception as e:
                print(f"  ❌ Error processing permit {permit.get('id')}: {str(e)}")
                continue

    # Get final counts
    props_after = supabase.table("properties").select("id", count="exact").execute()
    leads_with_property = supabase.table("leads").select("id", count="exact").not_.is_("property_id", "null").execute()

    print("\n" + "=" * 60)
    print("✅ Migration Complete!")
    print("=" * 60)
    print(f"Permits processed: {total_processed}/{len(permits)}")
    print(f"Properties before: {props_before.count}")
    print(f"Properties after: {props_after.count}")
    print(f"Properties created in migration: {properties_created}")
    print(f"Leads with property_id: {leads_with_property.count}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(migrate_permits_to_properties())
