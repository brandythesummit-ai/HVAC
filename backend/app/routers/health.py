"""Health monitoring endpoints."""
import time
from fastapi import APIRouter
from app.services.health_checker import get_health_summary

router = APIRouter(prefix="/api/health", tags=["health"])

# Track application start time for uptime calculation
_app_start_time = time.time()


@router.get("")
async def get_health():
    """
    Get comprehensive system health status.

    Returns health information for all system components:
    - Critical: Database, Encryption, Configuration
    - High: Job Processor
    - Medium: External APIs, Infrastructure
    - Low: Internal Services

    Response includes:
    - Overall status (healthy/degraded/down)
    - Individual component statuses
    - Response times
    - Last checked timestamps
    - Summary statistics
    """
    # Get health summary from health checker service
    health_data = await get_health_summary()

    # Add uptime
    uptime_seconds = int(time.time() - _app_start_time)
    health_data["uptime_seconds"] = uptime_seconds

    return health_data
