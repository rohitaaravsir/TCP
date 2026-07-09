"""
bot/handlers/support.py

Telegram handlers for customer support chat (AI-driven with human handoff).
"""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from bot.keyboards import get_support_menu_keyboard

from bot.states.support import SupportStates
from config import settings
from core.constants import MSG_ERROR_GENERIC
from interfaces.ai_provider import AIProviderInterface
from services.support_service import SupportService

logger = logging.getLogger(__name__)

router = Router(name="support")


# Helper to alert all admins
async def alert_admins_new_ticket(bot: Bot, ticket_id: int, user_name: str, user_id: int) -> None:
    """Send an alert to all registered admin IDs."""
    text = (
        f"⚠️ <b>Human Support Needed!</b>\n\n"
        f"👤 User: <b>{user_name}</b>\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"🎫 Ticket ID: <code>{ticket_id}</code>\n\n"
        f"Use <code>/replyticket {ticket_id} &lt;message&gt;</code> to reply."
    )
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML")
        except Exception as exc:
            logger.error("Failed to notify admin %s | error=%s", admin_id, exc)


async def forward_to_admins(bot: Bot, ticket_id: int, user_name: str, text: str) -> None:
    """Forward a user support message to all admins."""
    msg_text = (
        f"💬 <b>Ticket #{ticket_id}</b> (User: {user_name}):\n"
        f"<i>{text}</i>"
    )
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=msg_text, parse_mode="HTML")
        except Exception as exc:
            logger.error("Failed to forward user support message to admin %s | error=%s", admin_id, exc)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

@router.message(Command("support"))
async def handle_support_start(
    message: Message,
    state: FSMContext,
    support_service: SupportService,
) -> None:
    """
    Handle /support — start a support session.

    Retrieves or creates a ticket, updates FSM state.
    """
    user = message.from_user
    if user is None:
        return

    try:
        # Get or create ticket
        ticket = await support_service.get_or_create_ticket(user.id)

        await state.set_state(SupportStates.waiting_for_user)
        await state.update_data(ticket_id=ticket.id)

        # Notify user with persistent support menu options keyboard
        if ticket.is_assigned_to_human:
            await message.answer(
                "💬 <b>Support Session Active</b>\n\n"
                "You have been connected to human support. "
                "Type your message below and a support agent will reply to you.\n\n"
                "Send /exit to close support.",
                parse_mode="HTML",
                reply_markup=get_support_menu_keyboard(),
            )
        else:
            await message.answer(
                "💬 <b>Support Assistant</b>\n\n"
                "How can I help you today? You can ask me any question. "
                "If you need to speak with a human, just send /human.\n\n"
                "Send /exit at any time to end support.",
                parse_mode="HTML",
                reply_markup=get_support_menu_keyboard(),
            )
        logger.info("User entered support state | user_id=%s | ticket_id=%s", user.id, ticket.id)

    except Exception:
        logger.exception("handle_support_start failed | user_id=%s", user.id)
        await message.answer(MSG_ERROR_GENERIC)


@router.message(SupportStates.waiting_for_user, Command("exit"))
async def handle_support_exit(
    message: Message,
    state: FSMContext,
    support_service: SupportService,
) -> None:
    """Exit support and close the ticket."""
    user = message.from_user
    if user is None:
        return

    data = await state.get_data()
    ticket_id = data.get("ticket_id")

    try:
        if ticket_id:
            await support_service.close_ticket(ticket_id)

        await state.clear()
        await message.answer(
            "❌ <b>Support Chat Closed</b>\n\n"
            "Your support session has ended. You are now back to the main menu.",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
        logger.info("User exited support chat | user_id=%s | ticket_id=%s", user.id, ticket_id)
    except Exception:
        logger.exception("handle_support_exit failed | user_id=%s | ticket_id=%s", user.id, ticket_id)
        await state.clear()
        await message.answer(MSG_ERROR_GENERIC)


@router.message(SupportStates.waiting_for_user, Command("human"))
async def handle_support_human(
    message: Message,
    state: FSMContext,
    support_service: SupportService,
    bot: Bot,
) -> None:
    """Request human handoff."""
    user = message.from_user
    if user is None:
        return

    data = await state.get_data()
    ticket_id = data.get("ticket_id")

    if not ticket_id:
        await state.clear()
        await message.answer("❌ Session expired. Please run /support again.")
        return

    try:
        # Mark ticket as assigned to human
        ticket = await support_service.assign_to_human(ticket_id)

        await message.answer(
            "👨‍💻 <b>Human Support Requested</b>\n\n"
            "I have paused the AI assistant. A support agent has been notified "
            "and will reply to you shortly.",
            parse_mode="HTML",
        )

        # Notify admins
        user_name = user.full_name or user.first_name or "Unknown User"
        await alert_admins_new_ticket(bot, ticket_id, user_name, user.id)

    except Exception:
        logger.exception("handle_support_human failed | user_id=%s | ticket_id=%s", user.id, ticket_id)
        await message.answer(MSG_ERROR_GENERIC)


@router.message(SupportStates.waiting_for_user, F.text)
async def handle_support_message(
    message: Message,
    state: FSMContext,
    support_service: SupportService,
    ai_provider: AIProviderInterface,
    bot: Bot,
) -> None:
    """Process message in support FSM state."""
    user = message.from_user
    if user is None or not message.text:
        return

    # 0. Intercept custom persistent screen keyboard button clicks
    if message.text == "👨‍💻 Speak to Human":
        await handle_support_human(message, state, support_service, bot)
        return
    elif message.text == "❌ Exit Support":
        await handle_support_exit(message, state, support_service)
        return

    data = await state.get_data()
    ticket_id = data.get("ticket_id")

    if not ticket_id:
        await state.clear()
        await message.answer("❌ Session expired. Please run /support again.")
        return

    try:
        # 1. Fetch ticket status
        ticket = await support_service.get_ticket_with_messages(ticket_id)
        if not ticket or ticket.status.value != "open":
            await state.clear()
            await message.answer("❌ Ticket is already closed or does not exist. Use /support to open a new one.")
            return

        # 2. Log user's message
        await support_service.add_message(ticket_id, "user", message.text)

        # 3. Process reply
        user_name = user.full_name or user.first_name or "User"
        if ticket.is_assigned_to_human:
            # Human handoff: notify user of wait and forward message to admins
            await message.answer(
                "⏳ <b>Waiting for support agent...</b>\n\n"
                "Your message has been received by our support agents.",
                parse_mode="HTML",
            )
            await forward_to_admins(bot, ticket_id, user_name, message.text)
        else:
            # AI assistant responds
            # Format history for AI
            history = []
            if ticket.messages:
                # Map roles correctly: user -> user, ai/admin -> model/ai
                # We only pass last 10 messages to save context tokens
                for m in ticket.messages[-10:]:
                    role = "user" if m.sender_role == "user" else "ai"
                    history.append({"role": role, "text": m.text})

            # Call AI
            ai_reply = await ai_provider.generate_response(message.text, history)

            # Send response to user and log it
            await message.answer(ai_reply)
            await support_service.add_message(ticket_id, "ai", ai_reply)

    except Exception:
        logger.exception("handle_support_message failed | user_id=%s | ticket_id=%s", user.id, ticket_id)
        await message.answer(MSG_ERROR_GENERIC)


@router.message(SupportStates.waiting_for_user)
async def handle_support_wrong_input(message: Message) -> None:
    """Remind user that support chat only accepts text messages."""
    await message.answer(
        "⚠️ Support chat only accepts text messages.\n"
        "Send /exit to close support."
    )
