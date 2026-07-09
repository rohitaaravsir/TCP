"""
schemas/product.py

Pydantic schemas for the Product domain.

Schemas:
  - ProductSchema       — full model returned from DB (read)
  - ProductCreateSchema — fields required to create a product (admin)
  - ProductUpdateSchema — optional fields for partial updates (admin)
  - ProductListItemSchema — lightweight view for catalog listings

Rules (from PROJECT_RULES.md — Rule 18):
  - Schemas are reusable, testable, and decoupled from Telegram/DB concerns.
  - All data must be validated before entering the service layer.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ProductSchema(BaseModel):
    """
    Full product record as stored in Supabase.

    This is the canonical read model for the Product domain.
    """

    id: int = Field(..., description="Auto-generated product ID.")
    name: str = Field(..., description="Product display name.")
    description: str | None = Field(None, description="Optional product description.")
    price: Decimal = Field(..., description="Price in the shop currency.")
    category: str = Field(default="general", description="Product category tag.")
    file_id: str | None = Field(
        None, description="Telegram file_id for digital delivery (set after upload)."
    )
    is_active: bool = Field(default=True, description="Whether the product is listed publicly.")
    created_at: datetime = Field(..., description="UTC timestamp of creation.")
    updated_at: datetime = Field(..., description="UTC timestamp of last update.")

    model_config = {"from_attributes": True}

    @property
    def price_display(self) -> str:
        """Formatted price string, e.g. '₹149.00'."""
        return f"₹{self.price:.2f}"


class ProductCreateSchema(BaseModel):
    """
    Fields required (or allowed) when an admin creates a new product.
    """

    name: str = Field(..., min_length=1, max_length=200, description="Product name.")
    description: str | None = Field(None, max_length=2000, description="Optional description.")
    price: Decimal = Field(..., ge=0, description="Price (0 for free products).")
    category: str = Field(default="general", max_length=100, description="Category tag.")
    file_id: str | None = Field(None, description="Telegram file_id (optional at creation).")


class ProductUpdateSchema(BaseModel):
    """
    Partial update schema — all fields are optional.

    Only provided fields will be written to the database.
    """

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    price: Decimal | None = Field(None, ge=0)
    category: str | None = Field(None, max_length=100)
    file_id: str | None = None
    is_active: bool | None = None


class ProductListItemSchema(BaseModel):
    """
    Lightweight product view for catalog listings.

    Only exposes fields needed for a catalogue entry — avoids
    sending unnecessary data (e.g., internal file_id) to handlers.
    """

    id: int
    name: str
    price: Decimal
    category: str
    is_active: bool

    model_config = {"from_attributes": True}

    @property
    def price_display(self) -> str:
        return f"₹{self.price:.2f}"
