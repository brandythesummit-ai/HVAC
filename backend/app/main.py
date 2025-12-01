"""FastAPI application entry point."""
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import counties, permits, leads, summit, background_jobs, properties, health
from app.routers import settings as settings_router
from app.workers.job_processor import start_job_processor, stop_job_processor
from app.services.health_checker import background_health_checker
from app.services.scheduler import get_scheduler

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


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Start background services on application startup."""
    # Start job processor
    await start_job_processor()

    # Start pull scheduler for weekly incremental pulls
    scheduler = get_scheduler()
    scheduler.start()

    # Start background health checker
    asyncio.create_task(background_health_checker())


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background services on application shutdown."""
    await stop_job_processor()

    # Stop pull scheduler
    scheduler = get_scheduler()
    scheduler.stop()


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
