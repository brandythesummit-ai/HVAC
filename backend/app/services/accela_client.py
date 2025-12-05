"""Accela Civic Platform API client with OAuth refresh_token flow."""
import httpx
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import logging
from app.services.encryption import encryption_service
from app.services.rate_limiter import AccelaRateLimiter
from app.config import settings

logger = logging.getLogger(__name__)


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

        # Initialize rate limiter (configurable via environment)
        self.rate_limiter = AccelaRateLimiter(
            threshold=settings.accela_rate_limit_threshold,
            fallback_delay_pagination=settings.accela_pagination_delay_fallback,
            fallback_delay_enrichment=settings.accela_enrichment_delay_fallback,
        )

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
            return datetime.now(timezone.utc) >= expires_at - timedelta(minutes=1)
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
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.app_id,
            "client_secret": self.app_secret
        }

        # DETAILED LOGGING - Before request
        logger.debug(f" [AUTH CODE EXCHANGE] Starting token exchange")
        logger.debug(f"   URL: {url}")
        logger.debug(f"   Redirect URI: {redirect_uri}")
        logger.debug(f"   Code (first 20 chars): {code[:20]}...")
        logger.debug(f"   Client ID: {self.app_id}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    data=data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "x-accela-appid": self.app_id
                    }
                )

                # DETAILED LOGGING - After request
                logger.info(f" [AUTH CODE EXCHANGE] Response received")
                logger.debug(f"   Status: {response.status_code}")
                logger.debug(f"   Headers: {dict(response.headers)}")

                response.raise_for_status()
                result = response.json()

                logger.info(f" [AUTH CODE EXCHANGE] Token exchange successful")

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

        except httpx.HTTPStatusError as e:
            # DETAILED LOGGING - Error case
            error_body = e.response.text
            error_status = e.response.status_code
            trace_id = e.response.headers.get('x-accela-traceid') or e.response.headers.get('x-accela-trace-id')

            logger.error(f" [AUTH CODE EXCHANGE] Failed:")
            logger.debug(f"   Status: {error_status}")
            logger.debug(f"   URL: {url}")
            logger.debug(f"   Redirect URI sent: {redirect_uri}")
            logger.debug(f"   Request headers: {dict(e.response.request.headers)}")
            logger.debug(f"   Request body: {e.response.request.content.decode()}")
            logger.debug(f"   Response headers: {dict(e.response.headers)}")
            logger.debug(f"   Response body: {error_body}")
            if trace_id:
                logger.debug(f"   Trace ID: {trace_id}")

            return {
                "success": False,
                "error": f"Accela API error ({error_status}): {error_body}",
                "trace_id": trace_id
            }
        except Exception as e:
            logger.error(f" [AUTH CODE EXCHANGE] Unexpected error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def exchange_password_for_token(
        self,
        username: str,
        password: str,
        scope: str = "records"
    ) -> Dict[str, Any]:
        """
        Exchange user credentials for tokens using password grant flow.

        This is simpler than authorization code flow and works well for
        backend integrations. User enters password once, then we use
        refresh tokens for ongoing access.

        Args:
            username: User's email/username
            password: User's password
            scope: OAuth scope (default: 'records')

        Returns:
            Dict with 'success', 'refresh_token', 'access_token', 'expires_at'
        """
        url = f"{self.auth_url}/oauth2/token"

        data = {
            "grant_type": "password",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "username": username,
            "password": password,
            "scope": scope,
            "agency_name": self.county_code,
            "environment": "PROD"
        }

        logger.debug(f" [PASSWORD GRANT] Starting token exchange")
        logger.debug(f"   URL: {url}")
        logger.debug(f"   Username: {username}")
        logger.debug(f"   Agency: {self.county_code}")
        logger.debug(f"   Scope: {scope}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    data=data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "x-accela-appid": self.app_id
                    }
                )

                logger.info(f" [PASSWORD GRANT] Response received")
                logger.debug(f"   Status: {response.status_code}")

                response.raise_for_status()
                result = response.json()

                logger.info(f" [PASSWORD GRANT] Token exchange successful")

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

        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            error_status = e.response.status_code
            trace_id = e.response.headers.get('x-accela-traceid') or e.response.headers.get('x-accela-trace-id')

            logger.error(f" [PASSWORD GRANT] Failed:")
            logger.debug(f"   Status: {error_status}")
            logger.debug(f"   Response body: {error_body}")
            if trace_id:
                logger.debug(f"   Trace ID: {trace_id}")

            return {
                "success": False,
                "error": f"Accela API error ({error_status}): {error_body}",
                "trace_id": trace_id
            }
        except Exception as e:
            logger.error(f" [PASSWORD GRANT] Unexpected error: {str(e)}")
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
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token_decrypted,
            "client_id": self.app_id,
            "client_secret": self.app_secret
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                data=data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "x-accela-appid": self.app_id
                }
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

    async def ensure_valid_token(self) -> Dict[str, Any]:
        """
        Public method to verify OAuth token is valid before processing.

        Call this at the start of a job to fail fast if re-authorization is needed.

        Returns:
            Dict with 'success', 'error', 'needs_reauth'
        """
        try:
            if self._is_token_expired():
                logger.info(f"[TOKEN] Token expired, attempting refresh...")
                await self.refresh_access_token()

            return {
                "success": True,
                "error": None,
                "needs_reauth": False,
                "expires_at": self._token_expires_at
            }
        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            error_status = e.response.status_code

            # 400/401 errors typically mean refresh token is invalid
            needs_reauth = error_status in (400, 401)

            logger.error(f"[TOKEN] Refresh failed: {error_status} - {error_body}")

            return {
                "success": False,
                "error": f"Token refresh failed ({error_status}): {error_body}",
                "needs_reauth": needs_reauth,
                "expires_at": self._token_expires_at
            }
        except Exception as e:
            logger.error(f"[TOKEN] Unexpected error during token refresh: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "needs_reauth": True,  # Assume re-auth needed on unknown errors
                "expires_at": self._token_expires_at
            }

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        request_type: str = "general",
        max_retries: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Accela API with rate limiting.

        CRITICAL: Uses Authorization header WITHOUT 'Bearer ' prefix!

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            request_type: Type of request for rate limiter ("pagination", "enrichment", "general")
            max_retries: Maximum number of retries on 429 errors
            **kwargs: Additional arguments passed to httpx request

        Returns:
            Response JSON data

        Raises:
            httpx.HTTPStatusError: On non-429 HTTP errors
        """
        # Use configured max_retries if not specified
        if max_retries is None:
            max_retries = settings.accela_max_retries

        await self._ensure_valid_token()

        # Wait if needed before making request (proactive throttling)
        await self.rate_limiter.wait_if_needed(request_type=request_type)

        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": self.access_token,  # NO "Bearer " prefix!
            "Content-Type": "application/json",
            "x-accela-agency": self.county_code,  # Agency context header
            **kwargs.pop("headers", {})
        }

        # Configure timeout (30s default, configurable via ACCELA_REQUEST_TIMEOUT)
        timeout = httpx.Timeout(settings.accela_request_timeout, connect=10.0)

        # VERBOSE LOGGING: Show every API call
        params_str = ""
        if "params" in kwargs:
            params_str = "&".join([f"{k}={v}" for k, v in kwargs["params"].items() if v is not None])
        full_url = f"{url}?{params_str}" if params_str else url
        print(f"🌐 [ACCELA API] {method} {full_url}", flush=True)

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.request(method, url, headers=headers, **kwargs)

                    # Update rate limiter state from response headers
                    self.rate_limiter.update_from_headers(dict(response.headers))

                    # VERBOSE LOGGING: Show response status and rate limit info
                    rate_remaining = response.headers.get('x-ratelimit-remaining', '?')
                    rate_limit = response.headers.get('x-ratelimit-limit', '?')
                    print(f"   ✅ {response.status_code} OK | Rate: {rate_remaining}/{rate_limit} remaining", flush=True)

                    # Handle 429 Too Many Requests
                    if response.status_code == 429:
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"[ACCELA API] 429 Too Many Requests (attempt {attempt + 1}/{max_retries})"
                            )
                            await self.rate_limiter.handle_429(dict(response.headers))
                            continue  # Retry after waiting
                        else:
                            # Final attempt, raise error
                            response.raise_for_status()

                    # Raise for other error status codes
                    response.raise_for_status()
                    return response.json()

            except httpx.TimeoutException as e:
                logger.error(f"[ACCELA API] Timeout on {endpoint} (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    raise httpx.HTTPError(f"Request timeout after {settings.accela_request_timeout}s: {endpoint}")
                # Brief pause before retry
                await asyncio.sleep(1.0)

            except httpx.HTTPStatusError as e:
                # Re-raise non-429 errors immediately
                if e.response.status_code != 429:
                    raise
                # 429 on final attempt - raise
                if attempt == max_retries - 1:
                    raise

        # Should not reach here, but if we do, raise generic error
        raise httpx.HTTPError(f"Max retries ({max_retries}) exceeded for {endpoint}")

    async def get_permits(
        self,
        date_from: str,
        date_to: str,
        limit: int = 100,
        status: Optional[str] = None,
        permit_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get permits from Accela with automatic pagination.

        Fetches permits in chunks of 100 (Accela max per request)
        until reaching requested limit or no more results available.

        Uses the 'expand' parameter to include addresses, owners, and parcels
        in each record, eliminating the need for separate enrichment API calls.
        This reduces API calls from 4 per permit to 1 per permit batch.
        See: https://developer.accela.com/docs/construct-partialResponse.html

        Args:
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            limit: Max results (default 100)
            status: Optional status filter (e.g., 'Finaled')
            permit_type: Optional type filter (e.g., 'Residential Mechanical Trade Permit') - filters at API level

        Returns:
            Dict containing permits (with expanded addresses/owners/parcels), query_info, and debug_info
        """
        all_permits = []
        offset = 0
        page_size = 100  # Accela API max per request
        pages_fetched = 0

        logger.debug(f" [ACCELA API] Fetching up to {limit} permits with pagination")

        while offset < limit:
            current_page_size = min(page_size, limit - offset)

            params = {
                "module": "Building",
                "openedDateFrom": date_from,
                "openedDateTo": date_to,
                "limit": current_page_size,
                "offset": offset,  # ← KEY: Pagination offset
                "expand": "addresses,owners,parcels"  # ← Include enrichment data in single call
            }

            if status:
                params["status"] = status

            if permit_type:
                params["type"] = permit_type  # ← API-level filtering

            logger.debug(f"   📄 Fetching page {pages_fetched + 1}: offset={offset}, limit={current_page_size}")

            result = await self._make_request(
                "GET",
                "/v4/records",
                request_type="pagination",  # Rate limiter applies pagination delays
                params=params
            )
            page_permits = result.get("result", [])

            if not page_permits:
                logger.debug(f"   ✅ No more permits (empty page)")
                break

            all_permits.extend(page_permits)
            pages_fetched += 1

            logger.debug(f"   ✅ Got {len(page_permits)} permits (total: {len(all_permits)})")

            # If we got fewer than requested, we've hit the end
            if len(page_permits) < current_page_size:
                logger.debug(f"   ✅ Last page (partial)")
                break

            offset += current_page_size

        logger.info(f" [ACCELA API] Pagination complete: {len(all_permits)} permits across {pages_fetched} pages")

        # DATE VALIDATION: Check if returned permits match requested date range
        # This helps detect when Accela API ignores date filters
        date_validation = self._validate_permit_dates(all_permits, date_from, date_to)

        if not date_validation["all_in_range"]:
            logger.warning(
                f" [ACCELA API] DATE MISMATCH: Requested {date_from} to {date_to}, "
                f"but {date_validation['out_of_range_count']}/{len(all_permits)} permits "
                f"have dates outside this range. Sample dates: {date_validation['sample_dates']}"
            )

        # Return permits with diagnostics
        return {
            "permits": all_permits,
            "query_info": {
                "date_from": date_from,
                "date_to": date_to,
                "limit": limit,
                "status": status,
                "permit_type": permit_type,
                "module": "Building",
                "pages_fetched": pages_fetched,
                "total_fetched": len(all_permits)
            },
            "debug_info": {
                "total_returned": len(all_permits),
                "pagination_enabled": True,
                "api_endpoint": "/v4/records"
            },
            "date_validation": date_validation
        }

    def _validate_permit_dates(
        self,
        permits: List[Dict[str, Any]],
        date_from: str,
        date_to: str
    ) -> Dict[str, Any]:
        """
        Validate that permit dates fall within the requested date range.

        This helps detect when Accela API ignores date filters and returns
        permits outside the requested range.

        Args:
            permits: List of permit records from Accela
            date_from: Requested start date (YYYY-MM-DD)
            date_to: Requested end date (YYYY-MM-DD)

        Returns:
            Dict with validation results:
            - all_in_range: True if all permits are within range
            - in_range_count: Number of permits within range
            - out_of_range_count: Number of permits outside range
            - sample_dates: List of unique dates found (for debugging)
        """
        if not permits:
            return {
                "all_in_range": True,
                "in_range_count": 0,
                "out_of_range_count": 0,
                "sample_dates": []
            }

        in_range_count = 0
        out_of_range_count = 0
        sample_dates = set()

        for permit in permits:
            # Get openedDate from permit (may be in different formats)
            opened_date = permit.get("openedDate", "")
            if not opened_date:
                continue

            # Extract just the date portion (YYYY-MM-DD) for comparison
            permit_date = opened_date[:10] if len(opened_date) >= 10 else opened_date
            sample_dates.add(permit_date)

            # Check if within range
            if date_from <= permit_date <= date_to:
                in_range_count += 1
            else:
                out_of_range_count += 1

        return {
            "all_in_range": out_of_range_count == 0,
            "in_range_count": in_range_count,
            "out_of_range_count": out_of_range_count,
            "sample_dates": sorted(list(sample_dates))[:10]  # Limit to 10 samples
        }

    async def get_addresses(self, record_id: str) -> List[Dict[str, Any]]:
        """Get addresses for a record."""
        result = await self._make_request(
            "GET",
            f"/v4/records/{record_id}/addresses",
            request_type="enrichment"  # Rate limiter applies enrichment delays
        )
        return result.get("result", [])

    async def get_owners(self, record_id: str) -> List[Dict[str, Any]]:
        """Get owners for a record."""
        result = await self._make_request(
            "GET",
            f"/v4/records/{record_id}/owners",
            request_type="enrichment"  # Rate limiter applies enrichment delays
        )
        return result.get("result", [])

    async def get_parcels(self, record_id: str) -> List[Dict[str, Any]]:
        """Get parcels (property data) for a record."""
        result = await self._make_request(
            "GET",
            f"/v4/records/{record_id}/parcels",
            request_type="enrichment"  # Rate limiter applies enrichment delays
        )
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
