"""Accela Civic Platform API client with OAuth refresh_token flow."""
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from app.services.encryption import encryption_service


class AccelaClient:
    """Client for Accela Civic Platform V4 API using OAuth refresh_token flow."""

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        county_code: str,
        refresh_token: str = "",
        access_token: str = "",
        token_expires_at: str = ""
    ):
        """
        Initialize Accela client with OAuth refresh_token flow.

        Args:
            app_id: Accela application ID (global, from settings)
            app_secret: Accela application secret (decrypted)
            county_code: County/agency code (e.g., 'ISLANDERNC' for Nassau County)
            refresh_token: OAuth refresh token (encrypted, from database)
            access_token: Current access token (encrypted, from cache)
            token_expires_at: Token expiration timestamp (ISO format)
        """
        self.app_id = app_id
        self.app_secret = app_secret  # Store decrypted (received from config)
        self.county_code = county_code
        self._refresh_token = refresh_token  # Store encrypted
        self._access_token = access_token  # Store encrypted
        self._token_expires_at = token_expires_at

        # Use production Accela API
        self.base_url = "https://apis.accela.com"
        self.auth_url = "https://auth.accela.com"

    @property
    def access_token(self) -> str:
        """Get decrypted access token."""
        if not self._access_token:
            return ""
        return encryption_service.decrypt(self._access_token)

    @property
    def refresh_token_decrypted(self) -> str:
        """Get decrypted refresh token."""
        if not self._refresh_token:
            return ""
        return encryption_service.decrypt(self._refresh_token)

    def _is_token_expired(self) -> bool:
        """Check if current token is expired or will expire soon."""
        if not self._token_expires_at or not self._access_token:
            return True

        try:
            expires_at = datetime.fromisoformat(self._token_expires_at.replace('Z', '+00:00'))
            # Refresh if token expires within 1 minute
            return datetime.utcnow() >= expires_at - timedelta(minutes=1)
        except (ValueError, AttributeError):
            return True

    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for refresh token.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Must match the redirect_uri used in authorization request

        Returns:
            Dict with 'success', 'refresh_token', 'access_token', 'expires_at'
        """
        url = f"{self.auth_url}/oauth2/token"

        data = {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "environment": "PROD"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                result = response.json()

            # Calculate expiration
            expires_in = result.get("expires_in", 3600)  # Default 1 hour
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            return {
                "success": True,
                "refresh_token": result["refresh_token"],
                "access_token": result["access_token"],
                "expires_at": expires_at.isoformat() + 'Z',
                "error": None
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def refresh_access_token(self) -> Dict[str, Any]:
        """
        Use refresh token to get new access token.

        Returns:
            Dict with 'access_token' and 'expires_at' (encrypted)
        """
        if not self._refresh_token:
            raise ValueError("No refresh token available")

        url = f"{self.auth_url}/oauth2/token"

        data = {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token_decrypted,
            "environment": "PROD"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            result = response.json()

        # Calculate expiration
        expires_in = result.get("expires_in", 3600)  # Default 1 hour
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Encrypt and store
        encrypted_token = encryption_service.encrypt(result["access_token"])
        self._access_token = encrypted_token
        self._token_expires_at = expires_at.isoformat() + 'Z'

        return {
            "access_token": encrypted_token,
            "expires_at": self._token_expires_at
        }

    async def _ensure_valid_token(self):
        """Ensure we have a valid token, refresh if needed."""
        if self._is_token_expired():
            await self.refresh_access_token()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make authenticated request to Accela API.

        CRITICAL: Uses Authorization header WITHOUT 'Bearer ' prefix!
        """
        await self._ensure_valid_token()

        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": self.access_token,  # NO "Bearer " prefix!
            "Content-Type": "application/json",
            "x-accela-agency": self.county_code,  # Agency context header
            **kwargs.pop("headers", {})
        }

        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()

    async def get_permits(
        self,
        date_from: str,
        date_to: str,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get permits from Accela.

        Args:
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            limit: Max results (default 100)
            status: Optional status filter (e.g., 'Finaled')

        Returns:
            List of permit records
        """
        params = {
            "module": "Building",
            "openedDateFrom": date_from,
            "openedDateTo": date_to,
            "limit": limit
        }

        if status:
            params["status"] = status

        result = await self._make_request("GET", "/v4/records", params=params)
        return result.get("result", [])

    async def get_addresses(self, record_id: str) -> List[Dict[str, Any]]:
        """Get addresses for a record."""
        result = await self._make_request("GET", f"/v4/records/{record_id}/addresses")
        return result.get("result", [])

    async def get_owners(self, record_id: str) -> List[Dict[str, Any]]:
        """Get owners for a record."""
        result = await self._make_request("GET", f"/v4/records/{record_id}/owners")
        return result.get("result", [])

    async def get_parcels(self, record_id: str) -> List[Dict[str, Any]]:
        """Get parcels (property data) for a record."""
        result = await self._make_request("GET", f"/v4/records/{record_id}/parcels")
        return result.get("result", [])

    async def test_connection(self) -> Dict[str, Any]:
        """Test Accela connection by attempting to get permits."""
        try:
            await self._ensure_valid_token()
            # Try a minimal query
            result = await self.get_permits(
                date_from="2024-01-01",
                date_to="2024-01-02",
                limit=1
            )
            return {
                "success": True,
                "message": "Connection successful",
                "token_expires_at": self._token_expires_at
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}"
            }
