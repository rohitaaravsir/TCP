"""
tests/unit/test_order_service.py

Unit tests for services/order_service.py

Strategy:
  - Mock OrderRepository and ProductRepository to isolate service logic.
  - Test place_order (success + product not found + inactive product)
  - Test cancel_order (ownership check + state validation)
  - Test submit_payment_proof (state + ownership)
  - Test admin operations: confirm, deliver, list_pending_payments
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from schemas.order import (
    OrderCreateSchema,
    OrderSchema,
    OrderStatus,
    OrderSummarySchema,
    OrderUpdateSchema,
)
from schemas.product import ProductSchema
from services.order_service import OrderService, OrderServiceError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_order(**overrides) -> OrderSchema:
    base = {
        "id": 1,
        "user_id": 111,
        "product_id": 5,
        "amount": Decimal("99.99"),
        "status": OrderStatus.PENDING,
        "payment_proof": None,
        "notes": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return OrderSchema(**base)


def _make_product(product_id: int = 5, is_active: bool = True) -> ProductSchema:
    return ProductSchema(
        id=product_id,
        name="Test Product",
        description=None,
        price=Decimal("99.99"),
        category="general",
        file_id=None,
        is_active=is_active,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_order_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_product_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def order_service(mock_order_repo: AsyncMock, mock_product_repo: AsyncMock) -> OrderService:
    return OrderService(mock_order_repo, mock_product_repo)


# ---------------------------------------------------------------------------
# place_order
# ---------------------------------------------------------------------------

class TestPlaceOrder:

    async def test_creates_order_with_snapshotted_price(
        self, order_service: OrderService,
        mock_order_repo: AsyncMock, mock_product_repo: AsyncMock
    ):
        product = _make_product()
        expected_order = _make_order()
        mock_product_repo.get_by_id.return_value = product
        mock_order_repo.create.return_value = expected_order

        result = await order_service.place_order(user_id=111, product_id=5)

        mock_product_repo.get_by_id.assert_awaited_once_with(5)
        mock_order_repo.create.assert_awaited_once()
        # Verify price was snapshotted from product
        call_arg: OrderCreateSchema = mock_order_repo.create.call_args[0][0]
        assert call_arg.amount == product.price
        assert result.id == 1

    async def test_raises_if_product_not_found(
        self, order_service: OrderService, mock_product_repo: AsyncMock
    ):
        mock_product_repo.get_by_id.return_value = None
        with pytest.raises(OrderServiceError, match="does not exist"):
            await order_service.place_order(user_id=111, product_id=999)

    async def test_raises_if_product_inactive(
        self, order_service: OrderService, mock_product_repo: AsyncMock
    ):
        mock_product_repo.get_by_id.return_value = _make_product(is_active=False)
        with pytest.raises(OrderServiceError, match="no longer available"):
            await order_service.place_order(user_id=111, product_id=5)


# ---------------------------------------------------------------------------
# get_order / list_user_orders
# ---------------------------------------------------------------------------

class TestGetOrders:

    async def test_get_order_returns_schema(
        self, order_service: OrderService, mock_order_repo: AsyncMock
    ):
        expected = _make_order()
        mock_order_repo.get_by_id.return_value = expected
        result = await order_service.get_order(1)
        assert result == expected

    async def test_get_order_returns_none_when_missing(
        self, order_service: OrderService, mock_order_repo: AsyncMock
    ):
        mock_order_repo.get_by_id.return_value = None
        result = await order_service.get_order(999)
        assert result is None

    async def test_list_user_orders_calls_repo(
        self, order_service: OrderService, mock_order_repo: AsyncMock
    ):
        summaries = [
            OrderSummarySchema(
                id=i, product_id=5, amount=Decimal("10"),
                status=OrderStatus.PENDING,
                created_at=datetime.now(timezone.utc),
            ) for i in range(3)
        ]
        mock_order_repo.list_by_user.return_value = summaries

        result = await order_service.list_user_orders(111)
        mock_order_repo.list_by_user.assert_awaited_once_with(111, limit=10)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# cancel_order
# ---------------------------------------------------------------------------

class TestCancelOrder:

    async def test_cancels_pending_order(
        self, order_service: OrderService, mock_order_repo: AsyncMock
    ):
        pending = _make_order(status=OrderStatus.PENDING)
        cancelled = _make_order(status=OrderStatus.CANCELLED)
        mock_order_repo.get_by_id.return_value = pending
        mock_order_repo.update_status.return_value = cancelled

        result = await order_service.cancel_order(order_id=1, user_id=111)

        mock_order_repo.update_status.assert_awaited_once_with(1, OrderStatus.CANCELLED)
        assert result.status == OrderStatus.CANCELLED

    async def test_raises_if_order_not_found(
        self, order_service: OrderService, mock_order_repo: AsyncMock
    ):
        mock_order_repo.get_by_id.return_value = None
        with pytest.raises(OrderServiceError, match="not found"):
            await order_service.cancel_order(order_id=999, user_id=111)

    async def test_raises_if_wrong_user(
        self, order_service: OrderService, mock_order_repo: AsyncMock
    ):
        order = _make_order(user_id=999)  # Different user
        mock_order_repo.get_by_id.return_value = order
        with pytest.raises(OrderServiceError, match="permission"):
            await order_service.cancel_order(order_id=1, user_id=111)

    async def test_raises_if_already_confirmed(
        self, order_service: OrderService, mock_order_repo: AsyncMock
    ):
        order = _make_order(status=OrderStatus.CONFIRMED)
        mock_order_repo.get_by_id.return_value = order
        with pytest.raises(OrderServiceError, match="cannot be cancelled"):
            await order_service.cancel_order(order_id=1, user_id=111)


# ---------------------------------------------------------------------------
# submit_payment_proof
# ---------------------------------------------------------------------------

class TestSubmitPaymentProof:

    async def test_submits_proof_for_pending_order(
        self, order_service: OrderService, mock_order_repo: AsyncMock
    ):
        pending = _make_order(status=OrderStatus.PENDING)
        submitted = _make_order(
            status=OrderStatus.PAYMENT_SUBMITTED,
            payment_proof="file_abc123",
        )
        mock_order_repo.get_by_id.return_value = pending
        mock_order_repo.update.return_value = submitted

        result = await order_service.submit_payment_proof(
            order_id=1, user_id=111, file_id="file_abc123"
        )

        assert result.status == OrderStatus.PAYMENT_SUBMITTED
        assert result.payment_proof == "file_abc123"

    async def test_raises_if_not_pending(
        self, order_service: OrderService, mock_order_repo: AsyncMock
    ):
        order = _make_order(status=OrderStatus.CONFIRMED)
        mock_order_repo.get_by_id.return_value = order
        with pytest.raises(OrderServiceError, match="pending orders"):
            await order_service.submit_payment_proof(1, 111, "file_xyz")


# ---------------------------------------------------------------------------
# Admin operations
# ---------------------------------------------------------------------------

class TestAdminOperations:

    async def test_confirm_order(
        self, order_service: OrderService, mock_order_repo: AsyncMock
    ):
        confirmed = _make_order(status=OrderStatus.CONFIRMED)
        mock_order_repo.update_status.return_value = confirmed
        result = await order_service.confirm_order(1)
        mock_order_repo.update_status.assert_awaited_once_with(1, OrderStatus.CONFIRMED)
        assert result.status == OrderStatus.CONFIRMED

    async def test_mark_delivered(
        self, order_service: OrderService, mock_order_repo: AsyncMock
    ):
        delivered = _make_order(status=OrderStatus.DELIVERED)
        mock_order_repo.update_status.return_value = delivered
        result = await order_service.mark_delivered(1)
        assert result.status == OrderStatus.DELIVERED

    async def test_list_pending_payments(
        self, order_service: OrderService, mock_order_repo: AsyncMock
    ):
        orders = [_make_order(status=OrderStatus.PAYMENT_SUBMITTED)]
        mock_order_repo.list_by_status.return_value = orders
        result = await order_service.list_pending_payments()
        mock_order_repo.list_by_status.assert_awaited_once_with(
            OrderStatus.PAYMENT_SUBMITTED
        )
        assert len(result) == 1
