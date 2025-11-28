"""Summit.AI (HighLevel) CRM API client."""
import httpx
from typing import Dict, List, Optional, Any
from app.config import settings


class SummitClient:
    """Client for The Summit.AI (HighLevel) CRM API."""

    def __init__(self, api_key: Optional[str] = None, location_id: Optional[str] = None):
        """
        Initialize Summit.AI client.

        Args:
            api_key: Summit.AI API key (defaults to settings)
            location_id: Summit.AI location ID (defaults to settings)
        """
        self.api_key = api_key or settings.summit_api_key
        self.location_id = location_id or settings.summit_location_id
        self.base_url = "https://rest.gohighlevel.com/v1"

    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
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
        """Test Summit.AI connection."""
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
