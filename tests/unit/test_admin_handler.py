"""
tests/unit/test_admin_handler.py

Unit tests for bot/handlers/admin.py
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import Bot
from aiogram.types import Message, PhotoSize, User

from bot.handlers.admin import (
    handle_pending_payments,
    handle_approve_payment,
    handle_reject_payment,
    handle_view_proof,
    handle_tickets_list,
    handle_reply_ticket,
    handle_close_ticket,
    handle_broadcast,
    handle_ban_user,
    handle_unban_user,
    handle_admin_callbacks,
)
from aiogram.types import CallbackQuery
from config import settings
from schemas.order import OrderSchema, OrderStatus


@pytest.fixture(autouse=True)
def setup_admin_ids():
    original_ids = settings.admin_ids
    settings.admin_ids = [123456789]
    yield
    settings.admin_ids = original_ids



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_order_schema(order_id: int = 12, status: OrderStatus = OrderStatus.PAYMENT_SUBMITTED) -> OrderSchema:
    from datetime import datetime, timezone
    return OrderSchema(
        id=order_id,
        user_id=222,  # Buyer
        product_id=3,
        amount=Decimal("150.00"),
        status=status,
        payment_proof="photo_file_id_abc",
        notes=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_bot() -> AsyncMock:
    bot = AsyncMock(spec=Bot)
    bot.send_message = AsyncMock()
    bot.send_photo = AsyncMock()
    return bot


@pytest.fixture
def mock_message() -> MagicMock:
    message = MagicMock(spec=Message)
    message.from_user = User(id=123456789, is_bot=False, first_name="Admin", last_name="User", username="adminuser")
    message.answer = AsyncMock()
    message.chat = MagicMock()
    message.chat.id = 999
    return message


@pytest.fixture
def mock_order_service() -> AsyncMock:
    return AsyncMock()


# ---------------------------------------------------------------------------
# Tests: handle_pending_payments
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pending_payments_non_admin_ignored(mock_message, mock_order_service):
    """If user is not in settings.admin_ids, command is ignored (no message sent)."""
    mock_message.from_user = User(id=999999999, is_bot=False, first_name="NonAdmin", last_name="User", username="nonadmin")
    await handle_pending_payments(mock_message, mock_order_service)

    mock_order_service.list_pending_payments.assert_not_called()
    mock_message.answer.assert_not_called()


@pytest.mark.asyncio
async def test_pending_payments_success(mock_message, mock_order_service):
    """If user is admin, lists all pending payments."""
    orders = [_make_order_schema(order_id=12)]
    mock_order_service.list_pending_payments.return_value = orders

    await handle_pending_payments(mock_message, mock_order_service)

    mock_order_service.list_pending_payments.assert_awaited_once()
    assert "Pending Payments Awaiting Review" in mock_message.answer.call_args[0][0]


# ---------------------------------------------------------------------------
# Tests: handle_view_proof
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_view_proof_success(mock_message, mock_order_service, mock_bot):
    """If admin, sends the payment proof photo back to admin chat."""
    mock_message.text = "/proof_12"
    order = _make_order_schema(order_id=12)
    mock_order_service.get_order.return_value = order

    await handle_view_proof(mock_message, mock_order_service, mock_bot)

    mock_order_service.get_order.assert_awaited_once_with(12)
    mock_bot.send_photo.assert_awaited_once_with(
        chat_id=999,
        photo="photo_file_id_abc",
        caption="📸 Payment proof for <b>Order #12</b>\n💰 Amount: ₹150.00",
        parse_mode="HTML"
    )


# ---------------------------------------------------------------------------
# Tests: handle_approve_payment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_approve_payment_success(mock_message, mock_order_service, mock_bot):
    """Confirms the order and notifies the buyer of approval."""
    mock_message.text = "/approvepayment 12"
    order = _make_order_schema(order_id=12, status=OrderStatus.CONFIRMED)
    mock_order_service.confirm_order.return_value = order

    await handle_approve_payment(mock_message, mock_order_service, mock_bot)

    mock_order_service.confirm_order.assert_awaited_once_with(12)
    assert "Approved!" in mock_message.answer.call_args[0][0]
    
    # Verify buyer notification
    mock_bot.send_message.assert_awaited_once_with(
        chat_id=222,
        text=(
            "🎉 <b>Payment Approved!</b>\n\n"
            "📦 Order ID: <code>12</code>\n"
            "💰 Amount: ₹150.00\n"
            "🔖 Status: ✅ Confirmed\n\n"
            "Your order is now being processed. Thank you for your purchase!"
        ),
        parse_mode="HTML"
    )


# ---------------------------------------------------------------------------
# Tests: handle_reject_payment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reject_payment_success(mock_message, mock_order_service, mock_bot):
    """Cancels order with rejection reason and notifies buyer."""
    mock_message.text = "/rejectpayment 12 Screenshot was unreadable"
    order = _make_order_schema(order_id=12)
    mock_order_service.get_order.return_value = order

    await handle_reject_payment(mock_message, mock_order_service, mock_bot)

    # Verify update status and notes (rejection reason)
    mock_order_service._orders.update.assert_awaited_once()
    assert "Rejected" in mock_message.answer.call_args[0][0]

    # Verify buyer notification has reason
    mock_bot.send_message.assert_awaited_once()
    notify_text = mock_bot.send_message.call_args[1]["text"]
    assert "Screenshot was unreadable" in notify_text
    assert "rejected" in notify_text.lower()


# ---------------------------------------------------------------------------
# Tests: Support & Broadcast Admin Commands
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tickets_list_success(mock_message):
    """If admin, lists all open support tickets."""
    mock_support_service = AsyncMock()
    from schemas.support import SupportTicketSchema, TicketStatus
    from datetime import datetime, timezone
    
    tickets = [
        SupportTicketSchema(
            id=42, user_id=111, status=TicketStatus.OPEN,
            is_assigned_to_human=True, created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    ]
    mock_support_service.list_open_tickets.return_value = tickets

    await handle_tickets_list(mock_message, mock_support_service)

    mock_support_service.list_open_tickets.assert_awaited_once()
    assert "Open Support Tickets" in mock_message.answer.call_args[0][0]
    assert "Ticket #42" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_reply_ticket_success(mock_message, mock_bot):
    """If admin, sends reply to the user and logs in message history."""
    mock_message.text = "/replyticket 42 We are checking it now."
    mock_support_service = AsyncMock()
    
    from schemas.support import SupportTicketSchema, TicketStatus
    from datetime import datetime, timezone
    ticket = SupportTicketSchema(
        id=42, user_id=111, status=TicketStatus.OPEN,
        is_assigned_to_human=True, created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    mock_support_service.get_ticket_with_messages.return_value = ticket

    await handle_reply_ticket(mock_message, mock_support_service, mock_bot)

    mock_support_service.add_message.assert_awaited_once_with(42, "admin", "We are checking it now.")
    mock_bot.send_message.assert_awaited_once_with(
        chat_id=111,
        text="👨‍💻 <b>Support Reply:</b>\n\nWe are checking it now.\n\n<i>You can reply to this message directly to continue support.</i>",
        parse_mode="HTML"
    )
    assert "Reply sent" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_close_ticket_success(mock_message, mock_bot):
    """If admin, closes the ticket and notifies the user."""
    mock_message.text = "/closeticket 42"
    mock_support_service = AsyncMock()
    
    from schemas.support import SupportTicketSchema, TicketStatus
    from datetime import datetime, timezone
    ticket = SupportTicketSchema(
        id=42, user_id=111, status=TicketStatus.OPEN,
        is_assigned_to_human=True, created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    mock_support_service.get_ticket_with_messages.return_value = ticket

    await handle_close_ticket(mock_message, mock_support_service, mock_bot)

    mock_support_service.close_ticket.assert_awaited_once_with(42)
    mock_bot.send_message.assert_awaited_once()
    assert mock_bot.send_message.call_args[1]["chat_id"] == 111
    assert "resolved and closed" in mock_bot.send_message.call_args[1]["text"]
    assert "closed" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_broadcast_success(mock_message, mock_bot):
    """If admin, broadcasts the message to all users in the system."""
    mock_message.text = "/broadcast System maintenance in 1 hour."
    mock_user_service = AsyncMock()
    
    from schemas.user import UserSchema
    from datetime import datetime, timezone
    users = [
        UserSchema(
            id=111, username="u1", full_name="User One",
            language_code="en", is_banned=False, ban_reason=None,
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
        ),
        UserSchema(
            id=222, username="u2", full_name="User Two",
            language_code="hi", is_banned=False, ban_reason=None,
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
        ),
    ]
    mock_user_service.list_all_users.return_value = users

    await handle_broadcast(mock_message, mock_user_service, mock_bot)

    mock_user_service.list_all_users.assert_awaited_once()
    assert mock_bot.send_message.call_count == 2
    mock_bot.send_message.assert_any_call(
        chat_id=111,
        text="📢 <b>Announcement</b>\n\nSystem maintenance in 1 hour.",
        parse_mode="HTML"
    )
    mock_bot.send_message.assert_any_call(
        chat_id=222,
        text="📢 <b>Announcement</b>\n\nSystem maintenance in 1 hour.",
        parse_mode="HTML"
    )
    assert "Broadcast Completed!" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_ban_user_success(mock_message):
    """If admin, bans the targeted user with reason."""
    mock_message.text = "/ban 999 Abuse of support chat"
    mock_user_service = AsyncMock()
    
    from schemas.user import UserSchema
    from datetime import datetime, timezone
    target_user = UserSchema(
        id=999, username="baduser", full_name="Bad User",
        language_code="en", is_banned=False, ban_reason=None,
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
    )
    mock_user_service.get_user.return_value = target_user

    await handle_ban_user(mock_message, mock_user_service)

    mock_user_service.get_user.assert_awaited_once_with(999)
    mock_user_service.ban_user.assert_awaited_once_with(999, "Abuse of support chat")
    assert "banned" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_unban_user_success(mock_message):
    """If admin, unbans the targeted user."""
    mock_message.text = "/unban 999"
    mock_user_service = AsyncMock()
    
    from schemas.user import UserSchema
    from datetime import datetime, timezone
    target_user = UserSchema(
        id=999, username="gooduser", full_name="Good User",
        language_code="en", is_banned=True, ban_reason="abuse",
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
    )
    mock_user_service.get_user.return_value = target_user

    await handle_unban_user(mock_message, mock_user_service)

    mock_user_service.get_user.assert_awaited_once_with(999)
    mock_user_service.unban_user.assert_awaited_once_with(999)
    assert "unbanned" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_admin_callbacks_menu_payments(mock_message):
    """Admin callback menu:payments should trigger pending payments handler."""
    callback = MagicMock(spec=CallbackQuery)
    callback.data = "admin_menu:payments"
    callback.answer = AsyncMock()
    callback.from_user = User(id=123456789, is_bot=False, first_name="Admin", username="admin") # matching setup_admin_ids fixture ID
    
    mock_msg = MagicMock(spec=Message)
    mock_copied_msg = MagicMock(spec=Message)
    mock_msg.model_copy.return_value = mock_copied_msg
    callback.message = mock_msg

    mock_order_service = AsyncMock()
    mock_support_service = AsyncMock()
    mock_bot = AsyncMock()

    with patch("bot.handlers.admin.handle_pending_payments", new_callable=AsyncMock) as mock_pending:
        await handle_admin_callbacks(callback, mock_order_service, mock_support_service, mock_bot)

        callback.answer.assert_awaited_once()
        mock_pending.assert_awaited_once_with(mock_copied_msg, mock_order_service)
        mock_msg.model_copy.assert_called_once_with(update={"from_user": callback.from_user, "text": "/pendingpayments"})



