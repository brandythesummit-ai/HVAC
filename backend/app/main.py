"""FastAPI application entry point with graceful shutdown handling."""
import asyncio
import signal
import sys
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import counties, permits, leads, summit, background_jobs, properties, health
from app.routers import settings as settings_router
from app.workers.job_processor import start_job_processor, stop_job_processor
from app.services.health_checker import background_health_checker
from app.services.scheduler import get_scheduler

logger = logging.getLogger(__name__)

# Global state for graceful shutdown
_shutdown_requested = False
_background_tasks: set = set()

# Create FastAPI app
app = FastAPI(
    title="HVAC Lead Generation API",
    description="Backend API for HVAC lead generation platform with Accela and Summit.AI integration",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(counties.router)
app.include_router(permits.router)
app.include_router(leads.router)
app.include_router(summit.router)
app.include_router(settings_router.router)
app.include_router(background_jobs.router)
app.include_router(properties.router)


def _handle_shutdown_signal(signum, frame):
    """
    Handle OS signals (SIGTERM, SIGINT) for graceful shutdown.

    This prevents orphaned background tasks when the server is stopped.
    Without this, asyncio tasks can continue running even after the parent
    process is killed (becoming orphaned with PPID=1).
    """
    global _shutdown_requested

    if _shutdown_requested:
        # Second signal = force exit
        logger.warning("Forced shutdown - exiting immediately")
        sys.exit(1)

    _shutdown_requested = True
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name} - initiating graceful shutdown")

    # Trigger asyncio shutdown by creating a task that will stop the event loop
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(_graceful_shutdown())
    except RuntimeError:
        # No running loop - just exit
        sys.exit(0)


async def _graceful_shutdown():
    """Perform graceful shutdown of all background tasks."""
    logger.info("Starting graceful shutdown sequence...")

    # Stop job processor
    try:
        await stop_job_processor()
        logger.info("Job processor stopped")
    except Exception as e:
        logger.error(f"Error stopping job processor: {e}")

    # Stop scheduler
    try:
        scheduler = get_scheduler()
        scheduler.stop()
        logger.info("Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")

    # Cancel all tracked background tasks
    for task in _background_tasks.copy():
        if not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

    logger.info("Graceful shutdown complete")


# Register signal handlers
# Note: These only work on Unix-like systems. On Windows, only SIGINT works.
signal.signal(signal.SIGTERM, _handle_shutdown_signal)
signal.signal(signal.SIGINT, _handle_shutdown_signal)


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Start background services on application startup."""
    logger.info("Starting HVAC Lead Generation API...")

    # Start job processor
    await start_job_processor()
    logger.info("Job processor started")

    # Start pull scheduler for weekly incremental pulls
    scheduler = get_scheduler()
    scheduler.start()
    logger.info("Pull scheduler started")

    # Start background health checker and track the task
    health_task = asyncio.create_task(background_health_checker())
    _background_tasks.add(health_task)
    health_task.add_done_callback(_background_tasks.discard)
    logger.info("Background health checker started")

    logger.info("All background services started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background services on application shutdown."""
    logger.info("Shutdown event triggered")
    await _graceful_shutdown()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "HVAC Lead Generation API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """
    Simple health check endpoint (legacy).

    For comprehensive health monitoring, use /api/health instead.
    """
    return {
        "status": "healthy",
        "environment": settings.environment
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development"
    )
