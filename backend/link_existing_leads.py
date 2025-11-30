#!/usr/bin/env python3
"""
Link existing leads to their corresponding properties based on address matching.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from app.services.address_normalizer import AddressNormalizer

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Get Supabase credentials from environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def link_leads_to_properties():
    """Update existing leads to link them to properties based on address matching."""

    # Initialize Supabase client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("Starting lead-to-property linking...")
    print("=" * 60)

    # Get all leads without property_id
    print("\n📊 Fetching leads without property_id...")
    result = supabase.table("leads").select("*").is_("property_id", "null").execute()
    leads_without_property = result.data
    print(f"Found {len(leads_without_property)} leads without property_id")

    # Get all properties
    print("\n📊 Fetching all properties...")
    result = supabase.table("properties").select("*").execute()
    properties = result.data
    print(f"Found {len(properties)} properties")

    # Create address lookup for properties grouped by county
    property_lookup = {}
    for prop in properties:
        county_id = prop['county_id']
        normalized_address = prop['normalized_address']

        if county_id not in property_lookup:
            property_lookup[county_id] = {}

        property_lookup[county_id][normalized_address] = prop

    print(f"\n🔗 Matching leads to properties...")

    matched = 0
    unmatched = 0
    updated = 0

    for lead in leads_without_property:
        try:
            # Get the associated permit for this lead
            permit_id = lead.get('permit_id')
            if not permit_id:
                print(f"  ⚠️  Lead {lead['id']} has no permit_id, skipping")
                unmatched += 1
                continue

            # Fetch the permit
            permit_result = supabase.table("permits").select("*").eq("id", permit_id).execute()
            if not permit_result.data:
                print(f"  ⚠️  Permit {permit_id} not found for lead {lead['id']}, skipping")
                unmatched += 1
                continue

            permit = permit_result.data[0]

            # Extract and normalize the address
            raw_address = permit.get('property_address')
            if not raw_address:
                print(f"  ⚠️  Permit {permit_id} has no address, skipping")
                unmatched += 1
                continue

            parsed_address = AddressNormalizer.parse_address(raw_address)
            normalized_address = parsed_address.normalized_address
            county_id = permit.get('county_id')

            # Look up property by county_id and normalized_address
            if county_id in property_lookup and normalized_address in property_lookup[county_id]:
                property_record = property_lookup[county_id][normalized_address]
                property_id = property_record['id']

                # Update the lead with property_id
                supabase.table("leads").update({
                    "property_id": property_id
                }).eq("id", lead['id']).execute()

                matched += 1
                updated += 1

                if updated % 10 == 0:
                    print(f"  Updated {updated} leads...")
            else:
                unmatched += 1
                if unmatched <= 5:  # Only print first 5 unmatched
                    print(f"  ⚠️  No property found for address: {normalized_address} (county: {county_id})")

        except Exception as e:
            print(f"  ❌ Error processing lead {lead.get('id')}: {str(e)}")
            unmatched += 1
            continue

    # Get final counts
    leads_with_property = supabase.table("leads").select("id", count="exact").not_.is_("property_id", "null").execute()
    leads_without_property_final = supabase.table("leads").select("id", count="exact").is_("property_id", "null").execute()

    print("\n" + "=" * 60)
    print("✅ Linking Complete!")
    print("=" * 60)
    print(f"Leads matched to properties: {matched}")
    print(f"Leads without matching property: {unmatched}")
    print(f"Leads updated: {updated}")
    print(f"Final - Leads with property_id: {leads_with_property.count}")
    print(f"Final - Leads without property_id: {leads_without_property_final.count}")
    print("=" * 60)

if __name__ == "__main__":
    link_leads_to_properties()
