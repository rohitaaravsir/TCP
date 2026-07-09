"""
bot/middlewares/ban_check.py

Aiogram middleware that blocks banned users before any handler runs.

Responsibilities:
  - On every incoming Update, check if the sender is banned.
  - If banned: reply with a single message and stop the update.
  - If not banned: pass the update through to the next handler.

Rules (from PROJECT_RULES.md — Rule 5 & Rule 13):
  - Middleware calls services; it never touches the DB directly.
  - The system must never crash due to user input or DB issues.
  - On DB failure, fail open (do not block the user).

Usage:
    from bot.middlewares.ban_check import BanCheckMiddleware
    dp.message.middleware(BanCheckMiddleware(user_service))
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, Update

from services.user_service import UserService

logger = logging.getLogger(__name__)

_BAN_MESSAGE = (
    "🚫 Your account has been suspended.\n\n"
    "If you believe this is a mistake, please contact support."
)


class BanCheckMiddleware(BaseMiddleware):
    """
    Outer middleware that intercepts every incoming update.

    Checks whether the user associated with the update is banned.
    Banned users receive a single informational message and no further
    processing occurs.

    Args:
        user_service: An initialised UserService instance.
    """

    def __init__(self, user_service: UserService) -> None:
        self._user_service = user_service
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Intercept every update and check ban status before passing through.
        """
        # Extract the Telegram user from the event
        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, Update):
            # Unwrap common update types
            if event.message and event.message.from_user:
                user = event.message.from_user
            elif event.callback_query and event.callback_query.from_user:
                user = event.callback_query.from_user

        if user is not None:
            is_banned = await self._user_service.is_banned(user.id)

            if is_banned:
                logger.warning(
                    "Blocked banned user | user_id=%s | event=user.blocked",
                    user.id,
                )
                # Reply only to Message events (not to callback_query etc.)
                if isinstance(event, Message):
                    await event.answer(_BAN_MESSAGE)
                elif isinstance(event, Update) and event.message:
                    await event.message.answer(_BAN_MESSAGE)

                # Do NOT call the next handler
                return

        # User is not banned (or not identifiable) — continue normally
        return await handler(event, data)
