"""
schemas/user.py

Pydantic schemas for the User domain.

These schemas are the data contracts between layers:
  - UserSchema       — full model returned from DB (read)
  - UserCreateSchema — fields needed to create a new user
  - UserUpdateSchema — optional fields for partial updates

Rules (from PROJECT_RULES.md — Rule 18):
  - Schemas are reusable, testable, and decoupled from Telegram/DB concerns.
  - All data flowing through the system must be validated by schemas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UserSchema(BaseModel):
    """
    Full user record as stored in Supabase.

    This is the canonical read model for the User domain.
    """

    id: int = Field(..., description="Telegram user ID (primary key).")
    username: str | None = Field(None, description="Telegram @username (may be absent).")
    full_name: str = Field(..., description="Display name from Telegram.")
    language_code: str = Field(default="en", description="IETF language tag from Telegram.")
    is_banned: bool = Field(default=False, description="Whether the user is banned.")
    ban_reason: str | None = Field(None, description="Reason for ban (if applicable).")
    created_at: datetime = Field(..., description="UTC timestamp of first registration.")
    updated_at: datetime = Field(..., description="UTC timestamp of last profile update.")

    model_config = {"from_attributes": True}


class UserCreateSchema(BaseModel):
    """
    Fields required (or allowed) when registering a new user.

    Sourced directly from a Telegram User object on /start.
    """

    id: int = Field(..., description="Telegram user ID.")
    username: str | None = Field(None, description="Telegram @username.")
    full_name: str = Field(..., min_length=1, description="Display name (must not be empty).")
    language_code: str = Field(default="en", description="IETF language tag.")


class UserUpdateSchema(BaseModel):
    """
    Partial update schema — all fields are optional.

    Only the provided fields will be written to the database.
    """

    username: str | None = None
    full_name: str | None = Field(None, min_length=1)
    language_code: str | None = None
    is_banned: bool | None = None
    ban_reason: str | None = None
