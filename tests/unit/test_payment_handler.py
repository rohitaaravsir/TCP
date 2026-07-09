"""
tests/unit/test_payment_handler.py

Unit tests for bot/handlers/payment.py
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, PhotoSize, User

from bot.handlers.payment import handle_pay_initiate, handle_payment_photo, handle_payment_cancel, handle_pay_proof_callback
from bot.states.payment import PaymentStates
from services.ocr_service import OCRResult
from services.order_service import OrderServiceError
from schemas.order import OrderSchema, OrderStatus


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

def _make_order_schema(order_id: int = 12, status: OrderStatus = OrderStatus.PENDING) -> OrderSchema:
    from datetime import datetime, timezone
    return OrderSchema(
        id=order_id,
        user_id=111,
        product_id=3,
        amount=Decimal("150.00"),
        status=status,
        payment_proof=None,
        notes=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_message() -> MagicMock:
    message = MagicMock(spec=Message)
    message.from_user = User(id=111, is_bot=False, first_name="Test", last_name="User", username="testuser")
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_state() -> AsyncMock:
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    return state


@pytest.fixture
def mock_order_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_ocr_service() -> AsyncMock:
    return AsyncMock()


# ---------------------------------------------------------------------------
# Tests: handle_pay_initiate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pay_initiate_success(mock_message, mock_state, mock_order_service):
    """Should validate order, update FSM data, set state, and send prompts."""
    mock_message.text = "/pay 12"
    order = _make_order_schema(order_id=12, status=OrderStatus.PENDING)
    mock_order_service.get_order.return_value = order

    await handle_pay_initiate(mock_message, mock_state, mock_order_service)

    mock_order_service.get_order.assert_awaited_once_with(12)
    mock_state.set_state.assert_awaited_once_with(PaymentStates.waiting_for_proof)
    mock_state.update_data.assert_awaited_once_with(order_id=12, amount="150.00")
    assert "Payment Submission" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_pay_initiate_missing_args(mock_message, mock_state, mock_order_service):
    """Should prompt usage details if arguments are missing."""
    mock_message.text = "/pay"
    await handle_pay_initiate(mock_message, mock_state, mock_order_service)

    mock_state.set_state.assert_not_called()
    assert "Usage" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_pay_initiate_not_found(mock_message, mock_state, mock_order_service):
    """Should inform user if order does not exist or belong to them."""
    mock_message.text = "/pay 999"
    mock_order_service.get_order.return_value = None

    await handle_pay_initiate(mock_message, mock_state, mock_order_service)

    mock_state.set_state.assert_not_called()
    assert "not found" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_pay_initiate_not_pending(mock_message, mock_state, mock_order_service):
    """Should prevent payment submission if order is not pending."""
    mock_message.text = "/pay 12"
    order = _make_order_schema(order_id=12, status=OrderStatus.CONFIRMED)
    mock_order_service.get_order.return_value = order

    await handle_pay_initiate(mock_message, mock_state, mock_order_service)

    mock_state.set_state.assert_not_called()
    assert "Cannot submit payment" in mock_message.answer.call_args[0][0]


# ---------------------------------------------------------------------------
# Tests: handle_payment_photo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_payment_photo_success_under_review(
    mock_message, mock_state, mock_order_service, mock_ocr_service
):
    """Should run OCR, submit proof, clear FSM, and notify under review."""
    mock_state.get_data.return_value = {"order_id": 12, "amount": "150.00", "order_created_at": None}
    
    photo = MagicMock(spec=PhotoSize)
    photo.file_id = "best_file_id"
    mock_message.photo = [photo]  # highest resolution at index 0 (since it's only 1 item)

    mock_ocr_service.verify_payment.return_value = OCRResult(
        confidence=0.0,
        requires_review=True,
        is_near_miss=False,
        detected_amount=None,
        detected_app="GPay",
        utr_number=None,
        raw_text="",
        notes="Review needed"
    )

    submitted_order = _make_order_schema(order_id=12, status=OrderStatus.PAYMENT_SUBMITTED)
    mock_order_service.submit_payment_proof.return_value = submitted_order

    mock_bot = AsyncMock()
    mock_file = MagicMock()
    mock_file.file_path = "photos/file.jpg"
    mock_bot.get_file.return_value = mock_file
    mock_bot.download_file.return_value = b"mocked_image_bytes"

    with patch("bot.handlers.payment.settings.feature_ocr_enabled", True):
        await handle_payment_photo(mock_message, mock_state, mock_order_service, mock_ocr_service, mock_bot)

    mock_ocr_service.verify_payment.assert_awaited_once_with(
        image_bytes=b"mocked_image_bytes",
        expected_amount=Decimal("150.00"),
        order_created_at=None
    )
    mock_order_service.submit_payment_proof.assert_awaited_once_with(
        order_id=12,
        user_id=111,
        file_id="best_file_id"
    )
    mock_state.clear.assert_awaited_once()
    assert "Screenshot Received" in mock_message.answer.call_args[0][0]



# ---------------------------------------------------------------------------
# Tests: handle_payment_cancel
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_payment_cancel(mock_message, mock_state):
    """Should clear state and send cancellation message."""
    await handle_payment_cancel(mock_message, mock_state)
    mock_state.clear.assert_awaited_once()
    assert "cancelled" in mock_message.answer.call_args[0][0]


# ---------------------------------------------------------------------------
# Tests: handle_pay_proof_callback
# ---------------------------------------------------------------------------

from aiogram.types import CallbackQuery

@pytest.mark.asyncio
async def test_handle_pay_proof_callback(mock_state, mock_order_service):
    """Should intercept click on pay proof callback and trigger handle_pay_initiate."""
    callback = MagicMock(spec=CallbackQuery)
    callback.data = "pay_proof:12"
    callback.answer = AsyncMock()
    callback.from_user = User(id=111, is_bot=False, first_name="Test", last_name="User")
    
    mock_msg = MagicMock(spec=Message)
    mock_msg.answer = AsyncMock()
    
    def fake_model_copy(update=None):
        copied = MagicMock(spec=Message)
        copied.from_user = update.get("from_user") if update else None
        copied.text = update.get("text") if update else None
        return copied
    mock_msg.model_copy = fake_model_copy
    callback.message = mock_msg

    with patch("bot.handlers.payment.handle_pay_initiate", new_callable=AsyncMock) as mock_initiate:
        await handle_pay_proof_callback(callback, mock_state, mock_order_service)
        
        callback.answer.assert_awaited_once()
        mock_initiate.assert_awaited_once()
        # Verify it extracts order_id correctly
        args = mock_initiate.call_args[0]
        assert args[0].text == "/pay 12"
        assert args[1] == mock_state
        assert args[2] == mock_order_service

