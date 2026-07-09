"""
tests/unit/test_user_service.py

Unit tests for services/user_service.py

Strategy:
  - Mock UserRepository to isolate service logic.
  - Test register_or_update, get_user, is_banned, ban_user, unban_user.
  - Verify correct repository methods are called with correct arguments.
  - Test is_banned fails open on DB error.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from schemas.user import UserCreateSchema, UserSchema
from services.user_service import UserService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_user_schema(**overrides) -> UserSchema:
    """Return a UserSchema with sensible defaults."""
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
    return UserSchema(**base)


def _make_tg_user(
    user_id: int = 123456789,
    username: str = "test_user",
    first_name: str = "Test",
    last_name: str = "User",
    language_code: str = "en",
) -> MagicMock:
    """Return a mock Telegram User object."""
    tg_user = MagicMock()
    tg_user.id = user_id
    tg_user.username = username
    tg_user.first_name = first_name
    tg_user.last_name = last_name
    tg_user.full_name = f"{first_name} {last_name}"
    tg_user.language_code = language_code
    return tg_user


@pytest.fixture
def mock_repo() -> AsyncMock:
    repo = AsyncMock()
    return repo


@pytest.fixture
def user_service(mock_repo: AsyncMock) -> UserService:
    return UserService(mock_repo)


# ---------------------------------------------------------------------------
# register_or_update
# ---------------------------------------------------------------------------

class TestRegisterOrUpdate:

    @pytest.mark.asyncio
    async def test_calls_upsert_with_correct_data(
        self, user_service: UserService, mock_repo: AsyncMock
    ):
        """register_or_update should call repo.upsert with correct UserCreateSchema."""
        expected_user = _make_user_schema()
        mock_repo.upsert.return_value = expected_user

        tg_user = _make_tg_user()
        result = await user_service.register_or_update(tg_user)

        mock_repo.upsert.assert_awaited_once()
        call_arg: UserCreateSchema = mock_repo.upsert.call_args[0][0]
        assert call_arg.id == tg_user.id
        assert call_arg.username == tg_user.username
        assert call_arg.full_name == tg_user.full_name
        assert result == expected_user

    @pytest.mark.asyncio
    async def test_uses_first_name_when_full_name_is_empty(
        self, user_service: UserService, mock_repo: AsyncMock
    ):
        """If full_name is falsy, fall back to first_name."""
        tg_user = _make_tg_user()
        tg_user.full_name = ""
        tg_user.first_name = "OnlyFirst"

        expected_user = _make_user_schema(full_name="OnlyFirst")
        mock_repo.upsert.return_value = expected_user

        await user_service.register_or_update(tg_user)

        call_arg: UserCreateSchema = mock_repo.upsert.call_args[0][0]
        assert call_arg.full_name == "OnlyFirst"

    @pytest.mark.asyncio
    async def test_defaults_language_code_to_en(
        self, user_service: UserService, mock_repo: AsyncMock
    ):
        """If language_code is None, default to 'en'."""
        tg_user = _make_tg_user()
        tg_user.language_code = None

        mock_repo.upsert.return_value = _make_user_schema()
        await user_service.register_or_update(tg_user)

        call_arg: UserCreateSchema = mock_repo.upsert.call_args[0][0]
        assert call_arg.language_code == "en"


# ---------------------------------------------------------------------------
# get_user
# ---------------------------------------------------------------------------

class TestGetUser:

    @pytest.mark.asyncio
    async def test_returns_user_when_found(
        self, user_service: UserService, mock_repo: AsyncMock
    ):
        expected = _make_user_schema()
        mock_repo.get_by_id.return_value = expected
        result = await user_service.get_user(123456789)
        assert result == expected
        mock_repo.get_by_id.assert_awaited_once_with(123456789)

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(
        self, user_service: UserService, mock_repo: AsyncMock
    ):
        mock_repo.get_by_id.return_value = None
        result = await user_service.get_user(999)
        assert result is None


# ---------------------------------------------------------------------------
# is_banned
# ---------------------------------------------------------------------------

class TestIsBanned:

    @pytest.mark.asyncio
    async def test_returns_true_for_banned_user(
        self, user_service: UserService, mock_repo: AsyncMock
    ):
        mock_repo.get_by_id.return_value = _make_user_schema(is_banned=True)
        result = await user_service.is_banned(123456789)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_for_active_user(
        self, user_service: UserService, mock_repo: AsyncMock
    ):
        mock_repo.get_by_id.return_value = _make_user_schema(is_banned=False)
        result = await user_service.is_banned(123456789)
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_unknown_user(
        self, user_service: UserService, mock_repo: AsyncMock
    ):
        """Unregistered users are not banned."""
        mock_repo.get_by_id.return_value = None
        result = await user_service.is_banned(999)
        assert result is False

    @pytest.mark.asyncio
    async def test_fails_open_on_db_error(
        self, user_service: UserService, mock_repo: AsyncMock
    ):
        """On DB failure, is_banned must return False (fail open)."""
        from core.exceptions import DatabaseConnectionError
        mock_repo.get_by_id.side_effect = DatabaseConnectionError("DB down")
        result = await user_service.is_banned(123456789)
        assert result is False


# ---------------------------------------------------------------------------
# ban_user / unban_user
# ---------------------------------------------------------------------------

class TestBanUnban:

    @pytest.mark.asyncio
    async def test_ban_user_calls_repo_ban(
        self, user_service: UserService, mock_repo: AsyncMock
    ):
        expected = _make_user_schema(is_banned=True, ban_reason="spam")
        mock_repo.ban.return_value = expected

        result = await user_service.ban_user(123456789, "spam")

        mock_repo.ban.assert_awaited_once_with(123456789, "spam")
        assert result.is_banned is True

    @pytest.mark.asyncio
    async def test_unban_user_calls_repo_unban(
        self, user_service: UserService, mock_repo: AsyncMock
    ):
        expected = _make_user_schema(is_banned=False, ban_reason=None)
        mock_repo.unban.return_value = expected

        result = await user_service.unban_user(123456789)

        mock_repo.unban.assert_awaited_once_with(123456789)
        assert result.is_banned is False
