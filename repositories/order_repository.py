"""
repositories/order_repository.py

Supabase-backed async repository for the Order domain.

Responsibilities:
  - All direct Supabase table access for the `orders` table.
  - Returns validated OrderSchema / OrderSummarySchema objects.
  - Raises domain exceptions on failure.

Rules (from PROJECT_RULES.md — Rule 7):
  - Only repositories may touch the database.
  - Services call repositories; handlers call services.
  - No business logic lives here — only data access.

Usage:
    from repositories.order_repository import OrderRepository
    repo = OrderRepository(db.client)
    order = await repo.create(data)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from supabase import AsyncClient

from core.exceptions import DatabaseConnectionError
from schemas.order import (
    OrderCreateSchema,
    OrderSchema,
    OrderStatus,
    OrderSummarySchema,
    OrderUpdateSchema,
)

logger = logging.getLogger(__name__)

_TABLE = "orders"


class OrderRepository:
    """
    Async CRUD repository for the `orders` Supabase table.

    Args:
        client: An active Supabase AsyncClient (from db.client).
    """

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_by_id(self, order_id: int) -> OrderSchema | None:
        """
        Fetch a single order by its ID.

        Returns:
            OrderSchema if found, None otherwise.
        """
        try:
            response = (
                await self._client.table(_TABLE)
                .select("*")
                .eq("id", order_id)
                .limit(1)
                .execute()
            )
            if not response.data:
                return None
            return OrderSchema(**response.data[0])
        except Exception as exc:
            logger.error(
                "OrderRepository.get_by_id failed | order_id=%s | error=%s",
                order_id, exc,
            )
            raise DatabaseConnectionError(
                f"Failed to fetch order {order_id}: {exc}"
            ) from exc

    async def list_by_user(
        self, user_id: int, *, limit: int = 10
    ) -> list[OrderSummarySchema]:
        """
        Return the most recent orders for a given user.

        Args:
            user_id: Telegram user ID.
            limit:   Maximum number of orders to return (default 10).

        Returns:
            List of OrderSummarySchema ordered by newest first.
        """
        try:
            response = (
                await self._client.table(_TABLE)
                .select("id, product_id, amount, status, created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return [OrderSummarySchema(**row) for row in response.data]
        except Exception as exc:
            logger.error(
                "OrderRepository.list_by_user failed | user_id=%s | error=%s",
                user_id, exc,
            )
            raise DatabaseConnectionError(
                f"Failed to list orders for user {user_id}: {exc}"
            ) from exc

    async def list_by_status(self, status: OrderStatus) -> list[OrderSchema]:
        """
        Return all orders with a given status — admin use only.

        Returns:
            List of OrderSchema ordered by created_at ascending.
        """
        try:
            response = (
                await self._client.table(_TABLE)
                .select("*")
                .eq("status", status.value)
                .order("created_at")
                .execute()
            )
            return [OrderSchema(**row) for row in response.data]
        except Exception as exc:
            logger.error(
                "OrderRepository.list_by_status failed | status=%s | error=%s",
                status, exc,
            )
            raise DatabaseConnectionError(
                f"Failed to list orders by status '{status}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create(self, data: OrderCreateSchema) -> OrderSchema:
        """
        Insert a new order with status='pending'.

        Returns:
            The newly created OrderSchema.
        """
        try:
            payload = data.model_dump()
            payload["amount"] = float(payload["amount"])
            response = (
                await self._client.table(_TABLE)
                .insert(payload)
                .execute()
            )
            return OrderSchema(**response.data[0])
        except Exception as exc:
            logger.error(
                "OrderRepository.create failed | user_id=%s | product_id=%s | error=%s",
                data.user_id, data.product_id, exc,
            )
            raise DatabaseConnectionError(
                f"Failed to create order for user {data.user_id}: {exc}"
            ) from exc

    async def update(self, order_id: int, data: OrderUpdateSchema) -> OrderSchema:
        """
        Partially update an order record.

        Returns:
            The updated OrderSchema.
        """
        try:
            payload = data.model_dump(exclude_none=True)
            if not payload:
                order = await self.get_by_id(order_id)
                if order is None:
                    raise DatabaseConnectionError(f"Order {order_id} not found.")
                return order

            # Serialise enum value
            if "status" in payload:
                payload["status"] = payload["status"].value

            payload["updated_at"] = datetime.now(timezone.utc).isoformat()

            response = (
                await self._client.table(_TABLE)
                .update(payload)
                .eq("id", order_id)
                .execute()
            )
            return OrderSchema(**response.data[0])
        except DatabaseConnectionError:
            raise
        except Exception as exc:
            logger.error(
                "OrderRepository.update failed | order_id=%s | error=%s",
                order_id, exc,
            )
            raise DatabaseConnectionError(
                f"Failed to update order {order_id}: {exc}"
            ) from exc

    async def update_status(
        self, order_id: int, status: OrderStatus
    ) -> OrderSchema:
        """
        Convenience method to update only the order status.

        Returns:
            The updated OrderSchema.
        """
        return await self.update(order_id, OrderUpdateSchema(status=status))
