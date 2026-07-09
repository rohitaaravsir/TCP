"""
interfaces package

Abstract base classes (interfaces) for pluggable implementations.

Purpose (PROJECT_CHARTER.md — Future Compatibility):
  - Define contracts that multiple implementations can satisfy.
  - Allow swapping providers without changing service logic.
  - Enable easy mocking in tests.

Future interfaces:
  - AIProviderInterface    — contract for Groq, Gemini, OpenRouter
  - OCRInterface           — contract for EasyOCR and future OCR engines
  - StorageInterface       — contract for Supabase Storage and local FS
  - PaymentProviderInterface — contract for future payment gateways
  - NotificationInterface  — contract for Telegram, email, webhook alerts
"""
from interfaces.ai_provider import AIProviderInterface

__all__ = ["AIProviderInterface"]
