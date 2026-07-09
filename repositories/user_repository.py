"""
repositories/user_repository.py

Supabase-backed async repository for the User domain.

Responsibilities:
  - All direct Supabase table access for the `users` table.
  - Returns validated UserSchema objects — never raw dicts.
  - Raises domain exceptions on failure.

Rules (from PROJECT_RULES.md — Rule 7):
  - Only repositories may touch the database.
  - Services call repositories; handlers call services.
  - No business logic lives here — only data access.

Usage:
    from repositories.user_repository import UserRepository
    repo = UserRepository(db.client)
    user = await repo.get_by_id(123456789)
"""

from __future__ import annotations

import logging

from supabase import AsyncClient

from core.exceptions import DatabaseConnectionError
from schemas.user import UserCreateSchema, UserSchema, UserUpdateSchema

logger = logging.getLogger(__name__)

_TABLE = "users"


class UserRepository:
    """
    Async CRUD repository for the `users` Supabase table.

    Args:
        client: An active Supabase AsyncClient (from db.client).
    """

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_by_id(self, user_id: int) -> UserSchema | None:
        """
        Fetch a user by their Telegram ID.

        Returns:
            UserSchema if found, None if the user does not exist.

        Raises:
            DatabaseConnectionError: On unexpected Supabase errors.
        """
        try:
            response = (
                await self._client.table(_TABLE)
                .select("*")
                .eq("id", user_id)
                .limit(1)
                .execute()
            )
            if not response.data:
                return None
            return UserSchema(**response.data[0])
        except Exception as exc:
            logger.error("UserRepository.get_by_id failed | user_id=%s | error=%s", user_id, exc)
            raise DatabaseConnectionError(f"Failed to fetch user {user_id}: {exc}") from exc

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create(self, data: UserCreateSchema) -> UserSchema:
        """
        Insert a new user record.

        Returns:
            The newly created UserSchema.

        Raises:
            DatabaseConnectionError: On Supabase errors.
        """
        try:
            payload = data.model_dump()
            response = (
                await self._client.table(_TABLE)
                .insert(payload)
                .execute()
            )
            return UserSchema(**response.data[0])
        except Exception as exc:
            logger.error("UserRepository.create failed | user_id=%s | error=%s", data.id, exc)
            raise DatabaseConnectionError(f"Failed to create user {data.id}: {exc}") from exc

    async def upsert(self, data: UserCreateSchema) -> UserSchema:
        """
        Insert or update a user record (used on every /start).

        If the user already exists their profile fields (username,
        full_name, language_code, updated_at) are refreshed.

        Returns:
            The upserted UserSchema.

        Raises:
            DatabaseConnectionError: On Supabase errors.
        """
        try:
            payload = data.model_dump()
            # updated_at is managed by Supabase trigger or set explicitly here
            from datetime import datetime, timezone
            payload["updated_at"] = datetime.now(timezone.utc).isoformat()

            response = (
                await self._client.table(_TABLE)
                .upsert(payload, on_conflict="id")
                .execute()
            )
            return UserSchema(**response.data[0])
        except Exception as exc:
            logger.error("UserRepository.upsert failed | user_id=%s | error=%s", data.id, exc)
            raise DatabaseConnectionError(f"Failed to upsert user {data.id}: {exc}") from exc

    async def update(self, user_id: int, data: UserUpdateSchema) -> UserSchema:
        """
        Partially update a user record.

        Only fields explicitly set on `data` are written.

        Returns:
            The updated UserSchema.

        Raises:
            DatabaseConnectionError: On Supabase errors.
        """
        try:
            payload = data.model_dump(exclude_none=True)
            if not payload:
                # Nothing to update — fetch and return current state
                user = await self.get_by_id(user_id)
                if user is None:
                    raise DatabaseConnectionError(f"User {user_id} not found.")
                return user

            from datetime import datetime, timezone
            payload["updated_at"] = datetime.now(timezone.utc).isoformat()

            response = (
                await self._client.table(_TABLE)
                .update(payload)
                .eq("id", user_id)
                .execute()
            )
            return UserSchema(**response.data[0])
        except DatabaseConnectionError:
            raise
        except Exception as exc:
            logger.error("UserRepository.update failed | user_id=%s | error=%s", user_id, exc)
            raise DatabaseConnectionError(f"Failed to update user {user_id}: {exc}") from exc

    # ------------------------------------------------------------------
    # Ban / Unban
    # ------------------------------------------------------------------

    async def ban(self, user_id: int, reason: str) -> UserSchema:
        """
        Mark a user as banned with an optional reason.

        Returns:
            The updated UserSchema with is_banned=True.
        """
        return await self.update(
            user_id,
            UserUpdateSchema(is_banned=True, ban_reason=reason),
        )

    async def unban(self, user_id: int) -> UserSchema:
        """
        Remove the ban from a user.

        Returns:
            The updated UserSchema with is_banned=False.
        """
        return await self.update(
            user_id,
            UserUpdateSchema(is_banned=False, ban_reason=None),
        )

    async def list_all(self) -> list[UserSchema]:
        """
        Fetch all users from the database.

        Returns:
            A list of UserSchema objects.
        """
        try:
            response = (
                await self._client.table(_TABLE)
                .select("*")
                .execute()
            )
            return [UserSchema(**row) for row in response.data]
        except Exception as exc:
            logger.error("UserRepository.list_all failed | error=%s", exc)
            raise DatabaseConnectionError(f"Failed to list all users: {exc}") from exc

