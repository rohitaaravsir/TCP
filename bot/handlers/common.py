"""
bot/handlers/common.py

Common bot command handlers.

Handlers:
  - /start  — Register/update user and send welcome message
  - /help   — List available commands
  - /ping   — Health check with latency display

Rules (from PROJECT_RULES.md — Rule 5):
  - Handlers receive updates and call services.
  - No business logic is permitted here.
  - No direct database access is permitted here.
"""

import time

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import settings
from core.constants import MSG_HELP_USER, MSG_HELP_ADMIN, MSG_PING, MSG_START
from core.logger import get_logger
from services.user_service import UserService

logger = get_logger(__name__)

router = Router(name="common")


@router.message(Command("start"))
async def handle_start(message: Message, user_service: UserService) -> None:
    """
    Handle the /start command.

    Registers or updates the user in the database, then sends a
    personalised welcome message.  UserService is injected via the
    dispatcher workflow data — no business logic lives here.
    """
    tg_user = message.from_user
    if tg_user is None:
        return

    # Delegate to service — register new users or refresh existing ones
    user = await user_service.register_or_update(tg_user)

    logger.info(
        "User started bot | user_id=%s | username=%s",
        user.id,
        user.username,
    )

    text = MSG_START.format(shop_name="TCP Shop", user_name=user.full_name)
    await message.answer(text)


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """
    Handle the /help command.

    Displays the list of available commands, customized by role.
    """
    user = message.from_user
    user_id = user.id if user else 0
    is_admin = user_id in settings.admin_ids

    logger.info(
        "User requested help | user_id=%s | is_admin=%s",
        user_id,
        is_admin,
    )

    text = MSG_HELP_USER
    if is_admin:
        text += "\n\n" + MSG_HELP_ADMIN

    await message.answer(text, parse_mode="HTML")



@router.message(Command("ping"))
async def handle_ping(message: Message) -> None:
    """
    Handle the /ping command.

    Measures round-trip latency by recording time before and after
    sending a temporary message, then editing it with the result.
    """
    start_time = time.monotonic()
    sent = await message.answer("🏓 Pinging...")
    latency_ms = round((time.monotonic() - start_time) * 1000)

    await sent.edit_text(MSG_PING.format(latency_ms=latency_ms))

    logger.info(
        "Ping handled | user_id=%s | latency_ms=%d",
        message.from_user.id if message.from_user else "unknown",
        latency_ms,
    )
