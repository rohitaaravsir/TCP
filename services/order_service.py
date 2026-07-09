"""
services/order_service.py

Business logic layer for the Order domain.

Responsibilities:
  - Place a new order (validate product availability, snapshot price)
  - List a user's order history
  - Fetch a single order's details
  - Cancel an order (user-initiated)
  - Update order status (admin / payment processor)
  - Submit payment proof for an order

Rules (from PROJECT_RULES.md — Rule 6 & Rule 10):
  - All business logic lives in services.
  - State transitions are validated here before writing to the DB.
  - Services call repositories; handlers call services.

Usage:
    from services.order_service import OrderService
    service = OrderService(order_repo, product_repo)
    order = await service.place_order(user_id=123, product_id=5)
"""

from __future__ import annotations

import logging
from decimal import Decimal

from core.exceptions import DatabaseConnectionError
from repositories.order_repository import OrderRepository
from repositories.product_repository import ProductRepository
from schemas.order import (
    OrderCreateSchema,
    OrderSchema,
    OrderStatus,
    OrderSummarySchema,
    OrderUpdateSchema,
)

logger = logging.getLogger(__name__)


class OrderServiceError(Exception):
    """Raised when a business rule is violated in OrderService."""


class OrderService:
    """
    Orchestrates order-related business operations.

    Args:
        order_repo:   An initialised OrderRepository instance.
        product_repo: An initialised ProductRepository instance (for
                      price snapshots and availability checks).
    """

    def __init__(
        self,
        order_repo: OrderRepository,
        product_repo: ProductRepository,
    ) -> None:
        self._orders = order_repo
        self._products = product_repo

    # ------------------------------------------------------------------
    # Place order
    # ------------------------------------------------------------------

    async def place_order(
        self, user_id: int, product_id: int
    ) -> OrderSchema:
        """
        Place a new order for a user.

        Validates:
          - Product exists and is active.
          - Price is snapshotted at order time.

        Args:
            user_id:    Telegram user ID of the buyer.
            product_id: ID of the product to order.

        Returns:
            The newly created OrderSchema with status=pending.

        Raises:
            OrderServiceError: If product is unavailable.
            DatabaseConnectionError: On Supabase failure.
        """
        product = await self._products.get_by_id(product_id)

        if product is None:
            raise OrderServiceError(
                f"Product {product_id} does not exist."
            )
        if not product.is_active:
            raise OrderServiceError(
                f"Product '{product.name}' is no longer available."
            )

        data = OrderCreateSchema(
            user_id=user_id,
            product_id=product_id,
            amount=product.price,
        )
        order = await self._orders.create(data)

        logger.info(
            "Order placed | order_id=%s | user_id=%s | product_id=%s | "
            "amount=%s | event=order.placed",
            order.id, user_id, product_id, order.amount,
        )
        return order

    # ------------------------------------------------------------------
    # User-facing reads
    # ------------------------------------------------------------------

    async def get_order(self, order_id: int) -> OrderSchema | None:
        """
        Fetch full order details by ID.

        Returns:
            OrderSchema or None if not found.
        """
        return await self._orders.get_by_id(order_id)

    async def list_user_orders(
        self, user_id: int, *, limit: int = 10
    ) -> list[OrderSummarySchema]:
        """
        Return the most recent orders for a user.

        Args:
            user_id: Telegram user ID.
            limit:   Max number of orders to return (default 10).

        Returns:
            List of OrderSummarySchema newest first.
        """
        orders = await self._orders.list_by_user(user_id, limit=limit)
        logger.info(
            "Order history fetched | user_id=%s | count=%d",
            user_id, len(orders),
        )
        return orders

    # ------------------------------------------------------------------
    # User-initiated state changes
    # ------------------------------------------------------------------

    async def cancel_order(self, order_id: int, user_id: int) -> OrderSchema:
        """
        Cancel a pending order.

        Only orders in 'pending' status can be cancelled by the user.

        Args:
            order_id: Order to cancel.
            user_id:  Must match the order's user_id (ownership check).

        Returns:
            Updated OrderSchema with status=cancelled.

        Raises:
            OrderServiceError: If order not found, not owned by user,
                               or not in a cancellable state.
        """
        order = await self._orders.get_by_id(order_id)

        if order is None:
            raise OrderServiceError(f"Order {order_id} not found.")
        if order.user_id != user_id:
            raise OrderServiceError(
                "You do not have permission to cancel this order."
            )
        if order.status not in (OrderStatus.PENDING,):
            raise OrderServiceError(
                f"Order {order_id} cannot be cancelled "
                f"(current status: {order.status_display})."
            )

        updated = await self._orders.update_status(order_id, OrderStatus.CANCELLED)
        logger.info(
            "Order cancelled | order_id=%s | user_id=%s | event=order.cancelled",
            order_id, user_id,
        )
        return updated

    async def submit_payment_proof(
        self, order_id: int, user_id: int, file_id: str
    ) -> OrderSchema:
        """
        Attach a payment screenshot and advance status to payment_submitted.

        Args:
            order_id: Order to update.
            user_id:  Must match order owner.
            file_id:  Telegram file_id of the uploaded screenshot.

        Returns:
            Updated OrderSchema with status=payment_submitted.

        Raises:
            OrderServiceError: If order not found, not owned, or wrong status.
        """
        order = await self._orders.get_by_id(order_id)

        if order is None:
            raise OrderServiceError(f"Order {order_id} not found.")
        if order.user_id != user_id:
            raise OrderServiceError(
                "You do not have permission to submit proof for this order."
            )
        if order.status != OrderStatus.PENDING:
            raise OrderServiceError(
                f"Payment proof can only be submitted for pending orders "
                f"(current status: {order.status_display})."
            )

        updated = await self._orders.update(
            order_id,
            OrderUpdateSchema(
                status=OrderStatus.PAYMENT_SUBMITTED,
                payment_proof=file_id,
            ),
        )
        logger.info(
            "Payment proof submitted | order_id=%s | user_id=%s | "
            "event=order.payment_submitted",
            order_id, user_id,
        )
        return updated

    # ------------------------------------------------------------------
    # Admin-only operations
    # ------------------------------------------------------------------

    async def confirm_order(self, order_id: int) -> OrderSchema:
        """
        Confirm a payment-submitted order (admin).

        Returns:
            Updated OrderSchema with status=confirmed.
        """
        updated = await self._orders.update_status(order_id, OrderStatus.CONFIRMED)
        logger.info(
            "Order confirmed | order_id=%s | event=order.confirmed", order_id
        )
        return updated

    async def mark_delivered(self, order_id: int) -> OrderSchema:
        """
        Mark a confirmed order as delivered (admin).

        Returns:
            Updated OrderSchema with status=delivered.
        """
        updated = await self._orders.update_status(order_id, OrderStatus.DELIVERED)
        logger.info(
            "Order delivered | order_id=%s | event=order.delivered", order_id
        )
        return updated

    async def list_pending_payments(self) -> list[OrderSchema]:
        """
        Return all orders awaiting payment review (admin queue).

        Returns:
            List of OrderSchema with status=payment_submitted.
        """
        return await self._orders.list_by_status(OrderStatus.PAYMENT_SUBMITTED)
