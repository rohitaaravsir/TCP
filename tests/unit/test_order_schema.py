"""
tests/unit/test_order_schema.py

Unit tests for schemas/order.py

Validates:
  - OrderStatus enum values and display labels
  - OrderSchema accepts valid data and rejects missing fields
  - OrderCreateSchema constraints
  - OrderUpdateSchema partial updates
  - OrderSummarySchema lightweight view
  - amount_display and status_display properties
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from schemas.order import (
    OrderCreateSchema,
    OrderSchema,
    OrderStatus,
    OrderSummarySchema,
    OrderUpdateSchema,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_order_data(**overrides) -> dict:
    base = {
        "id": 1,
        "user_id": 123456789,
        "product_id": 5,
        "amount": Decimal("99.99"),
        "status": OrderStatus.PENDING,
        "payment_proof": None,
        "notes": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# OrderStatus
# ---------------------------------------------------------------------------

class TestOrderStatus:

    def test_all_statuses_have_display_labels(self):
        for status in OrderStatus:
            assert status.display  # Non-empty string

    def test_pending_display(self):
        assert OrderStatus.PENDING.display == "⏳ Pending"

    def test_confirmed_display(self):
        assert OrderStatus.CONFIRMED.display == "✅ Confirmed"

    def test_delivered_display(self):
        assert OrderStatus.DELIVERED.display == "📦 Delivered"

    def test_cancelled_display(self):
        assert OrderStatus.CANCELLED.display == "❌ Cancelled"

    def test_payment_submitted_display(self):
        assert OrderStatus.PAYMENT_SUBMITTED.display == "💳 Payment Submitted"

    def test_refunded_display(self):
        assert OrderStatus.REFUNDED.display == "↩️ Refunded"

    def test_status_is_string_enum(self):
        """Status values must be strings for Supabase compatibility."""
        assert OrderStatus.PENDING.value == "pending"
        assert isinstance(OrderStatus.CONFIRMED, str)


# ---------------------------------------------------------------------------
# OrderSchema
# ---------------------------------------------------------------------------

class TestOrderSchema:

    def test_valid_order_creates_successfully(self):
        order = OrderSchema(**_make_order_data())
        assert order.id == 1
        assert order.status == OrderStatus.PENDING

    def test_amount_display_formats_correctly(self):
        order = OrderSchema(**_make_order_data(amount=Decimal("149.50")))
        assert order.amount_display == "₹149.50"

    def test_status_display_uses_enum_property(self):
        order = OrderSchema(**_make_order_data(status=OrderStatus.CONFIRMED))
        assert order.status_display == "✅ Confirmed"

    def test_payment_proof_can_be_none(self):
        order = OrderSchema(**_make_order_data(payment_proof=None))
        assert order.payment_proof is None

    def test_missing_user_id_raises(self):
        data = _make_order_data()
        del data["user_id"]
        with pytest.raises(ValidationError):
            OrderSchema(**data)

    def test_missing_product_id_raises(self):
        data = _make_order_data()
        del data["product_id"]
        with pytest.raises(ValidationError):
            OrderSchema(**data)

    def test_missing_amount_raises(self):
        data = _make_order_data()
        del data["amount"]
        with pytest.raises(ValidationError):
            OrderSchema(**data)


# ---------------------------------------------------------------------------
# OrderCreateSchema
# ---------------------------------------------------------------------------

class TestOrderCreateSchema:

    def test_valid_create_schema(self):
        schema = OrderCreateSchema(
            user_id=111, product_id=5, amount=Decimal("49.99")
        )
        assert schema.user_id == 111
        assert schema.amount == Decimal("49.99")

    def test_zero_amount_is_valid(self):
        """Free orders (amount=0) must be allowed."""
        schema = OrderCreateSchema(user_id=1, product_id=1, amount=Decimal("0"))
        assert schema.amount == Decimal("0")

    def test_negative_amount_raises(self):
        with pytest.raises(ValidationError):
            OrderCreateSchema(user_id=1, product_id=1, amount=Decimal("-1"))

    def test_missing_user_id_raises(self):
        with pytest.raises(ValidationError):
            OrderCreateSchema(product_id=1, amount=Decimal("10"))  # type: ignore

    def test_missing_product_id_raises(self):
        with pytest.raises(ValidationError):
            OrderCreateSchema(user_id=1, amount=Decimal("10"))  # type: ignore


# ---------------------------------------------------------------------------
# OrderUpdateSchema
# ---------------------------------------------------------------------------

class TestOrderUpdateSchema:

    def test_all_none_is_valid(self):
        schema = OrderUpdateSchema()
        assert schema.status is None
        assert schema.payment_proof is None

    def test_status_only_update(self):
        schema = OrderUpdateSchema(status=OrderStatus.CONFIRMED)
        data = schema.model_dump(exclude_none=True)
        assert data == {"status": OrderStatus.CONFIRMED}

    def test_payment_proof_with_status(self):
        schema = OrderUpdateSchema(
            status=OrderStatus.PAYMENT_SUBMITTED,
            payment_proof="file_abc123",
        )
        data = schema.model_dump(exclude_none=True)
        assert "payment_proof" in data
        assert data["status"] == OrderStatus.PAYMENT_SUBMITTED


# ---------------------------------------------------------------------------
# OrderSummarySchema
# ---------------------------------------------------------------------------

class TestOrderSummarySchema:

    def test_valid_summary(self):
        summary = OrderSummarySchema(
            id=10,
            product_id=3,
            amount=Decimal("79.00"),
            status=OrderStatus.DELIVERED,
            created_at=datetime.now(timezone.utc),
        )
        assert summary.amount_display == "₹79.00"
        assert summary.status_display == "📦 Delivered"
