"""
services/user_service.py

Business logic layer for the User domain.

Responsibilities:
  - Register or update a user on /start (upsert)
  - Look up a user by Telegram ID
  - Ban / unban users
  - Check ban status (used by ban middleware)

Rules (from PROJECT_RULES.md — Rule 6):
  - All business logic lives in services.
  - Services call repositories; they never touch Supabase directly.
  - Handlers call services; they never call repositories.

Usage:
    from services.user_service import UserService
    service = UserService(user_repo)
    user = await service.register_or_update(tg_user)
"""

from __future__ import annotations

import logging

from aiogram.types import User as TelegramUser

from core.exceptions import DatabaseConnectionError
from repositories.user_repository import UserRepository
from schemas.user import UserCreateSchema, UserSchema

logger = logging.getLogger(__name__)


class UserService:
    """
    Orchestrates user-related business operations.

    Args:
        repository: An initialised UserRepository instance.
    """

    def __init__(self, repository: UserRepository) -> None:
        self._repo = repository

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    async def register_or_update(self, tg_user: TelegramUser) -> UserSchema:
        """
        Register a new user or refresh an existing user's profile.

        Called on every /start command.  Uses upsert so the operation
        is idempotent and safe to call repeatedly.

        Args:
            tg_user: The Telegram User object from the incoming message.

        Returns:
            The current (created or updated) UserSchema.

        Raises:
            DatabaseConnectionError: On Supabase failure.
        """
        full_name = tg_user.full_name or tg_user.first_name or "Unknown"

        data = UserCreateSchema(
            id=tg_user.id,
            username=tg_user.username,
            full_name=full_name,
            language_code=tg_user.language_code or "en",
        )

        user = await self._repo.upsert(data)

        logger.info(
            "User registered/updated | user_id=%s | username=%s | event=user.registered",
            user.id,
            user.username,
        )
        return user

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    async def get_user(self, user_id: int) -> UserSchema | None:
        """
        Fetch a user by their Telegram ID.

        Returns:
            UserSchema if found, None if the user does not exist.
        """
        return await self._repo.get_by_id(user_id)

    # ------------------------------------------------------------------
    # Ban system
    # ------------------------------------------------------------------

    async def is_banned(self, user_id: int) -> bool:
        """
        Check whether a user is currently banned.

        Returns False if the user does not exist (unregistered users
        are not considered banned; they will be registered on /start).

        Args:
            user_id: Telegram user ID to check.

        Returns:
            True if the user exists and is_banned is True, else False.
        """
        try:
            user = await self._repo.get_by_id(user_id)
            return user is not None and user.is_banned
        except DatabaseConnectionError:
            # On DB failure, fail open (do not block the user)
            logger.warning(
                "is_banned check failed for user_id=%s — failing open", user_id
            )
            return False

    async def ban_user(self, user_id: int, reason: str = "No reason provided.") -> UserSchema:
        """
        Ban a user and record the reason.

        Args:
            user_id: Telegram user ID to ban.
            reason:  Human-readable ban reason.

        Returns:
            The updated UserSchema with is_banned=True.

        Raises:
            DatabaseConnectionError: On Supabase failure.
        """
        user = await self._repo.ban(user_id, reason)
        logger.warning(
            "User banned | user_id=%s | reason=%s | event=user.banned",
            user_id,
            reason,
        )
        return user

    async def unban_user(self, user_id: int) -> UserSchema:
        """
        Remove an existing ban from a user.

        Args:
            user_id: Telegram user ID to unban.

        Returns:
            The updated UserSchema with is_banned=False.

        Raises:
            DatabaseConnectionError: On Supabase failure.
        """
        user = await self._repo.unban(user_id)
        logger.info(
            "User unbanned | user_id=%s | event=user.unbanned",
            user_id,
        )
        return user

    async def list_all_users(self) -> list[UserSchema]:
        """
        Fetch all users from the database.

        Returns:
            A list of UserSchema objects.
        """
        return await self._repo.list_all()

