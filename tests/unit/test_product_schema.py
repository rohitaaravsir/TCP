"""
tests/unit/test_product_schema.py

Unit tests for schemas/product.py

Validates:
  - ProductSchema accepts valid data
  - ProductSchema rejects missing required fields
  - ProductCreateSchema enforces constraints (name, price >= 0)
  - ProductUpdateSchema allows all-None (partial update)
  - ProductListItemSchema works as lightweight catalogue view
  - price_display property formats correctly
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from schemas.product import (
    ProductCreateSchema,
    ProductListItemSchema,
    ProductSchema,
    ProductUpdateSchema,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_product_data(**overrides) -> dict:
    """Return a minimal valid dict for ProductSchema."""
    base = {
        "id": 1,
        "name": "Test Product",
        "description": "A great product.",
        "price": Decimal("99.99"),
        "category": "general",
        "file_id": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# ProductSchema
# ---------------------------------------------------------------------------

class TestProductSchema:

    def test_valid_product_creates_successfully(self):
        p = ProductSchema(**_make_product_data())
        assert p.id == 1
        assert p.name == "Test Product"
        assert p.price == Decimal("99.99")
        assert p.is_active is True

    def test_description_can_be_none(self):
        p = ProductSchema(**_make_product_data(description=None))
        assert p.description is None

    def test_file_id_can_be_none(self):
        p = ProductSchema(**_make_product_data(file_id=None))
        assert p.file_id is None

    def test_missing_name_raises(self):
        data = _make_product_data()
        del data["name"]
        with pytest.raises(ValidationError):
            ProductSchema(**data)

    def test_missing_price_raises(self):
        data = _make_product_data()
        del data["price"]
        with pytest.raises(ValidationError):
            ProductSchema(**data)

    def test_price_display_formats_correctly(self):
        p = ProductSchema(**_make_product_data(price=Decimal("149.00")))
        assert p.price_display == "₹149.00"

    def test_price_display_zero(self):
        p = ProductSchema(**_make_product_data(price=Decimal("0.00")))
        assert p.price_display == "₹0.00"


# ---------------------------------------------------------------------------
# ProductCreateSchema
# ---------------------------------------------------------------------------

class TestProductCreateSchema:

    def test_valid_create_schema(self):
        schema = ProductCreateSchema(name="Widget", price=Decimal("49.99"))
        assert schema.name == "Widget"
        assert schema.category == "general"

    def test_zero_price_is_valid(self):
        """Free products (price=0) must be allowed."""
        schema = ProductCreateSchema(name="Free Item", price=Decimal("0"))
        assert schema.price == Decimal("0")

    def test_negative_price_raises(self):
        with pytest.raises(ValidationError):
            ProductCreateSchema(name="Bad", price=Decimal("-1"))

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            ProductCreateSchema(name="", price=Decimal("10"))

    def test_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            ProductCreateSchema(name="x" * 201, price=Decimal("10"))

    def test_description_is_optional(self):
        schema = ProductCreateSchema(name="Minimal", price=Decimal("5"))
        assert schema.description is None

    def test_category_defaults_to_general(self):
        schema = ProductCreateSchema(name="Item", price=Decimal("10"))
        assert schema.category == "general"

    def test_missing_price_raises(self):
        with pytest.raises(ValidationError):
            ProductCreateSchema(name="No Price")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# ProductUpdateSchema
# ---------------------------------------------------------------------------

class TestProductUpdateSchema:

    def test_all_none_is_valid(self):
        """Empty update (all None) is a valid no-op."""
        schema = ProductUpdateSchema()
        assert schema.name is None
        assert schema.is_active is None

    def test_partial_update_excludes_none_fields(self):
        schema = ProductUpdateSchema(is_active=False)
        data = schema.model_dump(exclude_none=True)
        assert data == {"is_active": False}
        assert "name" not in data

    def test_negative_price_raises(self):
        with pytest.raises(ValidationError):
            ProductUpdateSchema(price=Decimal("-5"))

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            ProductUpdateSchema(name="")


# ---------------------------------------------------------------------------
# ProductListItemSchema
# ---------------------------------------------------------------------------

class TestProductListItemSchema:

    def test_valid_list_item(self):
        item = ProductListItemSchema(
            id=2,
            name="List Item",
            price=Decimal("29.99"),
            category="digital",
            is_active=True,
        )
        assert item.id == 2
        assert item.price_display == "₹29.99"

    def test_inactive_item_is_valid(self):
        item = ProductListItemSchema(
            id=3,
            name="Hidden",
            price=Decimal("0"),
            category="general",
            is_active=False,
        )
        assert item.is_active is False
