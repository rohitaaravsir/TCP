"""
tests/unit/test_common_handler.py

Unit tests for bot/handlers/common.py
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from aiogram.types import Message, User, CallbackQuery

from bot.handlers.common import handle_start, handle_help, handle_ping, handle_menu_callback
from schemas.user import UserSchema


@pytest.fixture
def mock_message() -> MagicMock:
    message = MagicMock(spec=Message)
    message.from_user = User(id=111, is_bot=False, first_name="Test", last_name="User", username="testuser")
    message.answer = AsyncMock()
    return message


@pytest.mark.asyncio
async def test_handle_start(mock_message):
    """Should register/update the user and send personalized welcome."""
    mock_user_service = AsyncMock()
    
    from datetime import datetime, timezone
    user_schema = UserSchema(
        id=111, username="testuser", full_name="Test User",
        language_code="en", is_banned=False, ban_reason=None,
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
    )
    mock_user_service.register_or_update.return_value = user_schema

    await handle_start(mock_message, mock_user_service)

    mock_user_service.register_or_update.assert_awaited_once_with(mock_message.from_user)
    mock_message.answer.assert_awaited_once()
    assert "Test User" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_help_user(mock_message):
    """If user is not admin, should display only user commands."""
    with patch("bot.handlers.common.settings") as mock_settings:
        mock_settings.admin_ids = [999]  # Not user 111
        await handle_help(mock_message)

    mock_message.answer.assert_awaited_once()
    text = mock_message.answer.call_args[0][0]
    assert "Available Commands" in text
    assert "General:" in text
    assert "Admin Commands:" not in text


@pytest.mark.asyncio
async def test_handle_help_admin(mock_message):
    """If user is admin, should display both user and admin commands."""
    with patch("bot.handlers.common.settings") as mock_settings:
        mock_settings.admin_ids = [111]  # User 111 is admin
        await handle_help(mock_message)

    mock_message.answer.assert_awaited_once()
    text = mock_message.answer.call_args[0][0]
    assert "Available Commands" in text
    assert "Admin Commands:" in text


@pytest.mark.asyncio
async def test_handle_ping(mock_message):
    """Should measure and reply with latency pong."""
    # We mock sent message edit_text
    sent_msg = AsyncMock(spec=Message)
    sent_msg.edit_text = AsyncMock()
    mock_message.answer.return_value = sent_msg

    await handle_ping(mock_message)

    mock_message.answer.assert_awaited_once_with("🏓 Pinging...")
    sent_msg.edit_text.assert_awaited_once()
    assert "Latency" in sent_msg.edit_text.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_menu_callback():
    """Should intercept menu callback queries and trigger the respective handlers."""
    callback = MagicMock(spec=CallbackQuery)
    callback.data = "menu:catalogue"
    callback.answer = AsyncMock()
    callback.from_user = User(id=111, is_bot=False, first_name="T", username="t")
    
    mock_msg = MagicMock(spec=Message)
    mock_copied_msg = MagicMock(spec=Message)
    mock_copied_msg.from_user = callback.from_user
    mock_msg.model_copy.return_value = mock_copied_msg
    callback.message = mock_msg

    mock_state = AsyncMock()
    mock_user_service = AsyncMock()
    mock_product_service = AsyncMock()
    mock_order_service = AsyncMock()
    mock_support_service = AsyncMock()

    with patch("bot.handlers.products.handle_products", new_callable=AsyncMock) as mock_handle_products:
        await handle_menu_callback(
            callback, mock_state, mock_user_service,
            mock_product_service, mock_order_service, mock_support_service
        )

        callback.answer.assert_awaited_once()
        mock_handle_products.assert_awaited_once_with(mock_copied_msg, mock_product_service)
        mock_msg.model_copy.assert_called_once_with(update={"from_user": callback.from_user})

