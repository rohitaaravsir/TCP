"""
repositories/support_repository.py

Supabase-backed repository for the Support domain.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from supabase import AsyncClient

from core.exceptions import DatabaseConnectionError
from schemas.support import (
    SupportTicketSchema,
    SupportTicketCreateSchema,
    SupportTicketUpdateSchema,
    SupportMessageSchema,
    SupportMessageCreateSchema,
)

logger = logging.getLogger(__name__)

_TICKETS_TABLE = "support_tickets"
_MESSAGES_TABLE = "support_messages"


class SupportRepository:
    """Async CRUD repository for support tickets and messages."""

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # Tickets CRUD
    # ------------------------------------------------------------------

    async def create_ticket(self, data: SupportTicketCreateSchema) -> SupportTicketSchema:
        """Create a new support ticket."""
        try:
            payload = data.model_dump()
            payload["status"] = "open"
            payload["is_assigned_to_human"] = False
            payload["created_at"] = datetime.now(timezone.utc).isoformat()
            payload["updated_at"] = datetime.now(timezone.utc).isoformat()

            response = (
                await self._client.table(_TICKETS_TABLE)
                .insert(payload)
                .execute()
            )
            return SupportTicketSchema(**response.data[0])
        except Exception as exc:
            logger.error("SupportRepository.create_ticket failed | error=%s", exc)
            raise DatabaseConnectionError(f"Failed to create support ticket: {exc}") from exc

    async def get_ticket(self, ticket_id: int) -> SupportTicketSchema | None:
        """Fetch a ticket by ID."""
        try:
            response = (
                await self._client.table(_TICKETS_TABLE)
                .select("*")
                .eq("id", ticket_id)
                .limit(1)
                .execute()
            )
            if not response.data:
                return None
            return SupportTicketSchema(**response.data[0])
        except Exception as exc:
            logger.error("SupportRepository.get_ticket failed | ticket_id=%s | error=%s", ticket_id, exc)
            raise DatabaseConnectionError(f"Failed to fetch ticket {ticket_id}: {exc}") from exc

    async def get_open_ticket_by_user(self, user_id: int) -> SupportTicketSchema | None:
        """Fetch the active open ticket for a user if it exists."""
        try:
            response = (
                await self._client.table(_TICKETS_TABLE)
                .select("*")
                .eq("user_id", user_id)
                .eq("status", "open")
                .limit(1)
                .execute()
            )
            if not response.data:
                return None
            return SupportTicketSchema(**response.data[0])
        except Exception as exc:
            logger.error("SupportRepository.get_open_ticket_by_user failed | user_id=%s | error=%s", user_id, exc)
            raise DatabaseConnectionError(f"Failed to fetch open ticket for user {user_id}: {exc}") from exc

    async def update_ticket(self, ticket_id: int, data: SupportTicketUpdateSchema) -> SupportTicketSchema:
        """Update ticket fields."""
        try:
            payload = data.model_dump(exclude_none=True)
            if not payload:
                ticket = await self.get_ticket(ticket_id)
                if ticket is None:
                    raise DatabaseConnectionError(f"Ticket {ticket_id} not found.")
                return ticket

            payload["updated_at"] = datetime.now(timezone.utc).isoformat()

            response = (
                await self._client.table(_TICKETS_TABLE)
                .update(payload)
                .eq("id", ticket_id)
                .execute()
            )
            return SupportTicketSchema(**response.data[0])
        except DatabaseConnectionError:
            raise
        except Exception as exc:
            logger.error("SupportRepository.update_ticket failed | ticket_id=%s | error=%s", ticket_id, exc)
            raise DatabaseConnectionError(f"Failed to update ticket {ticket_id}: {exc}") from exc

    async def list_open_tickets(self) -> list[SupportTicketSchema]:
        """List all open support tickets."""
        try:
            response = (
                await self._client.table(_TICKETS_TABLE)
                .select("*")
                .eq("status", "open")
                .order("created_at", desc=True)
                .execute()
            )
            return [SupportTicketSchema(**row) for row in response.data]
        except Exception as exc:
            logger.error("SupportRepository.list_open_tickets failed | error=%s", exc)
            raise DatabaseConnectionError(f"Failed to list open tickets: {exc}") from exc

    # ------------------------------------------------------------------
    # Messages CRUD
    # ------------------------------------------------------------------

    async def create_message(self, data: SupportMessageCreateSchema) -> SupportMessageSchema:
        """Insert a support message into the database."""
        try:
            payload = data.model_dump()
            payload["created_at"] = datetime.now(timezone.utc).isoformat()

            response = (
                await self._client.table(_MESSAGES_TABLE)
                .insert(payload)
                .execute()
            )
            return SupportMessageSchema(**response.data[0])
        except Exception as exc:
            logger.error("SupportRepository.create_message failed | error=%s", exc)
            raise DatabaseConnectionError(f"Failed to save support message: {exc}") from exc

    async def list_messages_by_ticket(self, ticket_id: int) -> list[SupportMessageSchema]:
        """Fetch all messages for a specific support ticket."""
        try:
            response = (
                await self._client.table(_MESSAGES_TABLE)
                .select("*")
                .eq("ticket_id", ticket_id)
                .order("created_at", desc=False)
                .execute()
            )
            return [SupportMessageSchema(**row) for row in response.data]
        except Exception as exc:
            logger.error("SupportRepository.list_messages_by_ticket failed | ticket_id=%s | error=%s", ticket_id, exc)
            raise DatabaseConnectionError(f"Failed to fetch messages for ticket {ticket_id}: {exc}") from exc
