"""Supabase database connection and utilities."""
from supabase import create_client, Client
from app.config import settings


class Database:
    """Supabase database connection manager."""

    _client: Client = None

    @classmethod
    def get_client(cls) -> Client:
        """Get or create Supabase client."""
        if cls._client is None:
            cls._client = create_client(
                settings.supabase_url,
                settings.supabase_key
            )
        return cls._client


def get_db() -> Client:
    """Dependency to get database client."""
    return Database.get_client()
