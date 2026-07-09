"""
repositories/product_repository.py

Supabase-backed async repository for the Product domain.

Responsibilities:
  - All direct Supabase table access for the `products` table.
  - Returns validated ProductSchema / ProductListItemSchema objects.
  - Raises domain exceptions on failure.

Rules (from PROJECT_RULES.md — Rule 7):
  - Only repositories may touch the database.
  - Services call repositories; handlers call services.
  - No business logic lives here — only data access.

Usage:
    from repositories.product_repository import ProductRepository
    repo = ProductRepository(db.client)
    products = await repo.list_active()
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from supabase import AsyncClient

from core.exceptions import DatabaseConnectionError
from schemas.product import (
    ProductCreateSchema,
    ProductListItemSchema,
    ProductSchema,
    ProductUpdateSchema,
)

logger = logging.getLogger(__name__)

_TABLE = "products"


class ProductRepository:
    """
    Async CRUD repository for the `products` Supabase table.

    Args:
        client: An active Supabase AsyncClient (from db.client).
    """

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_by_id(self, product_id: int) -> ProductSchema | None:
        """
        Fetch a single product by its ID.

        Returns:
            ProductSchema if found, None otherwise.
        """
        try:
            response = (
                await self._client.table(_TABLE)
                .select("*")
                .eq("id", product_id)
                .limit(1)
                .execute()
            )
            if not response.data:
                return None
            return ProductSchema(**response.data[0])
        except Exception as exc:
            logger.error(
                "ProductRepository.get_by_id failed | product_id=%s | error=%s",
                product_id, exc,
            )
            raise DatabaseConnectionError(
                f"Failed to fetch product {product_id}: {exc}"
            ) from exc

    async def list_active(self) -> list[ProductListItemSchema]:
        """
        Return all active (publicly listed) products ordered by name.

        Returns:
            List of ProductListItemSchema (lightweight catalogue view).
        """
        try:
            response = (
                await self._client.table(_TABLE)
                .select("id, name, price, category, is_active")
                .eq("is_active", True)
                .order("name")
                .execute()
            )
            return [ProductListItemSchema(**row) for row in response.data]
        except Exception as exc:
            logger.error("ProductRepository.list_active failed | error=%s", exc)
            raise DatabaseConnectionError(
                f"Failed to list active products: {exc}"
            ) from exc

    async def list_all(self) -> list[ProductSchema]:
        """
        Return all products (active and inactive) — admin use only.

        Returns:
            List of ProductSchema ordered by created_at descending.
        """
        try:
            response = (
                await self._client.table(_TABLE)
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )
            return [ProductSchema(**row) for row in response.data]
        except Exception as exc:
            logger.error("ProductRepository.list_all failed | error=%s", exc)
            raise DatabaseConnectionError(
                f"Failed to list all products: {exc}"
            ) from exc

    async def list_by_category(self, category: str) -> list[ProductListItemSchema]:
        """
        Return active products filtered by category.

        Returns:
            List of ProductListItemSchema for the given category.
        """
        try:
            response = (
                await self._client.table(_TABLE)
                .select("id, name, price, category, is_active")
                .eq("is_active", True)
                .eq("category", category)
                .order("name")
                .execute()
            )
            return [ProductListItemSchema(**row) for row in response.data]
        except Exception as exc:
            logger.error(
                "ProductRepository.list_by_category failed | category=%s | error=%s",
                category, exc,
            )
            raise DatabaseConnectionError(
                f"Failed to list products in category '{category}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create(self, data: ProductCreateSchema) -> ProductSchema:
        """
        Insert a new product record.

        Returns:
            The newly created ProductSchema.
        """
        try:
            payload = data.model_dump()
            # Convert Decimal to float for JSON serialisation
            payload["price"] = float(payload["price"])
            response = (
                await self._client.table(_TABLE)
                .insert(payload)
                .execute()
            )
            return ProductSchema(**response.data[0])
        except Exception as exc:
            logger.error(
                "ProductRepository.create failed | name=%s | error=%s",
                data.name, exc,
            )
            raise DatabaseConnectionError(
                f"Failed to create product '{data.name}': {exc}"
            ) from exc

    async def update(self, product_id: int, data: ProductUpdateSchema) -> ProductSchema:
        """
        Partially update a product record.

        Only fields explicitly set on `data` are written.

        Returns:
            The updated ProductSchema.
        """
        try:
            payload = data.model_dump(exclude_none=True)
            if not payload:
                product = await self.get_by_id(product_id)
                if product is None:
                    raise DatabaseConnectionError(
                        f"Product {product_id} not found."
                    )
                return product

            # Convert Decimal to float if present
            if "price" in payload:
                payload["price"] = float(payload["price"])

            payload["updated_at"] = datetime.now(timezone.utc).isoformat()

            response = (
                await self._client.table(_TABLE)
                .update(payload)
                .eq("id", product_id)
                .execute()
            )
            return ProductSchema(**response.data[0])
        except DatabaseConnectionError:
            raise
        except Exception as exc:
            logger.error(
                "ProductRepository.update failed | product_id=%s | error=%s",
                product_id, exc,
            )
            raise DatabaseConnectionError(
                f"Failed to update product {product_id}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Activation toggle
    # ------------------------------------------------------------------

    async def set_active(self, product_id: int, *, is_active: bool) -> ProductSchema:
        """
        Enable or disable a product's public listing.

        Args:
            product_id: The product to modify.
            is_active:  True to list publicly, False to hide.

        Returns:
            The updated ProductSchema.
        """
        return await self.update(
            product_id,
            ProductUpdateSchema(is_active=is_active),
        )
