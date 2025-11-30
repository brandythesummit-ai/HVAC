"""Summit.AI (HighLevel) CRM API client with Private Integration static token."""
import httpx
import logging
from typing import Dict, List, Optional, Any
from app.config import settings

logger = logging.getLogger(__name__)


class SummitClient:
    """Client for The Summit.AI (HighLevel) CRM API with Private Integration static token."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        location_id: Optional[str] = None,
    ):
        """
        Initialize Summit.AI client with Private Integration static token.

        Args:
            access_token: GHL Private Integration static access token (pit-****)
            location_id: Summit.AI location ID

        Raises:
            ValueError: If credentials contain non-ASCII characters
        """
        self.access_token = access_token or settings.summit_access_token
        self.location_id = location_id or settings.summit_location_id
        self.base_url = "https://services.leadconnectorhq.com"

        # Log credential source for debugging
        if access_token:
            logger.info("SummitClient initialized with explicit credentials (database)")
        else:
            logger.info("SummitClient initialized with environment variable credentials")

        # Defensive validation: Ensure credentials are ASCII-encodable
        # HTTP headers (including Authorization) must be ASCII per RFC 7230
        if self.access_token:
            try:
                self.access_token.encode('ascii')
            except UnicodeEncodeError:
                raise ValueError(
                    "Summit.AI access token contains non-ASCII characters. "
                    "HTTP Authorization headers require ASCII-only values."
                )

        if self.location_id:
            try:
                self.location_id.encode('ascii')
            except UnicodeEncodeError:
                raise ValueError(
                    "Summit.AI location ID contains non-ASCII characters. "
                    "HTTP headers require ASCII-only values."
                )

    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers with static access token."""
        if not self.access_token:
            raise ValueError("No access token configured. Please add your Private Integration token in Settings.")

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Version": "2021-07-28"
        }

    async def search_contact(
        self,
        phone: Optional[str] = None,
        email: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Search for contact by phone or email.

        Args:
            phone: Phone number
            email: Email address

        Returns:
            Contact dict if found, None otherwise
        """
        url = f"{self.base_url}/contacts/"
        params = {"locationId": self.location_id}

        if phone:
            params["query"] = phone
        elif email:
            params["query"] = email
        else:
            return None

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                params=params,
                headers=self._get_headers()
            )
            response.raise_for_status()
            result = response.json()

        contacts = result.get("contacts", [])
        return contacts[0] if contacts else None

    async def create_contact(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create new contact.

        Args:
            contact_data: Contact information

        Returns:
            Created contact with ID
        """
        url = f"{self.base_url}/contacts/"

        # Ensure location ID is set
        contact_data["locationId"] = self.location_id

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=contact_data,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

    async def update_contact(
        self,
        contact_id: str,
        contact_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update existing contact.

        Args:
            contact_id: Contact ID
            contact_data: Updated contact information

        Returns:
            Updated contact
        """
        url = f"{self.base_url}/contacts/{contact_id}"

        async with httpx.AsyncClient() as client:
            response = await client.put(
                url,
                json=contact_data,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

    async def add_tags(self, contact_id: str, tags: List[str]) -> Dict[str, Any]:
        """
        Add tags to contact.

        Args:
            contact_id: Contact ID
            tags: List of tags to add

        Returns:
            Updated contact
        """
        url = f"{self.base_url}/contacts/{contact_id}/tags"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={"tags": tags},
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

    async def test_connection(self) -> Dict[str, Any]:
        """Test Summit.AI connection with Private Integration token."""
        try:
            url = f"{self.base_url}/locations/{self.location_id}"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()

            return {
                "success": True,
                "message": "Connection successful"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}"
            }
