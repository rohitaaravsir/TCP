"""
tests/unit/test_support_handler.py

Unit tests for bot/handlers/support.py
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, User

from bot.handlers.support import (
    handle_support_start,
    handle_support_exit,
    handle_support_human,
    handle_support_message,
)
from bot.states.support import SupportStates
from schemas.support import SupportTicketSchema, SupportMessageSchema, TicketStatus


def _make_ticket_schema(ticket_id: int = 1, is_assigned: bool = False) -> SupportTicketSchema:
    from datetime import datetime, timezone
    return SupportTicketSchema(
        id=ticket_id,
        user_id=111,
        status=TicketStatus.OPEN,
        is_assigned_to_human=is_assigned,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_message() -> MagicMock:
    message = MagicMock(spec=Message)
    message.from_user = User(id=111, is_bot=False, first_name="Test", last_name="User", username="testuser")
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_state() -> AsyncMock:
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={"ticket_id": 1})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    return state


@pytest.fixture
def mock_support_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_ai_provider() -> AsyncMock:
    provider = AsyncMock()
    provider.generate_response = AsyncMock(return_value="AI Reply")
    return provider


@pytest.fixture
def mock_bot() -> AsyncMock:
    bot = AsyncMock(spec=Bot)
    bot.send_message = AsyncMock()
    return bot


@pytest.mark.asyncio
async def test_support_start(mock_message, mock_state, mock_support_service):
    """Should fetch/create ticket, set FSM state, and welcome user."""
    ticket = _make_ticket_schema(ticket_id=12)
    mock_support_service.get_or_create_ticket.return_value = ticket

    await handle_support_start(mock_message, mock_state, mock_support_service)

    mock_support_service.get_or_create_ticket.assert_awaited_once_with(111)
    mock_state.set_state.assert_awaited_once_with(SupportStates.waiting_for_user)
    mock_state.update_data.assert_awaited_once_with(ticket_id=12)
    assert "Support Assistant" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_support_exit(mock_message, mock_state, mock_support_service):
    """Should close the ticket, clear state, and say goodbye."""
    await handle_support_exit(mock_message, mock_state, mock_support_service)

    mock_support_service.close_ticket.assert_awaited_once_with(1)
    mock_state.clear.assert_awaited_once()
    assert "Closed" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_support_human(mock_message, mock_state, mock_support_service, mock_bot):
    """Should mark ticket as assigned to human and notify admins."""
    ticket = _make_ticket_schema(ticket_id=1, is_assigned=True)
    mock_support_service.assign_to_human.return_value = ticket

    with patch("bot.handlers.support.settings") as mock_settings:
        mock_settings.admin_ids = [999]
        await handle_support_human(mock_message, mock_state, mock_support_service, mock_bot)

    mock_support_service.assign_to_human.assert_awaited_once_with(1)
    mock_bot.send_message.assert_awaited_once()
    assert "999" in str(mock_bot.send_message.call_args[1]["chat_id"])
    assert "Human Support Requested" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_support_message_ai_responds(
    mock_message, mock_state, mock_support_service, mock_ai_provider, mock_bot
):
    """If ticket is NOT assigned to human, AI provider should generate response."""
    mock_message.text = "How much is product A?"
    ticket = _make_ticket_schema(ticket_id=1, is_assigned=False)
    ticket.messages = []
    mock_support_service.get_ticket_with_messages.return_value = ticket

    await handle_support_message(mock_message, mock_state, mock_support_service, mock_ai_provider, mock_bot)

    mock_support_service.add_message.assert_any_call(1, "user", "How much is product A?")
    mock_ai_provider.generate_response.assert_awaited_once_with("How much is product A?", [])
    mock_message.answer.assert_awaited_once_with("AI Reply")
    mock_support_service.add_message.assert_any_call(1, "ai", "AI Reply")


@pytest.mark.asyncio
async def test_support_message_waiting_for_human(
    mock_message, mock_state, mock_support_service, mock_ai_provider, mock_bot
):
    """If ticket is assigned to human, it should inform user and forward message to admins."""
    mock_message.text = "Hello, is anyone there?"
    ticket = _make_ticket_schema(ticket_id=1, is_assigned=True)
    ticket.messages = []
    mock_support_service.get_ticket_with_messages.return_value = ticket

    with patch("bot.handlers.support.settings") as mock_settings:
        mock_settings.admin_ids = [999]
        await handle_support_message(mock_message, mock_state, mock_support_service, mock_ai_provider, mock_bot)

    mock_support_service.add_message.assert_awaited_once_with(1, "user", "Hello, is anyone there?")
    mock_ai_provider.generate_response.assert_not_called()
    assert "Waiting for support agent" in mock_message.answer.call_args[0][0]
    
    # Forwarded message to admin
    mock_bot.send_message.assert_awaited_once()
    assert mock_bot.send_message.call_args[1]["chat_id"] == 999
    assert "Hello, is anyone there?" in mock_bot.send_message.call_args[1]["text"]
