"""
tests/unit/test_product_service.py

Unit tests for services/product_service.py

Strategy:
  - Mock ProductRepository to isolate service logic.
  - Test get_catalogue, get_product, create_product,
    activate_product, deactivate_product, update_product.
  - Verify correct repository methods are called with correct arguments.
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from schemas.product import (
    ProductCreateSchema,
    ProductListItemSchema,
    ProductSchema,
    ProductUpdateSchema,
)
from services.product_service import ProductService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_product_schema(**overrides) -> ProductSchema:
    base = {
        "id": 1,
        "name": "Test Product",
        "description": "A test product.",
        "price": Decimal("99.99"),
        "category": "general",
        "file_id": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return ProductSchema(**base)


def _make_list_item(**overrides) -> ProductListItemSchema:
    base = {
        "id": 1,
        "name": "Test Product",
        "price": Decimal("99.99"),
        "category": "general",
        "is_active": True,
    }
    base.update(overrides)
    return ProductListItemSchema(**base)


@pytest.fixture
def mock_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def product_service(mock_repo: AsyncMock) -> ProductService:
    return ProductService(mock_repo)


# ---------------------------------------------------------------------------
# get_catalogue
# ---------------------------------------------------------------------------

class TestGetCatalogue:

    async def test_returns_active_products(
        self, product_service: ProductService, mock_repo: AsyncMock
    ):
        items = [_make_list_item(id=i, name=f"Product {i}") for i in range(3)]
        mock_repo.list_active.return_value = items

        result = await product_service.get_catalogue()

        mock_repo.list_active.assert_awaited_once()
        assert len(result) == 3

    async def test_returns_empty_list_when_no_products(
        self, product_service: ProductService, mock_repo: AsyncMock
    ):
        mock_repo.list_active.return_value = []
        result = await product_service.get_catalogue()
        assert result == []


# ---------------------------------------------------------------------------
# get_product
# ---------------------------------------------------------------------------

class TestGetProduct:

    async def test_returns_product_when_found(
        self, product_service: ProductService, mock_repo: AsyncMock
    ):
        expected = _make_product_schema()
        mock_repo.get_by_id.return_value = expected

        result = await product_service.get_product(1)

        mock_repo.get_by_id.assert_awaited_once_with(1)
        assert result == expected

    async def test_returns_none_when_not_found(
        self, product_service: ProductService, mock_repo: AsyncMock
    ):
        mock_repo.get_by_id.return_value = None
        result = await product_service.get_product(999)
        assert result is None


# ---------------------------------------------------------------------------
# create_product
# ---------------------------------------------------------------------------

class TestCreateProduct:

    async def test_calls_repo_create_with_correct_data(
        self, product_service: ProductService, mock_repo: AsyncMock
    ):
        data = ProductCreateSchema(name="New Item", price=Decimal("49.99"))
        expected = _make_product_schema(name="New Item", price=Decimal("49.99"))
        mock_repo.create.return_value = expected

        result = await product_service.create_product(data)

        mock_repo.create.assert_awaited_once_with(data)
        assert result.name == "New Item"

    async def test_logs_creation_event(
        self, product_service: ProductService, mock_repo: AsyncMock
    ):
        """Ensure create_product completes without exception."""
        data = ProductCreateSchema(name="Log Test", price=Decimal("10"))
        mock_repo.create.return_value = _make_product_schema()
        await product_service.create_product(data)
        mock_repo.create.assert_awaited_once()


# ---------------------------------------------------------------------------
# activate / deactivate
# ---------------------------------------------------------------------------

class TestActivateDeactivate:

    async def test_activate_product(
        self, product_service: ProductService, mock_repo: AsyncMock
    ):
        expected = _make_product_schema(is_active=True)
        mock_repo.set_active.return_value = expected

        result = await product_service.activate_product(1)

        mock_repo.set_active.assert_awaited_once_with(1, is_active=True)
        assert result.is_active is True

    async def test_deactivate_product(
        self, product_service: ProductService, mock_repo: AsyncMock
    ):
        expected = _make_product_schema(is_active=False)
        mock_repo.set_active.return_value = expected

        result = await product_service.deactivate_product(1)

        mock_repo.set_active.assert_awaited_once_with(1, is_active=False)
        assert result.is_active is False


# ---------------------------------------------------------------------------
# update_product
# ---------------------------------------------------------------------------

class TestUpdateProduct:

    async def test_update_calls_repo_update(
        self, product_service: ProductService, mock_repo: AsyncMock
    ):
        data = ProductUpdateSchema(name="Renamed", price=Decimal("19.99"))
        expected = _make_product_schema(name="Renamed", price=Decimal("19.99"))
        mock_repo.update.return_value = expected

        result = await product_service.update_product(1, data)

        mock_repo.update.assert_awaited_once_with(1, data)
        assert result.name == "Renamed"


# ---------------------------------------------------------------------------
# get_all_products_admin
# ---------------------------------------------------------------------------

class TestGetAllProductsAdmin:

    async def test_returns_all_products_including_inactive(
        self, product_service: ProductService, mock_repo: AsyncMock
    ):
        products = [
            _make_product_schema(id=1, is_active=True),
            _make_product_schema(id=2, is_active=False),
        ]
        mock_repo.list_all.return_value = products

        result = await product_service.get_all_products_admin()

        mock_repo.list_all.assert_awaited_once()
        assert len(result) == 2
