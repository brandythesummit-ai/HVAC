"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase
    supabase_url: str
    supabase_key: str

    # Summit.AI (Private Integration - Static Token)
    summit_access_token: str = ""
    summit_location_id: str = ""

    # Encryption
    encryption_key: str

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_url: str = "http://localhost:8000"  # Base URL for API (used for OAuth callbacks)
    # CORS origins - supports both localhost and Vercel deployment
    # Set CORS_ORIGINS in Vercel to include your frontend URL
    cors_origins: str = "http://localhost:3000,http://localhost:5173,https://*.vercel.app"

    # Environment
    environment: str = "development"

    # Accela API Rate Limiting
    # LAYER 5: Speed Optimizations - reduced delays and threshold
    # Threshold: fraction remaining before pausing (0.10 = pause at 10% remaining, i.e., 90% usage)
    accela_rate_limit_threshold: float = 0.10
    # Fallback delays (used when rate limit headers not available)
    accela_pagination_delay_fallback: float = 0.2  # 200ms between pagination requests (was 500ms)
    accela_enrichment_delay_fallback: float = 0.05  # 50ms between enrichment requests (was 100ms)
    # Request settings
    accela_max_retries: int = 3  # Max retries on 429 errors
    accela_request_timeout: float = 30.0  # Request timeout in seconds

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
