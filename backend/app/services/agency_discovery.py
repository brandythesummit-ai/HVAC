"""
Accela Agency Discovery Service

Automatically discovers county_code (serviceProviderCode) from Accela's
Agencies API. Requires x-accela-appid header (any valid app_id works).

This enables self-healing behavior:
1. When a county's pull job starts with NULL county_code → auto-discover
2. When a pull fails with 500/400 error → re-discover (maybe code changed)
3. When OAuth is added to a new county → discover code immediately

The GET /v4/agencies endpoint returns all Accela agencies including:
- serviceProviderCode: The county_code we need
- name: Agency display name for matching
- state: Two-letter state code (e.g., "FL")
- country: Country code (e.g., "US")
- enabled: Whether agency is active

Note: The Agencies API returns ALL agencies regardless of which app_id is used,
making it possible to discover any agency with any valid app_id.
"""
import httpx
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

# Conditional import for fuzzy matching
# Falls back to simple matching if rapidfuzz not available
try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logger.warning("rapidfuzz not installed - using simple string matching")


class AgencyDiscoveryService:
    """
    Discovers Accela agency codes for counties.

    Uses Accela's public Agencies API (no auth required) to find the
    serviceProviderCode for a given county name and state.
    """

    AGENCIES_URL = "https://apis.accela.com/v4/agencies"
    MATCH_THRESHOLD = 80  # Minimum fuzzy match score
    REQUEST_TIMEOUT = 30  # seconds

    async def discover_county_code(
        self,
        county_name: str,
        state: str,
        app_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Discover the Accela serviceProviderCode for a county.

        Args:
            county_name: e.g., "Brevard County"
            state: e.g., "FL"
            app_id: Accela app_id for API authentication (required).
                   Any valid app_id works - the Agencies API returns ALL agencies.

        Returns:
            {
                "county_code": "BREVARD",
                "agency_name": "Brevard County",
                "confidence": "exact",
                "match_score": 100
            }
            or None if no match found
        """
        if not app_id:
            logger.error("app_id is required for agency discovery")
            print("❌ app_id is required for agency discovery", flush=True)
            return None

        logger.info(f"🔍 Discovering agency code for {county_name}, {state}")
        print(f"🔍 Discovering agency code for {county_name}, {state}...", flush=True)

        try:
            # Fetch agencies filtered by state
            agencies = await self._fetch_agencies_by_state(state, app_id)

            if not agencies:
                logger.warning(f"No Accela agencies found for state {state}")
                print(f"⚠️ No Accela agencies found for state {state}", flush=True)
                return None

            print(f"   Found {len(agencies)} agencies in {state}", flush=True)

            # Try matching strategies in order
            match = self._find_best_match(county_name, agencies)

            if match:
                logger.info(
                    f"✅ Found match: {county_name} → {match['county_code']} "
                    f"({match['confidence']}, score={match['match_score']})"
                )
                print(
                    f"✅ Found match: {county_name} → {match['county_code']} "
                    f"({match['confidence']}, score={match['match_score']})",
                    flush=True
                )
            else:
                logger.warning(f"❌ No Accela match found for {county_name}, {state}")
                print(f"❌ No Accela match found for {county_name}, {state}", flush=True)

            return match

        except Exception as e:
            logger.error(f"Error discovering agency code: {e}")
            print(f"❌ Error discovering agency code: {e}", flush=True)
            return None

    async def _fetch_agencies_by_state(self, state: str, app_id: str) -> List[Dict]:
        """
        Fetch all enabled Accela agencies for a state.

        The API requires x-accela-appid header and supports pagination.
        We fetch all agencies then filter by state client-side since
        the API doesn't support state filtering directly.

        Note: Any valid app_id works - the endpoint returns ALL agencies.
        """
        all_agencies = []
        offset = 0
        limit = 100

        headers = {
            "x-accela-appid": app_id
        }

        async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
            while True:
                try:
                    response = await client.get(
                        self.AGENCIES_URL,
                        params={"limit": limit, "offset": offset},
                        headers=headers
                    )
                    response.raise_for_status()
                    data = response.json()

                    results = data.get("result", [])
                    if not results:
                        break

                    all_agencies.extend(results)

                    # Stop if we got fewer results than the limit (last page)
                    if len(results) < limit:
                        break
                    offset += limit

                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP error fetching agencies: {e}")
                    break
                except Exception as e:
                    logger.error(f"Error fetching agencies: {e}")
                    break

        # Filter to requested state, US only, enabled only
        filtered = [
            a for a in all_agencies
            if a.get("state") == state
            and a.get("country") == "US"
            and a.get("enabled", True)
        ]

        logger.info(f"Fetched {len(all_agencies)} total agencies, {len(filtered)} in {state}")
        return filtered

    def _find_best_match(self, county_name: str, agencies: List[Dict]) -> Optional[Dict]:
        """
        Find best matching agency for county name.

        Uses multiple matching strategies in order of confidence:
        1. Exact substring match (highest confidence)
        2. County name in serviceProviderCode
        3. Fuzzy matching (if rapidfuzz installed)
        """
        county_lower = county_name.lower()

        # Strategy 1: Exact substring match
        # e.g., "Brevard County" in "Brevard County, FL"
        for agency in agencies:
            agency_name = agency.get("name", "")
            if county_lower in agency_name.lower():
                return {
                    "county_code": agency["serviceProviderCode"],
                    "agency_name": agency_name,
                    "confidence": "exact",
                    "match_score": 100
                }

        # Strategy 2: County name in serviceProviderCode
        # e.g., "BREVARD" matches "Brevard County"
        county_base = county_name.replace(" County", "").strip().upper()
        for agency in agencies:
            code = agency.get("serviceProviderCode", "").upper()
            # Check both directions for flexibility
            if county_base in code or code in county_base:
                return {
                    "county_code": agency["serviceProviderCode"],
                    "agency_name": agency.get("name", ""),
                    "confidence": "code_match",
                    "match_score": 95
                }

        # Strategy 3: Fuzzy matching (if available)
        if RAPIDFUZZ_AVAILABLE:
            agency_names = [a.get("name", "") for a in agencies]
            result = process.extractOne(
                county_name,
                agency_names,
                scorer=fuzz.token_sort_ratio
            )

            if result and result[1] >= self.MATCH_THRESHOLD:
                matched_agency = next(
                    a for a in agencies if a.get("name") == result[0]
                )
                return {
                    "county_code": matched_agency["serviceProviderCode"],
                    "agency_name": result[0],
                    "confidence": "fuzzy",
                    "match_score": result[1]
                }
        else:
            # Simple fallback: check if any word from county name appears in agency name
            county_words = set(county_lower.replace(" county", "").split())
            for agency in agencies:
                agency_name_lower = agency.get("name", "").lower()
                agency_words = set(agency_name_lower.split())
                # If significant overlap (at least one meaningful word matches)
                if county_words & agency_words:
                    return {
                        "county_code": agency["serviceProviderCode"],
                        "agency_name": agency.get("name", ""),
                        "confidence": "simple_match",
                        "match_score": 75
                    }

        return None


# Singleton instance for convenience
_discovery_service: Optional[AgencyDiscoveryService] = None


def get_discovery_service() -> AgencyDiscoveryService:
    """Get or create the agency discovery service singleton."""
    global _discovery_service
    if _discovery_service is None:
        _discovery_service = AgencyDiscoveryService()
    return _discovery_service
