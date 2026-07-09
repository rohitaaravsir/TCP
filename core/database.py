"""
core/database.py

Supabase async client wrapper.

Responsibilities:
  - Hold a single shared Supabase client instance (singleton)
  - Verify connectivity on startup
  - Expose a clean interface for the rest of the application

Rules (from PROJECT_RULES.md):
  - All database operations must pass through the data/repository layer.
  - Direct SQL inside handlers is forbidden.
  - This module provides the client; repositories use it.

Usage:
    from core.database import db
    await db.connect()
    client = db.client
"""

from __future__ import annotations

from supabase import AsyncClient, acreate_client

from core.constants import LOG_EVENT_DB_CONNECTED, LOG_EVENT_DB_CONNECTION_FAILED
from core.exceptions import DatabaseConnectionError
from core.logger import get_logger

logger = get_logger(__name__)


class Database:
    """
    Supabase async client wrapper.

    Lifecycle:
        1. Instantiated at module level as `db` singleton.
        2. `await db.connect()` is called once during app startup.
        3. `db.client` is accessed by repositories.
        4. `await db.disconnect()` is called on graceful shutdown.
    """

    def __init__(self) -> None:
        self._client: AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self, url: str, key: str) -> None:
        """
        Establish and verify the Supabase connection.

        Args:
            url: Supabase project URL.
            key: Supabase service role key.

        Raises:
            DatabaseConnectionError: If the connection cannot be established.
        """
        try:
            self._client = await acreate_client(url, key)
            # Lightweight connectivity probe — list tables in public schema
            await self._client.table("_tcp_health").select("*").limit(1).execute()
            logger.info(
                "Supabase connected successfully | event=%s",
                LOG_EVENT_DB_CONNECTED,
            )
        except DatabaseConnectionError:
            raise
        except Exception as exc:
            logger.error(
                "Supabase connection failed | event=%s | error=%s",
                LOG_EVENT_DB_CONNECTION_FAILED,
                str(exc),
            )
            raise DatabaseConnectionError(
                f"Cannot connect to Supabase: {exc}"
            ) from exc

    async def connect_no_verify(self, url: str, key: str) -> None:
        """
        Establish a Supabase connection without a connectivity probe.

        Use this when the _tcp_health table does not yet exist (e.g.,
        before schema migrations have been applied).
        """
        try:
            self._client = await acreate_client(url, key)
            logger.info(
                "Supabase client created (no verify) | event=%s",
                LOG_EVENT_DB_CONNECTED,
            )
        except Exception as exc:
            logger.error(
                "Supabase client creation failed | event=%s | error=%s",
                LOG_EVENT_DB_CONNECTION_FAILED,
                str(exc),
            )
            raise DatabaseConnectionError(
                f"Cannot create Supabase client: {exc}"
            ) from exc

    async def disconnect(self) -> None:
        """
        Release the Supabase client on graceful shutdown.
        """
        if self._client is not None:
            self._client = None
            logger.info("Supabase client released.")

    # ------------------------------------------------------------------
    # Client access
    # ------------------------------------------------------------------

    @property
    def client(self) -> AsyncClient:
        """
        Return the active Supabase async client.

        Raises:
            DatabaseConnectionError: If connect() has not been called yet.
        """
        if self._client is None:
            raise DatabaseConnectionError(
                "Database client is not initialised. Call db.connect() first."
            )
        return self._client

    @property
    def is_connected(self) -> bool:
        """True if the client has been initialised."""
        return self._client is not None


# Module-level singleton — import and use throughout the application.
db = Database()
