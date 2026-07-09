"""
services package

All business logic belongs here (PROJECT_RULES.md — Rule 6).

Every service:
  - Operates on domain models
  - May call repositories for data access
  - Never directly handles Telegram updates
  - Must be fully testable without a running bot

Future services:
  - UserService     — user registration, lookup, ban management
  - ProductService  — product catalogue, availability
  - OrderService    — order lifecycle management
  - PaymentService  — payment verification orchestration
  - OCRService      — payment screenshot processing
  - AIService       — AI provider routing and response generation
  - SupportService  — support ticket lifecycle
  - BroadcastService — broadcast message management
"""
from services.user_service import UserService
from services.product_service import ProductService
from services.order_service import OrderService
from services.ocr_service import OCRService
from services.ai_provider_service import GeminiProvider
from services.support_service import SupportService

__all__ = [
    "UserService",
    "ProductService",
    "OrderService",
    "OCRService",
    "GeminiProvider",
    "SupportService",
]
