"""
repositories package

All database access operations belong here (PROJECT_RULES.md — Rule 7).

The Repository Pattern:
  - Each repository is responsible for one domain entity.
  - Repositories use db.client from core.database.
  - Services call repositories — never call db.client directly.
  - Handlers never access repositories directly.

Future repositories:
  - UserRepository     — CRUD for users table
  - ProductRepository  — CRUD for products table
  - OrderRepository    — CRUD for orders table
  - PaymentRepository  — CRUD for payments table
  - SupportRepository  — CRUD for support_tickets table
  - AuditRepository    — append-only audit log writes
"""
from repositories.user_repository import UserRepository
from repositories.product_repository import ProductRepository
from repositories.order_repository import OrderRepository
from repositories.support_repository import SupportRepository

__all__ = [
    "UserRepository",
    "ProductRepository",
    "OrderRepository",
    "SupportRepository",
]
