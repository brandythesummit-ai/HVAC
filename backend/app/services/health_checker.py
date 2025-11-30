"""
Health Check Service

Provides comprehensive health checking for all system components.
Uses a hybrid approach: inline checks (fast) and cached checks (slow, run in background).
"""

import asyncio
import time
import httpx
from datetime import datetime, timezone
from typing import Dict, Optional, Any, Literal
from dataclasses import dataclass, asdict

from supabase import Client
from app.database import get_db
from app.services.encryption import encryption_service
from app.config import settings
import app.workers.job_processor as job_processor


@dataclass
class HealthCheck:
    """Health check result for a component."""
    status: Literal["healthy", "degraded", "down", "unknown"]
    priority: Literal["critical", "high", "medium", "low"]
    message: str
    response_time_ms: Optional[float] = None
    last_checked: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, filtering None values."""
        result = asdict(self)
        result['last_checked'] = self.last_checked or datetime.now(timezone.utc).isoformat()
        return {k: v for k, v in result.items() if v is not None}


class HealthCheckCache:
    """In-memory cache for slow health checks."""

    def __init__(self):
        self._cache: Dict[str, HealthCheck] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[HealthCheck]:
        """Get cached health check result."""
        async with self._lock:
            return self._cache.get(key)

    async def set(self, key: str, value: HealthCheck):
        """Set cached health check result."""
        async with self._lock:
            self._cache[key] = value

    async def get_all(self) -> Dict[str, HealthCheck]:
        """Get all cached results."""
        async with self._lock:
            return self._cache.copy()


# Global cache instance
_health_cache = HealthCheckCache()


async def check_database() -> HealthCheck:
    """
    Check database connectivity (inline, fast).

    Tests:
    - Supabase client can execute a simple query
    - Response time is reasonable (<100ms expected)
    """
    start_time = time.time()

    try:
        db = get_db()
        # Simple query to check connectivity
        result = db.table("counties").select("id").limit(1).execute()

        response_time = (time.time() - start_time) * 1000

        # Degraded if slow (>500ms)
        if response_time > 500:
            return HealthCheck(
                status="degraded",
                priority="critical",
                message=f"Database slow ({response_time:.0f}ms)",
                response_time_ms=response_time
            )

        return HealthCheck(
            status="healthy",
            priority="critical",
            message="Database connected",
            response_time_ms=response_time
        )

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return HealthCheck(
            status="down",
            priority="critical",
            message=f"Database error: {str(e)}",
            response_time_ms=response_time
        )


async def check_encryption() -> HealthCheck:
    """
    Check encryption service (inline, fast).

    Tests:
    - Encryption service can encrypt/decrypt test data
    - Round-trip encryption works correctly
    """
    start_time = time.time()

    try:
        test_data = "health_check_test"
        encrypted = encryption_service.encrypt(test_data)
        decrypted = encryption_service.decrypt(encrypted)

        if decrypted != test_data:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                status="down",
                priority="critical",
                message="Encryption round-trip failed",
                response_time_ms=response_time
            )

        response_time = (time.time() - start_time) * 1000
        return HealthCheck(
            status="healthy",
            priority="critical",
            message="Encryption operational",
            response_time_ms=response_time
        )

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return HealthCheck(
            status="down",
            priority="critical",
            message=f"Encryption error: {str(e)}",
            response_time_ms=response_time
        )


async def check_configuration() -> HealthCheck:
    """
    Check critical configuration (inline, fast).

    Tests:
    - Required environment variables are set
    - Configuration is valid
    """
    start_time = time.time()

    try:
        # Check critical environment variables
        missing = []

        if not settings.supabase_url:
            missing.append("supabase_url")
        if not settings.supabase_key:
            missing.append("supabase_key")
        if not settings.encryption_key:
            missing.append("encryption_key")

        if missing:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                status="down",
                priority="critical",
                message=f"Missing config: {', '.join(missing)}",
                response_time_ms=response_time
            )

        response_time = (time.time() - start_time) * 1000
        return HealthCheck(
            status="healthy",
            priority="critical",
            message="Configuration valid",
            response_time_ms=response_time
        )

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return HealthCheck(
            status="down",
            priority="critical",
            message=f"Config error: {str(e)}",
            response_time_ms=response_time
        )


async def check_services() -> HealthCheck:
    """
    Check internal services (inline, fast).

    Tests:
    - Address normalizer available
    - Property aggregator available
    - These are stateless services (always healthy)
    """
    start_time = time.time()

    try:
        # These are stateless services, always available
        # Just verify they can be imported
        from app.services.address_normalizer import AddressNormalizer
        from app.services.property_aggregator import PropertyAggregator

        response_time = (time.time() - start_time) * 1000
        return HealthCheck(
            status="healthy",
            priority="low",
            message="Internal services available",
            response_time_ms=response_time
        )

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return HealthCheck(
            status="down",
            priority="low",
            message=f"Services error: {str(e)}",
            response_time_ms=response_time
        )


async def check_job_processor() -> HealthCheck:
    """
    Check job processor status (cached, run in background).

    Tests:
    - Job processor is running
    - Background task is alive
    """
    start_time = time.time()

    try:
        # Check if processor instance exists and is running
        if job_processor._processor_instance is None:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                status="down",
                priority="high",
                message="Job processor not initialized",
                response_time_ms=response_time
            )

        if not job_processor._processor_instance.is_running:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                status="down",
                priority="high",
                message="Job processor stopped",
                response_time_ms=response_time
            )

        response_time = (time.time() - start_time) * 1000
        return HealthCheck(
            status="healthy",
            priority="high",
            message="Job processor running",
            response_time_ms=response_time
        )

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return HealthCheck(
            status="down",
            priority="high",
            message=f"Job processor error: {str(e)}",
            response_time_ms=response_time
        )


async def check_accela_api() -> HealthCheck:
    """
    Check Accela API connectivity (cached, run in background).

    Tests:
    - Can reach Accela API endpoint
    - API responds to health check

    Note: This is a slow check (2-5s), should be cached.
    """
    start_time = time.time()

    try:
        # Try to reach Accela API (just check the base URL)
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Accela uses auth.accela.com for OAuth
            response = await client.get("https://apis.accela.com", follow_redirects=True)

            response_time = (time.time() - start_time) * 1000

            # API is reachable if we get any response
            if response.status_code < 500:
                # Degraded if slow (>3s)
                if response_time > 3000:
                    return HealthCheck(
                        status="degraded",
                        priority="medium",
                        message=f"Accela API slow ({response_time:.0f}ms)",
                        response_time_ms=response_time
                    )

                return HealthCheck(
                    status="healthy",
                    priority="medium",
                    message="Accela API reachable",
                    response_time_ms=response_time
                )
            else:
                return HealthCheck(
                    status="degraded",
                    priority="medium",
                    message=f"Accela API error {response.status_code}",
                    response_time_ms=response_time
                )

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return HealthCheck(
            status="degraded",
            priority="medium",
            message=f"Accela API unreachable: {str(e)[:50]}",
            response_time_ms=response_time
        )


async def check_summit_api() -> HealthCheck:
    """
    Check Summit.AI API connectivity (cached, run in background).

    Tests:
    - Can reach Summit.AI (HighLevel) API
    - API responds

    Note: This is a slow check (2-5s), should be cached.
    """
    start_time = time.time()

    try:
        # Check if Summit.AI is configured
        if not settings.summit_access_token:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                status="unknown",
                priority="medium",
                message="Summit.AI not configured",
                response_time_ms=response_time
            )

        # Try to reach Summit.AI API
        async with httpx.AsyncClient(timeout=10.0) as client:
            # HighLevel API endpoint
            headers = {
                "Authorization": f"Bearer {settings.summit_access_token}",
                "Version": "2021-07-28"
            }
            response = await client.get(
                f"https://services.leadconnectorhq.com/locations/{settings.summit_location_id}",
                headers=headers
            )

            response_time = (time.time() - start_time) * 1000

            if response.status_code < 500:
                # Degraded if slow (>3s)
                if response_time > 3000:
                    return HealthCheck(
                        status="degraded",
                        priority="medium",
                        message=f"Summit.AI API slow ({response_time:.0f}ms)",
                        response_time_ms=response_time
                    )

                return HealthCheck(
                    status="healthy",
                    priority="medium",
                    message="Summit.AI API reachable",
                    response_time_ms=response_time
                )
            else:
                return HealthCheck(
                    status="degraded",
                    priority="medium",
                    message=f"Summit.AI API error {response.status_code}",
                    response_time_ms=response_time
                )

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return HealthCheck(
            status="degraded",
            priority="medium",
            message=f"Summit.AI API unreachable: {str(e)[:50]}",
            response_time_ms=response_time
        )


async def check_vercel_frontend() -> HealthCheck:
    """
    Check Vercel frontend deployment (cached, run in background).

    Tests:
    - Frontend URL is reachable
    - Returns 200 status

    Note: This is a slow check (1-3s), should be cached.
    """
    start_time = time.time()

    try:
        frontend_url = "https://hvac-liard.vercel.app"

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(frontend_url)

            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                # Degraded if slow (>2s)
                if response_time > 2000:
                    return HealthCheck(
                        status="degraded",
                        priority="medium",
                        message=f"Frontend slow ({response_time:.0f}ms)",
                        response_time_ms=response_time
                    )

                return HealthCheck(
                    status="healthy",
                    priority="medium",
                    message="Frontend reachable",
                    response_time_ms=response_time
                )
            else:
                return HealthCheck(
                    status="degraded",
                    priority="medium",
                    message=f"Frontend error {response.status_code}",
                    response_time_ms=response_time
                )

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return HealthCheck(
            status="down",
            priority="medium",
            message=f"Frontend unreachable: {str(e)[:50]}",
            response_time_ms=response_time
        )


async def check_railway_backend() -> HealthCheck:
    """
    Check Railway backend deployment (cached, run in background).

    Tests:
    - Backend is externally reachable
    - Health endpoint responds

    Note: This check verifies external accessibility (what users experience).
    Note: This is a slow check (1-3s), should be cached.
    """
    start_time = time.time()

    try:
        # Get Railway backend URL from environment or use production URL
        backend_url = getattr(settings, 'railway_backend_url',
                             'https://hvac-backend-production-11e6.up.railway.app')

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Check the simple health endpoint
            response = await client.get(f"{backend_url}/health")

            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                # Degraded if slow (>2s)
                if response_time > 2000:
                    return HealthCheck(
                        status="degraded",
                        priority="medium",
                        message=f"Backend slow ({response_time:.0f}ms)",
                        response_time_ms=response_time
                    )

                return HealthCheck(
                    status="healthy",
                    priority="medium",
                    message="Backend externally reachable",
                    response_time_ms=response_time
                )
            else:
                return HealthCheck(
                    status="degraded",
                    priority="medium",
                    message=f"Backend error {response.status_code}",
                    response_time_ms=response_time
                )

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return HealthCheck(
            status="down",
            priority="medium",
            message=f"Backend unreachable: {str(e)[:50]}",
            response_time_ms=response_time
        )


async def check_network() -> HealthCheck:
    """
    Check network connectivity (cached, run in background).

    Tests:
    - Can reach external internet
    - DNS resolution works

    Note: This is a slow check (1-2s), should be cached.
    """
    start_time = time.time()

    try:
        # Check connectivity to a reliable external service
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://www.google.com")

            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return HealthCheck(
                    status="healthy",
                    priority="medium",
                    message="Network connected",
                    response_time_ms=response_time
                )
            else:
                return HealthCheck(
                    status="degraded",
                    priority="medium",
                    message=f"Network degraded (status {response.status_code})",
                    response_time_ms=response_time
                )

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return HealthCheck(
            status="down",
            priority="medium",
            message=f"Network down: {str(e)[:50]}",
            response_time_ms=response_time
        )


async def run_inline_checks() -> Dict[str, HealthCheck]:
    """
    Run all inline (fast) health checks.

    These checks run on every /health request:
    - Database connectivity
    - Encryption service
    - Configuration
    - Internal services
    """
    results = await asyncio.gather(
        check_database(),
        check_encryption(),
        check_configuration(),
        check_services(),
        return_exceptions=True
    )

    return {
        "database": results[0] if not isinstance(results[0], Exception) else HealthCheck(
            status="down", priority="critical", message=f"Check failed: {str(results[0])}"
        ),
        "encryption": results[1] if not isinstance(results[1], Exception) else HealthCheck(
            status="down", priority="critical", message=f"Check failed: {str(results[1])}"
        ),
        "configuration": results[2] if not isinstance(results[2], Exception) else HealthCheck(
            status="down", priority="critical", message=f"Check failed: {str(results[2])}"
        ),
        "services": results[3] if not isinstance(results[3], Exception) else HealthCheck(
            status="down", priority="low", message=f"Check failed: {str(results[3])}"
        ),
    }


async def run_cached_checks() -> Dict[str, HealthCheck]:
    """
    Run all cached (slow) health checks in background.

    These checks are expensive (2-5s each) and run every 30-60 seconds:
    - Job processor status
    - Accela API
    - Summit.AI API
    - Vercel frontend
    - Railway backend
    - Network connectivity
    """
    results = await asyncio.gather(
        check_job_processor(),
        check_accela_api(),
        check_summit_api(),
        check_vercel_frontend(),
        check_railway_backend(),
        check_network(),
        return_exceptions=True
    )

    checks = {
        "job_processor": results[0] if not isinstance(results[0], Exception) else HealthCheck(
            status="down", priority="high", message=f"Check failed: {str(results[0])}"
        ),
        "accela_api": results[1] if not isinstance(results[1], Exception) else HealthCheck(
            status="degraded", priority="medium", message=f"Check failed: {str(results[1])}"
        ),
        "summit_api": results[2] if not isinstance(results[2], Exception) else HealthCheck(
            status="degraded", priority="medium", message=f"Check failed: {str(results[2])}"
        ),
        "vercel_frontend": results[3] if not isinstance(results[3], Exception) else HealthCheck(
            status="degraded", priority="medium", message=f"Check failed: {str(results[3])}"
        ),
        "railway_backend": results[4] if not isinstance(results[4], Exception) else HealthCheck(
            status="degraded", priority="medium", message=f"Check failed: {str(results[4])}"
        ),
        "network": results[5] if not isinstance(results[5], Exception) else HealthCheck(
            status="down", priority="medium", message=f"Check failed: {str(results[5])}"
        ),
    }

    # Update cache
    for key, check in checks.items():
        await _health_cache.set(key, check)

    return checks


def determine_overall_status(components: Dict[str, HealthCheck]) -> str:
    """
    Determine overall system status based on component health.

    Rules:
    - Any critical component down = system down
    - Any component degraded or down = system degraded
    - All healthy = system healthy

    Returns:
        "healthy", "degraded", or "down"
    """
    for component in components.values():
        # Any critical component down = system down
        if component.status == "down" and component.priority == "critical":
            return "down"

    # Any component degraded or down = system degraded
    for component in components.values():
        if component.status in ["down", "degraded"]:
            return "degraded"

    return "healthy"


async def get_health_summary() -> Dict[str, Any]:
    """
    Get complete health summary with inline and cached checks.

    Returns:
        Dictionary with overall status, timestamp, components, and summary.
    """
    # Run inline checks
    inline_results = await run_inline_checks()

    # Get cached results (don't block on these)
    cached_results = await _health_cache.get_all()

    # Combine results
    all_components = {**inline_results, **cached_results}

    # Determine overall status
    overall_status = determine_overall_status(all_components)

    # Count statuses
    summary = {
        "healthy": sum(1 for c in all_components.values() if c.status == "healthy"),
        "degraded": sum(1 for c in all_components.values() if c.status == "degraded"),
        "down": sum(1 for c in all_components.values() if c.status == "down"),
        "unknown": sum(1 for c in all_components.values() if c.status == "unknown"),
    }

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {k: v.to_dict() for k, v in all_components.items()},
        "summary": summary
    }


async def background_health_checker():
    """
    Background task that runs cached health checks every 30 seconds.

    This task runs continuously and updates the health cache with
    results from slow external checks (APIs, infrastructure).
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info("🏥 Background health checker started")

    while True:
        try:
            await run_cached_checks()
            logger.debug("✅ Background health checks completed")
        except Exception as e:
            logger.error(f"❌ Error in background health checker: {str(e)}")

        # Wait 30 seconds before next check
        await asyncio.sleep(30)
