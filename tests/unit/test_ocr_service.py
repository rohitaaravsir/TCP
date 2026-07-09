"""
tests/unit/test_ocr_service.py

Unit tests for services/ocr_service.py
"""

from decimal import Decimal
import pytest

from services.ocr_service import OCRService


@pytest.mark.asyncio
async def test_ocr_service_always_returns_low_confidence_and_requires_review():
    """OCRService (Sprint 4 placeholder) should fail verification open to admin review."""
    service = OCRService()
    result = await service.verify_payment(file_id="test_photo_id", expected_amount=Decimal("99.99"))

    assert result.confidence == 0.0
    assert result.requires_review is True
    assert result.detected_amount is None
    assert result.is_auto_approved is False
    assert "placeholder" in result.notes.lower()
