"""
services/product_service.py

Business logic layer for the Product domain.

Responsibilities:
  - List active products for the catalogue (public)
  - Fetch a single product's full details
  - Create new products (admin)
  - Activate / deactivate products (admin)
  - Update product fields (admin)

Rules (from PROJECT_RULES.md — Rule 6):
  - All business logic lives in services.
  - Services call repositories; they never touch Supabase directly.
  - Handlers call services; they never call repositories.

Usage:
    from services.product_service import ProductService
    service = ProductService(product_repo)
    products = await service.get_catalogue()
"""

from __future__ import annotations

import logging

from core.exceptions import DatabaseConnectionError
from repositories.product_repository import ProductRepository
from schemas.product import (
    ProductCreateSchema,
    ProductListItemSchema,
    ProductSchema,
    ProductUpdateSchema,
)

logger = logging.getLogger(__name__)


class ProductService:
    """
    Orchestrates product-related business operations.

    Args:
        repository: An initialised ProductRepository instance.
    """

    def __init__(self, repository: ProductRepository) -> None:
        self._repo = repository

    # ------------------------------------------------------------------
    # Public catalogue (user-facing)
    # ------------------------------------------------------------------

    async def get_catalogue(self) -> list[ProductListItemSchema]:
        """
        Return all active products for the public catalogue.

        Returns:
            List of lightweight ProductListItemSchema, ordered by name.
            Returns an empty list if no products are active.
        """
        products = await self._repo.list_active()
        logger.info(
            "Catalogue fetched | product_count=%d | event=product.catalogue_fetched",
            len(products),
        )
        return products

    async def get_catalogue_by_category(
        self, category: str
    ) -> list[ProductListItemSchema]:
        """
        Return active products filtered by category.

        Args:
            category: Category tag to filter by.

        Returns:
            Filtered list of ProductListItemSchema.
        """
        return await self._repo.list_by_category(category)

    async def get_product(self, product_id: int) -> ProductSchema | None:
        """
        Fetch full product details by ID.

        Returns None if the product does not exist.

        Args:
            product_id: The numeric product ID.

        Returns:
            ProductSchema or None.
        """
        return await self._repo.get_by_id(product_id)

    # ------------------------------------------------------------------
    # Admin operations
    # ------------------------------------------------------------------

    async def create_product(self, data: ProductCreateSchema) -> ProductSchema:
        """
        Create a new product.

        Args:
            data: Validated ProductCreateSchema from the admin handler.

        Returns:
            The newly created ProductSchema.

        Raises:
            DatabaseConnectionError: On Supabase failure.
        """
        product = await self._repo.create(data)
        logger.info(
            "Product created | product_id=%s | name=%s | price=%s | event=product.created",
            product.id,
            product.name,
            product.price,
        )
        return product

    async def update_product(
        self, product_id: int, data: ProductUpdateSchema
    ) -> ProductSchema:
        """
        Partially update a product's fields.

        Args:
            product_id: ID of the product to update.
            data: Partial ProductUpdateSchema (only set fields are written).

        Returns:
            The updated ProductSchema.

        Raises:
            DatabaseConnectionError: On Supabase failure.
        """
        product = await self._repo.update(product_id, data)
        logger.info(
            "Product updated | product_id=%s | event=product.updated",
            product_id,
        )
        return product

    async def activate_product(self, product_id: int) -> ProductSchema:
        """
        Make a product publicly visible in the catalogue.

        Args:
            product_id: The product to activate.

        Returns:
            Updated ProductSchema with is_active=True.
        """
        product = await self._repo.set_active(product_id, is_active=True)
        logger.info(
            "Product activated | product_id=%s | event=product.activated",
            product_id,
        )
        return product

    async def deactivate_product(self, product_id: int) -> ProductSchema:
        """
        Hide a product from the public catalogue.

        Args:
            product_id: The product to deactivate.

        Returns:
            Updated ProductSchema with is_active=False.
        """
        product = await self._repo.set_active(product_id, is_active=False)
        logger.info(
            "Product deactivated | product_id=%s | event=product.deactivated",
            product_id,
        )
        return product

    async def get_all_products_admin(self) -> list[ProductSchema]:
        """
        Return all products including inactive ones — admin only.

        Returns:
            List of full ProductSchema ordered by newest first.
        """
        return await self._repo.list_all()
