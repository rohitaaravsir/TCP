"""
services/support_service.py

Business logic service for managing AI and human customer support tickets.
"""

from __future__ import annotations

import logging

from repositories.support_repository import SupportRepository
from schemas.support import (
    SupportTicketSchema,
    SupportTicketCreateSchema,
    SupportTicketUpdateSchema,
    SupportMessageSchema,
    SupportMessageCreateSchema,
    TicketStatus,
)

logger = logging.getLogger(__name__)


class SupportService:
    """Orchestrates ticket creation, message logging, human handover, and closure."""

    def __init__(self, support_repo: SupportRepository) -> None:
        self._support_repo = support_repo

    async def get_or_create_ticket(self, user_id: int) -> SupportTicketSchema:
        """
        Fetch the active open ticket for a user, or create one if none is open.
        """
        ticket = await self._support_repo.get_open_ticket_by_user(user_id)
        if ticket is None:
            logger.info("No open support ticket found for user_id=%s. Creating new ticket.", user_id)
            ticket = await self._support_repo.create_ticket(
                SupportTicketCreateSchema(user_id=user_id)
            )
        return ticket

    async def get_ticket_with_messages(self, ticket_id: int) -> SupportTicketSchema | None:
        """
        Fetch a ticket and populate its message history.
        """
        ticket = await self._support_repo.get_ticket(ticket_id)
        if ticket:
            messages = await self._support_repo.list_messages_by_ticket(ticket_id)
            ticket.messages = messages
        return ticket

    async def add_message(self, ticket_id: int, sender_role: str, text: str) -> SupportMessageSchema:
        """
        Save a message (from user, AI, or admin) to a ticket's history.
        """
        return await self._support_repo.create_message(
            SupportMessageCreateSchema(
                ticket_id=ticket_id,
                sender_role=sender_role,
                text=text,
            )
        )

    async def assign_to_human(self, ticket_id: int) -> SupportTicketSchema:
        """
        Flag the ticket as assigned to human support, pausing AI response generation.
        """
        logger.info("Support ticket #%s marked as assigned to human.", ticket_id)
        return await self._support_repo.update_ticket(
            ticket_id,
            SupportTicketUpdateSchema(is_assigned_to_human=True)
        )

    async def close_ticket(self, ticket_id: int) -> SupportTicketSchema:
        """
        Close the support ticket.
        """
        logger.info("Support ticket #%s closed.", ticket_id)
        return await self._support_repo.update_ticket(
            ticket_id,
            SupportTicketUpdateSchema(status=TicketStatus.CLOSED)
        )

    async def list_open_tickets(self) -> list[SupportTicketSchema]:
        """
        Get all open tickets.
        """
        return await self._support_repo.list_open_tickets()

    async def get_ticket_history(self, ticket_id: int) -> list[SupportMessageSchema]:
        """
        Retrieve message logs for a ticket.
        """
        return await self._support_repo.list_messages_by_ticket(ticket_id)
