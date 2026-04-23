"""GoHighLevel (GHL) CRM API client with Private Integration static token.

Summit.AI is a white-labeled GHL instance under the user's agency.
This client talks to the same services.leadconnectorhq.com endpoints
that GHL's Private Integration uses.

M10 renames the module from summit_client.py. A backward-compat shim
at app/services/summit_client.py re-exports SummitClient = GHLClient
so any in-flight imports from the old name continue to work. M13
extends this client with the Contact + Opportunity handoff model.
"""
import httpx
import logging
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class GHLClient:
    """Client for GoHighLevel (GHL) CRM API with Private Integration static token.

    Summit.AI = GHL white-label. Same API.
    """

    def __init__(
        self,
        access_token: Optional[str] = None,
        location_id: Optional[str] = None,
    ):
        """
        Initialize GHL client with Private Integration static token.

        Args:
            access_token: GHL Private Integration static access token (pit-****)
            location_id: GHL location ID
        """
        # settings.ghl_* falls back to SUMMIT_* at Settings-init time
        # so old deploys without GHL_* env vars still function.
        self.access_token = access_token or settings.ghl_access_token
        self.location_id = location_id or settings.ghl_location_id
        self.base_url = "https://services.leadconnectorhq.com"

        if access_token:
            logger.info("GHLClient initialized with explicit credentials (database)")
        else:
            logger.info("GHLClient initialized with environment variable credentials")

        # HTTP headers must be ASCII per RFC 7230. Fail loud if not.
        if self.access_token:
            try:
                self.access_token.encode('ascii')
            except UnicodeEncodeError:
                raise ValueError(
                    "GHL access token contains non-ASCII characters. "
                    "HTTP Authorization headers require ASCII-only values."
                )

        if self.location_id:
            try:
                self.location_id.encode('ascii')
            except UnicodeEncodeError:
                raise ValueError(
                    "GHL location ID contains non-ASCII characters. "
                    "HTTP headers require ASCII-only values."
                )

    def _get_headers(self) -> Dict[str, str]:
        if not self.access_token:
            raise ValueError(
                "No access token configured. Please add your Private "
                "Integration token in Settings."
            )
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Version": "2021-07-28",
        }

    async def search_contact(
        self,
        phone: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/contacts/"
        params = {"locationId": self.location_id}
        if phone:
            params["query"] = phone
        elif email:
            params["query"] = email
        else:
            return None

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=self._get_headers())
            response.raise_for_status()
            result = response.json()

        contacts = result.get("contacts", [])
        return contacts[0] if contacts else None

    async def create_contact(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/contacts/"
        contact_data["locationId"] = self.location_id
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=contact_data, headers=self._get_headers())
            response.raise_for_status()
            return response.json()

    async def update_contact(
        self,
        contact_id: str,
        contact_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/contacts/{contact_id}"
        async with httpx.AsyncClient() as client:
            response = await client.put(url, json=contact_data, headers=self._get_headers())
            response.raise_for_status()
            return response.json()

    async def add_tags(self, contact_id: str, tags: List[str]) -> Dict[str, Any]:
        url = f"{self.base_url}/contacts/{contact_id}/tags"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={"tags": tags}, headers=self._get_headers())
            response.raise_for_status()
            return response.json()

    async def test_connection(self) -> Dict[str, Any]:
        try:
            url = f"{self.base_url}/locations/{self.location_id}"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()
            return {"success": True, "message": "Connection successful"}
        except Exception as e:
            logger.warning("GHL test_connection failed: %s", e)
            return {"success": False, "message": f"Connection failed: {e!s}"}
