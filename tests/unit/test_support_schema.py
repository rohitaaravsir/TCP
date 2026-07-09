"""
tests/unit/test_support_schema.py

Unit tests for schemas/support.py
"""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from schemas.support import (
    SupportMessageSchema,
    SupportMessageCreateSchema,
    SupportTicketSchema,
    SupportTicketCreateSchema,
    SupportTicketUpdateSchema,
    TicketStatus,
)


def _make_ticket_data(**overrides) -> dict:
    base = {
        "id": 1,
        "user_id": 123456789,
        "status": "open",
        "is_assigned_to_human": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return base


def _make_message_data(**overrides) -> dict:
    base = {
        "id": 10,
        "ticket_id": 1,
        "sender_role": "user",
        "text": "Hello world",
        "created_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return base


class TestSupportTicketSchema:
    def test_valid_ticket_creation(self):
        data = _make_ticket_data()
        ticket = SupportTicketSchema(**data)
        assert ticket.id == 1
        assert ticket.user_id == 123456789
        assert ticket.status == TicketStatus.OPEN
        assert ticket.status_display == "🟢 Open"
        assert ticket.is_assigned_to_human is False

    def test_invalid_status_raises(self):
        data = _make_ticket_data(status="invalid_status")
        with pytest.raises(ValidationError):
            SupportTicketSchema(**data)


class TestSupportMessageSchema:
    def test_valid_message_creation(self):
        data = _make_message_data()
        msg = SupportMessageSchema(**data)
        assert msg.id == 10
        assert msg.sender_role == "user"
        assert msg.text == "Hello world"

    def test_message_create_schema_validation(self):
        # Valid
        msg = SupportMessageCreateSchema(ticket_id=1, sender_role="ai", text="Hi!")
        assert msg.sender_role == "ai"

        # Invalid role
        with pytest.raises(ValidationError):
            SupportMessageCreateSchema(ticket_id=1, sender_role="invalid_role", text="Hi!")

        # Empty text
        with pytest.raises(ValidationError):
            SupportMessageCreateSchema(ticket_id=1, sender_role="user", text="")
