"""
schemas package

Pydantic request and response models.

Purpose:
  - Validate data entering services (request schemas)
  - Shape data leaving services (response schemas)
  - Provide consistent data contracts across all layers

Future schemas:
  - UserSchema          — user profile model
  - ProductSchema       — product listing model
  - OrderSchema         — order data model
  - PaymentSchema       — payment submission model
  - OCRResultSchema     — OCR analysis output
  - SupportTicketSchema — support ticket model
  - BroadcastSchema     — broadcast message model
"""
from schemas.user import UserSchema, UserCreateSchema, UserUpdateSchema
from schemas.product import ProductSchema, ProductCreateSchema, ProductUpdateSchema, ProductListItemSchema
from schemas.order import OrderSchema, OrderCreateSchema, OrderUpdateSchema, OrderSummarySchema, OrderStatus
from schemas.support import (
    TicketStatus,
    SupportMessageSchema,
    SupportMessageCreateSchema,
    SupportTicketSchema,
    SupportTicketCreateSchema,
    SupportTicketUpdateSchema,
)

__all__ = [
    "UserSchema",
    "UserCreateSchema",
    "UserUpdateSchema",
    "ProductSchema",
    "ProductCreateSchema",
    "ProductUpdateSchema",
    "ProductListItemSchema",
    "OrderSchema",
    "OrderCreateSchema",
    "OrderUpdateSchema",
    "OrderSummarySchema",
    "OrderStatus",
    "TicketStatus",
    "SupportMessageSchema",
    "SupportMessageCreateSchema",
    "SupportTicketSchema",
    "SupportTicketCreateSchema",
    "SupportTicketUpdateSchema",
]
