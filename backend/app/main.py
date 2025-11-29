"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import counties, permits, leads, summit
from app.routers import settings as settings_router

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
app.include_router(counties.router)
app.include_router(permits.router)
app.include_router(leads.router)
app.include_router(summit.router)
app.include_router(settings_router.router)


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
    """Health check endpoint."""
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
