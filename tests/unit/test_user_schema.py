"""
tests/unit/test_user_schema.py

Unit tests for schemas/user.py

Validates:
  - UserSchema accepts valid data
  - UserSchema rejects missing required fields
  - UserCreateSchema enforces full_name is non-empty
  - UserUpdateSchema allows all-None (partial update)
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from schemas.user import UserCreateSchema, UserSchema, UserUpdateSchema


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user_data(**overrides) -> dict:
    """Return a minimal valid dict for UserSchema."""
    base = {
        "id": 123456789,
        "username": "test_user",
        "full_name": "Test User",
        "language_code": "en",
        "is_banned": False,
        "ban_reason": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# UserSchema
# ---------------------------------------------------------------------------

class TestUserSchema:
    """Tests for the full read model."""

    def test_valid_user_creates_successfully(self):
        data = _make_user_data()
        user = UserSchema(**data)
        assert user.id == 123456789
        assert user.full_name == "Test User"
        assert user.is_banned is False

    def test_username_can_be_none(self):
        data = _make_user_data(username=None)
        user = UserSchema(**data)
        assert user.username is None

    def test_ban_reason_can_be_none(self):
        data = _make_user_data(ban_reason=None)
        user = UserSchema(**data)
        assert user.ban_reason is None

    def test_missing_required_id_raises(self):
        data = _make_user_data()
        del data["id"]
        with pytest.raises(ValidationError):
            UserSchema(**data)

    def test_missing_required_full_name_raises(self):
        data = _make_user_data()
        del data["full_name"]
        with pytest.raises(ValidationError):
            UserSchema(**data)

    def test_missing_timestamps_raises(self):
        data = _make_user_data()
        del data["created_at"]
        with pytest.raises(ValidationError):
            UserSchema(**data)


# ---------------------------------------------------------------------------
# UserCreateSchema
# ---------------------------------------------------------------------------

class TestUserCreateSchema:
    """Tests for the creation input schema."""

    def test_valid_create_schema(self):
        schema = UserCreateSchema(
            id=111,
            username="newuser",
            full_name="New User",
            language_code="hi",
        )
        assert schema.id == 111
        assert schema.language_code == "hi"

    def test_language_code_defaults_to_en(self):
        schema = UserCreateSchema(id=222, full_name="No Lang")
        assert schema.language_code == "en"

    def test_username_is_optional(self):
        schema = UserCreateSchema(id=333, full_name="No Username")
        assert schema.username is None

    def test_empty_full_name_raises(self):
        with pytest.raises(ValidationError):
            UserCreateSchema(id=444, full_name="")

    def test_missing_id_raises(self):
        with pytest.raises(ValidationError):
            UserCreateSchema(full_name="No ID")  # type: ignore[call-arg]

    def test_missing_full_name_raises(self):
        with pytest.raises(ValidationError):
            UserCreateSchema(id=555)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# UserUpdateSchema
# ---------------------------------------------------------------------------

class TestUserUpdateSchema:
    """Tests for the partial update schema."""

    def test_all_none_is_valid(self):
        """An empty update (all fields None) is a valid no-op."""
        schema = UserUpdateSchema()
        assert schema.full_name is None
        assert schema.is_banned is None

    def test_partial_update_only_sets_given_fields(self):
        schema = UserUpdateSchema(is_banned=True, ban_reason="spam")
        data = schema.model_dump(exclude_none=True)
        assert data == {"is_banned": True, "ban_reason": "spam"}
        assert "username" not in data

    def test_empty_full_name_raises(self):
        with pytest.raises(ValidationError):
            UserUpdateSchema(full_name="")
