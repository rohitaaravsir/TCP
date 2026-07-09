"""
tests/unit/test_support_service.py

Unit tests for services/support_service.py
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest

from services.support_service import SupportService
from schemas.support import SupportTicketSchema, SupportMessageSchema, TicketStatus


def _make_ticket_schema(ticket_id: int = 1, status: TicketStatus = TicketStatus.OPEN, is_assigned: bool = False) -> SupportTicketSchema:
    return SupportTicketSchema(
        id=ticket_id,
        user_id=111,
        status=status,
        is_assigned_to_human=is_assigned,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _make_message_schema(msg_id: int = 10, role: str = "user", text: str = "help") -> SupportMessageSchema:
    return SupportMessageSchema(
        id=msg_id,
        ticket_id=1,
        sender_role=role,
        text=text,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_support_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def support_service(mock_support_repo) -> SupportService:
    return SupportService(mock_support_repo)


@pytest.mark.asyncio
async def test_get_or_create_ticket_existing(support_service, mock_support_repo):
    expected = _make_ticket_schema()
    mock_support_repo.get_open_ticket_by_user.return_value = expected

    result = await support_service.get_or_create_ticket(111)

    assert result == expected
    mock_support_repo.get_open_ticket_by_user.assert_awaited_once_with(111)
    mock_support_repo.create_ticket.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_create_ticket_new(support_service, mock_support_repo):
    mock_support_repo.get_open_ticket_by_user.return_value = None
    expected = _make_ticket_schema(ticket_id=2)
    mock_support_repo.create_ticket.return_value = expected

    result = await support_service.get_or_create_ticket(111)

    assert result == expected
    mock_support_repo.create_ticket.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_message(support_service, mock_support_repo):
    expected = _make_message_schema()
    mock_support_repo.create_message.return_value = expected

    result = await support_service.add_message(1, "user", "help")

    assert result == expected
    mock_support_repo.create_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_assign_to_human(support_service, mock_support_repo):
    expected = _make_ticket_schema(is_assigned=True)
    mock_support_repo.update_ticket.return_value = expected

    result = await support_service.assign_to_human(1)

    assert result.is_assigned_to_human is True
    mock_support_repo.update_ticket.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_ticket(support_service, mock_support_repo):
    expected = _make_ticket_schema(status=TicketStatus.CLOSED)
    mock_support_repo.update_ticket.return_value = expected

    result = await support_service.close_ticket(1)

    assert result.status == TicketStatus.CLOSED
    mock_support_repo.update_ticket.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_ticket_with_messages(support_service, mock_support_repo):
    ticket = _make_ticket_schema()
    messages = [_make_message_schema(10), _make_message_schema(11, "ai", "sure")]
    mock_support_repo.get_ticket.return_value = ticket
    mock_support_repo.list_messages_by_ticket.return_value = messages

    result = await support_service.get_ticket_with_messages(1)

    assert result.id == 1
    assert len(result.messages) == 2
    assert result.messages[1].text == "sure"
    mock_support_repo.get_ticket.assert_awaited_once_with(1)
    mock_support_repo.list_messages_by_ticket.assert_awaited_once_with(1)
