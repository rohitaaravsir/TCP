"""
schemas/support.py

Pydantic schemas for the AI Support domain.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    """Lifecycle states of a support ticket."""
    OPEN = "open"
    CLOSED = "closed"

    @property
    def display(self) -> str:
        """Human-readable status label."""
        labels = {
            "open": "🟢 Open",
            "closed": "🔴 Closed",
        }
        return labels.get(self.value, self.value.title())


class SupportMessageSchema(BaseModel):
    """Full support message record."""

    id: int
    ticket_id: int
    sender_role: str = Field(..., description="Role of sender: 'user' | 'ai' | 'admin'")
    text: str = Field(..., description="Text content of the message.")
    created_at: datetime

    model_config = {"from_attributes": True}


class SupportMessageCreateSchema(BaseModel):
    """Request model for creating a new support message."""

    ticket_id: int
    sender_role: str = Field(..., pattern="^(user|ai|admin)$", description="Role of sender.")
    text: str = Field(..., min_length=1, description="Message text.")


class SupportTicketSchema(BaseModel):
    """Full support ticket record."""

    id: int
    user_id: int = Field(..., description="Telegram user ID of client.")
    status: TicketStatus = Field(default=TicketStatus.OPEN)
    is_assigned_to_human: bool = Field(default=False)
    created_at: datetime
    updated_at: datetime
    messages: list[SupportMessageSchema] | None = None

    model_config = {"from_attributes": True}

    @property
    def status_display(self) -> str:
        """Get status string with emoji."""
        return self.status.display


class SupportTicketCreateSchema(BaseModel):
    """Request model for creating a new support ticket."""

    user_id: int


class SupportTicketUpdateSchema(BaseModel):
    """Request model for updating an existing support ticket."""

    status: TicketStatus | None = None
    is_assigned_to_human: bool | None = None
