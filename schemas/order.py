"""
schemas/order.py

Pydantic schemas for the Order domain.

Schemas:
  - OrderStatus      — Enum of all valid order states
  - OrderSchema      — full model returned from DB (read)
  - OrderCreateSchema — fields required to place a new order
  - OrderUpdateSchema — partial update (status, notes, payment_proof)
  - OrderSummarySchema — lightweight view for /myorders listing

Rules (from PROJECT_RULES.md — Rule 10):
  - Every user action must belong to a valid state.
  - Status transitions are enforced by the service layer, not schemas.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    """
    Valid order lifecycle states.

    Transitions (enforced by OrderService):
      pending → payment_submitted → confirmed → delivered
      Any state → cancelled
      confirmed → refunded
    """
    PENDING            = "pending"
    PAYMENT_SUBMITTED  = "payment_submitted"
    CONFIRMED          = "confirmed"
    DELIVERED          = "delivered"
    CANCELLED          = "cancelled"
    REFUNDED           = "refunded"

    @property
    def display(self) -> str:
        """Human-readable label for Telegram messages."""
        labels = {
            "pending":           "⏳ Pending",
            "payment_submitted": "💳 Payment Submitted",
            "confirmed":         "✅ Confirmed",
            "delivered":         "📦 Delivered",
            "cancelled":         "❌ Cancelled",
            "refunded":          "↩️ Refunded",
        }
        return labels.get(self.value, self.value.title())


class OrderSchema(BaseModel):
    """
    Full order record as stored in Supabase.

    This is the canonical read model for the Order domain.
    """

    id: int = Field(..., description="Auto-generated order ID.")
    user_id: int = Field(..., description="Telegram user ID of the buyer.")
    product_id: int = Field(..., description="ID of the purchased product.")
    amount: Decimal = Field(..., description="Price charged at time of order.")
    status: OrderStatus = Field(default=OrderStatus.PENDING, description="Current order status.")
    payment_proof: str | None = Field(
        None, description="Telegram file_id of payment screenshot."
    )
    notes: str | None = Field(None, description="Internal notes (admin use).")
    created_at: datetime = Field(..., description="UTC timestamp of order creation.")
    updated_at: datetime = Field(..., description="UTC timestamp of last update.")

    model_config = {"from_attributes": True}

    @property
    def amount_display(self) -> str:
        """Formatted amount string, e.g. '₹149.00'."""
        return f"₹{self.amount:.2f}"

    @property
    def status_display(self) -> str:
        """Human-readable status label."""
        return self.status.display


class OrderCreateSchema(BaseModel):
    """
    Fields required when a user places a new order.

    Amount is captured at order time (not re-read from product)
    to protect against price changes after ordering.
    """

    user_id: int = Field(..., description="Telegram user ID.")
    product_id: int = Field(..., description="ID of the product being ordered.")
    amount: Decimal = Field(..., ge=0, description="Price at time of order.")


class OrderUpdateSchema(BaseModel):
    """
    Partial update schema for order records.

    Used by admin operations and payment processing.
    """

    status: OrderStatus | None = None
    payment_proof: str | None = None
    notes: str | None = None


class OrderSummarySchema(BaseModel):
    """
    Lightweight order view for /myorders listing.

    Excludes internal fields (payment_proof, notes).
    """

    id: int
    product_id: int
    amount: Decimal
    status: OrderStatus
    created_at: datetime

    model_config = {"from_attributes": True}

    @property
    def amount_display(self) -> str:
        return f"₹{self.amount:.2f}"

    @property
    def status_display(self) -> str:
        return self.status.display
