"""
Platform Detection Script for Florida Counties - API-Based Approach

Uses Accela's public /v4/agencies directory API to get canonical agency codes,
then validates each county's portal URL.

Platforms detected:
- Accela (with serviceProviderCode from official directory)
- EnerGov (Tyler Technologies)
- eTRAKiT
- Tyler Technologies
- OpenGov
- Custom (county-specific system)
- Unknown (unable to determine)

Usage:
    python -m backend.scripts.detect_florida_platforms

Requirements:
    - SUPABASE_URL and SUPABASE_KEY environment variables
    - Internet connection
"""

import asyncio
import re
import os
import sys
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import httpx
from supabase import create_client, Client

# Platform detection signatures (non-Accela platforms)
PLATFORM_SIGNATURES = {
    'EnerGov': [
        'energov.tylertech.com',
        'energov.com',
        'Tyler EnerGov',
        'EnerGov Portal'
    ],
    'eTRAKiT': [
        'etrakit.com',
        'eTRAKiT',
        'Central Square eTRAKiT'
    ],
    'Tyler': [
        'tylertech.com/products/eden',
        'Tyler Eden',
        'Tyler Technologies',
        'mytylertechnologies.com'
    ],
    'OpenGov': [
        'opengov.com/products/permitting',
        'OpenGov Permitting',
        'opengov permitting'
    ]
}

# County URL patterns to try for finding portals
COUNTY_URL_PATTERNS = [
    'https://{county}county.gov',
    'https://www.{county}county.gov',
    'https://{county}countygov.com',
    'https://www.{county}.fl.gov',
    'https://{county}fl.gov',
]

# Building department paths
BUILDING_DEPT_PATHS = [
    '/building',
    '/building-department',
    '/building-permits',
    '/permits',
    '/development-services',
    '/planning-and-zoning',
    '/community-development',
]


class PlatformDetector:
    """Detects permit platform and extracts agency codes for Florida counties."""

    def __init__(self):
        """Initialize Supabase client and HTTP client."""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables required")

        self.supabase: Client = create_client(supabase_url, supabase_key)

        # Get Accela app ID from database for API calls
        self.accela_app_id = self._get_accela_app_id()

        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; HVAC-LeadGen-Bot/1.0)',
                'x-accela-appid': self.accela_app_id if self.accela_app_id else ''
            }
        )

        # Cache of Florida Accela agencies from API
        self.fl_accela_agencies = []

        # Statistics
        self.stats = {
            'total_processed': 0,
            'platforms_detected': {},
            'agency_codes_found': 0,
            'api_validated': 0,
            'errors': 0
        }

    def _get_accela_app_id(self) -> Optional[str]:
        """Fetch Accela app ID from database settings."""
        try:
            result = self.supabase.table('app_settings').select('app_id').eq('key', 'accela').execute()
            if result.data and len(result.data) > 0:
                return result.data[0].get('app_id')
            return None
        except Exception as e:
            print(f"⚠️  Warning: Could not fetch Accela app ID: {e}")
            return None

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()

    async def fetch_accela_agencies(self) -> List[Dict]:
        """
        Fetch all Florida agencies from Accela's public directory API.

        Note: API returns all agencies at once (no real pagination).
        Returns list of agencies with: serviceProviderCode, displayName, state, hostedACA, enabled
        """
        print("\n📡 Fetching Florida agencies from Accela directory API...")

        try:
            # API returns all agencies at once despite limit/offset params
            url = "https://apis.accela.com/v4/agencies?limit=10000"
            response = await self.http_client.get(url)

            if response.status_code != 200:
                print(f"  ❌ API returned status {response.status_code}")
                return []

            data = response.json()
            all_agencies = data.get('result', [])

            # Filter to Florida agencies only
            fl_agencies = [a for a in all_agencies if a.get('state') == 'FL']

            print(f"  📄 Fetched {len(all_agencies)} total agencies")
            print(f"\n✅ Found {len(fl_agencies)} Accela agencies in Florida")
            return fl_agencies

        except Exception as e:
            print(f"  ❌ Error fetching agencies: {str(e)}")
            return []

    # Manual mapping of known Florida Accela counties (from /v4/agencies API)
    KNOWN_ACCELA_COUNTIES = {
        'Hillsborough County': 'HCFL',
        'Lee County': 'LEECO',
        'Martin County': 'MARTINCO',
        'Escambia County': 'Escambia',
        'Pinellas County': 'PINELLAS',
        'Pasco County': 'PASCO',
        'Osceola County': 'OSCEOLA',
        'Charlotte County': 'BOCC',
        'Brevard County': 'BREVARD',
        'Manatee County': 'MANATEE',
        'Leon County': 'LEONCO',
        'Polk County': 'POLKCO',
        'Sarasota County': 'SARASOTACO',
    }

    def match_county_to_agency(self, county_name: str, agencies: List[Dict]) -> Optional[Dict]:
        """
        Try to match a county name to an Accela agency from the directory.

        Uses manual mapping first, then pattern matching fallback.
        Returns matched agency dict or None.
        """
        # Step 1: Check manual mapping for known counties
        if county_name in self.KNOWN_ACCELA_COUNTIES:
            target_code = self.KNOWN_ACCELA_COUNTIES[county_name]
            # Find agency with this code
            for agency in agencies:
                if agency.get('serviceProviderCode') == target_code:
                    return agency

        # Step 2: Fallback - try pattern matching for counties we might have missed
        county_base = county_name.replace(' County', '').strip()

        # Try exact match on display name
        for agency in agencies:
            display_name = agency.get('display', '') or ''
            if county_base.lower() in display_name.lower() and 'county' in display_name.lower():
                return agency

        # Try common code patterns: {COUNTY}CO, {COUNTY}, {INITIALS}CO
        patterns = [
            f"{county_base.upper()}CO",      # e.g., LEECO, POLKCO
            f"{county_base.upper()}",        # e.g., BREVARD, MANATEE
            f"{county_base[:3].upper()}CO",  # e.g., LEONCO (Leon County)
        ]

        for pattern in patterns:
            for agency in agencies:
                if agency.get('serviceProviderCode') == pattern:
                    return agency

        return None

    async def validate_agency_code(self, code: str) -> Tuple[bool, Optional[Dict]]:
        """
        Validate an agency code using Accela's /v4/agencies/{code} endpoint.

        Returns (is_valid, agency_info)
        """
        try:
            url = f"https://apis.accela.com/v4/agencies/{code}"
            response = await self.http_client.get(url)

            if response.status_code == 200:
                data = response.json()
                agency_info = data.get('result')
                return True, agency_info
            else:
                return False, None

        except Exception as e:
            print(f"    ⚠️  Validation error for {code}: {str(e)[:50]}")
            return False, None

    def get_county_slug(self, county_name: str) -> str:
        """Convert county name to URL slug."""
        slug = county_name.lower().replace(' county', '').strip()
        slug = slug.replace(' ', '-')
        return slug

    async def fetch_url(self, url: str) -> Optional[str]:
        """Fetch URL content with error handling."""
        try:
            response = await self.http_client.get(url)
            if response.status_code == 200:
                return response.text
            return None
        except Exception:
            return None

    def detect_platform_from_content(self, url: str, html_content: str) -> Tuple[str, str]:
        """Detect non-Accela platform from HTML content."""
        html_lower = html_content.lower()

        for platform, signatures in PLATFORM_SIGNATURES.items():
            for signature in signatures:
                if signature.lower() in html_lower or signature.lower() in url.lower():
                    confidence = 'Confirmed' if signature.lower() in url.lower() else 'Likely'
                    return platform, confidence

        # Custom system indicators
        custom_keywords = ['permit search', 'building permits', 'permit application']
        if any(keyword in html_lower for keyword in custom_keywords):
            return 'Custom', 'Likely'

        return 'Unknown', 'Unknown'

    async def find_county_portal(self, county_name: str) -> Optional[Tuple[str, str]]:
        """
        Try to find county's permit portal URL.

        Returns (portal_url, platform_type) or None
        """
        county_slug = self.get_county_slug(county_name)

        # Try common county website patterns
        for url_pattern in COUNTY_URL_PATTERNS:
            base_url = url_pattern.format(county=county_slug)

            for path in BUILDING_DEPT_PATHS:
                test_url = base_url + path
                html = await self.fetch_url(test_url)

                if html:
                    # Check for Accela
                    if 'accela' in html.lower() or 'aca-prod.accela.com' in html.lower():
                        return test_url, 'Accela'

                    # Check for other platforms
                    platform, _ = self.detect_platform_from_content(test_url, html)
                    if platform != 'Unknown':
                        return test_url, platform

        return None

    async def detect_county_platform(self, county_name: str, accela_agencies: List[Dict]) -> Dict[str, any]:
        """
        Detect platform for a single county using API-first approach.
        """
        print(f"\n🔍 Detecting platform for {county_name}...")

        result = {
            'platform': 'Unknown',
            'platform_confidence': 'Unknown',
            'permit_portal_url': None,
            'building_dept_website': None,
            'county_code': None,
            'platform_detection_notes': None
        }

        notes = []

        # Step 1: Try to match county to Accela agency from directory
        matched_agency = self.match_county_to_agency(county_name, accela_agencies)

        if matched_agency:
            code = matched_agency.get('serviceProviderCode')
            display_name = matched_agency.get('displayName')
            hosted_aca = matched_agency.get('hostedACA', False)

            # Validate the code
            is_valid, agency_info = await self.validate_agency_code(code)

            if is_valid:
                result['platform'] = 'Accela'
                result['platform_confidence'] = 'Confirmed'
                result['county_code'] = code

                # Try to construct portal URL if hosted
                if hosted_aca:
                    portal_url = f"https://aca-prod.accela.com/{code}/Default.aspx"
                    # Verify it exists
                    if await self.fetch_url(portal_url):
                        result['permit_portal_url'] = portal_url

                notes.append(f"Matched to Accela agency '{display_name}' (code: {code})")
                notes.append(f"Validated via /v4/agencies/{code} API")
                print(f"  ✅ Accela confirmed! Code: {code} ({display_name})")
                self.stats['api_validated'] += 1
            else:
                notes.append(f"Matched to agency {code} but validation failed")
                print(f"  ⚠️  Agency {code} found but validation failed")

        # Step 2: If no Accela match, try to find portal and detect platform
        if result['platform'] == 'Unknown':
            portal_info = await self.find_county_portal(county_name)

            if portal_info:
                portal_url, platform_type = portal_info
                result['platform'] = platform_type
                result['platform_confidence'] = 'Likely'
                result['building_dept_website'] = portal_url
                notes.append(f"{platform_type} detected at {portal_url}")
                print(f"  ✅ {platform_type} detected via web portal!")
            else:
                notes.append(f"Attempted detection on {datetime.now().strftime('%Y-%m-%d')}, no platform identified")
                print(f"  ❓ Platform could not be determined")

        # Set notes
        result['platform_detection_notes'] = '; '.join(notes) if notes else None

        return result

    async def update_county_in_db(self, county_name: str, detection_result: Dict[str, any]):
        """Update county record in database with detection results."""
        try:
            update_data = {
                'platform': detection_result['platform'],
                'platform_confidence': detection_result['platform_confidence'],
                'platform_detection_notes': detection_result['platform_detection_notes']
            }

            if detection_result['permit_portal_url']:
                update_data['permit_portal_url'] = detection_result['permit_portal_url']
            if detection_result['building_dept_website']:
                update_data['building_dept_website'] = detection_result['building_dept_website']
            if detection_result['county_code']:
                update_data['county_code'] = detection_result['county_code']

            response = self.supabase.table('counties').update(update_data).eq('name', county_name).execute()

            if response.data:
                print(f"  💾 Database updated successfully")
                return True
            else:
                print(f"  ❌ Database update failed: No rows affected")
                return False

        except Exception as e:
            print(f"  ❌ Database update error: {str(e)}")
            self.stats['errors'] += 1
            return False

    async def process_all_counties(self):
        """Process all Florida counties using API-first detection."""
        print("=" * 80)
        print("🚀 Florida County Platform Detection Script (API-Based)")
        print("=" * 80)

        # Step 1: Fetch Accela agencies from directory API
        self.fl_accela_agencies = await self.fetch_accela_agencies()

        # Step 2: Fetch all Florida counties from database
        try:
            response = self.supabase.table('counties').select('id, name, platform').eq('state', 'FL').order('name').execute()
            counties = response.data

            print(f"\n📊 Processing {len(counties)} Florida counties")
            print(f"⏱️  Rate limit: 2 seconds between requests")
            print("\n" + "=" * 80)

        except Exception as e:
            print(f"❌ Error fetching counties from database: {e}")
            return

        # Step 3: Process each county
        for idx, county in enumerate(counties, 1):
            county_name = county['name']
            current_platform = county.get('platform', 'Unknown')

            print(f"\n[{idx}/{len(counties)}] Processing: {county_name} (current: {current_platform})")

            # Detect platform
            detection_result = await self.detect_county_platform(county_name, self.fl_accela_agencies)

            # Update database
            await self.update_county_in_db(county_name, detection_result)

            # Update statistics
            self.stats['total_processed'] += 1
            platform = detection_result['platform']
            self.stats['platforms_detected'][platform] = self.stats['platforms_detected'].get(platform, 0) + 1

            if detection_result['county_code']:
                self.stats['agency_codes_found'] += 1

            # Rate limiting
            if idx < len(counties):
                print(f"  ⏳ Waiting 2 seconds...")
                await asyncio.sleep(2)

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print detection summary statistics."""
        print("\n" + "=" * 80)
        print("📊 DETECTION SUMMARY")
        print("=" * 80)

        print(f"\n✅ Total counties processed: {self.stats['total_processed']}")
        print(f"🏢 Agency codes extracted: {self.stats['agency_codes_found']}")
        print(f"✓  API-validated codes: {self.stats['api_validated']}")
        print(f"❌ Errors encountered: {self.stats['errors']}")

        print("\n🎯 Platform Distribution:")
        for platform, count in sorted(self.stats['platforms_detected'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / self.stats['total_processed'] * 100) if self.stats['total_processed'] > 0 else 0
            print(f"  • {platform}: {count} counties ({percentage:.1f}%)")

        print("\n" + "=" * 80)


async def main():
    """Main entry point."""
    detector = PlatformDetector()

    try:
        await detector.process_all_counties()
    except KeyboardInterrupt:
        print("\n\n⚠️  Detection interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await detector.close()


if __name__ == '__main__':
    asyncio.run(main())
