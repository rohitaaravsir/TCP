"""
services/ocr_service.py

OCR (Optical Character Recognition) service for payment screenshot verification.

Current Status: PLACEHOLDER — confidence scoring framework only.
  Real OCR integration (EasyOCR + Template Parser) is scheduled for Sprint 5.

Philosophy (from PROJECT_CHARTER.md — OCR Philosophy):
  - OCR must NEVER blindly approve payments.
  - Confidence scoring is mandatory.
  - Manual review must always remain available.
  - If confidence < threshold → escalate to admin queue.

Current behaviour:
  - Returns a fixed LOW confidence score for all images.
  - All payment proofs are routed to admin review (manual verification).
  - This is the safe default — no auto-approvals until OCR is implemented.

Usage:
    from services.ocr_service import OCRService
    result = await ocr_service.verify_payment(file_id, expected_amount)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)

# Minimum confidence score required for automatic approval
# Any score below this threshold requires manual admin review
OCR_AUTO_APPROVE_THRESHOLD = 0.90


@dataclass
class OCRResult:
    """
    Result of an OCR payment verification attempt.

    Attributes:
        confidence:       Score from 0.0 (no match) to 1.0 (perfect match).
        requires_review:  True if confidence < threshold (always manual review).
        detected_amount:  Amount parsed from screenshot (None if undetected).
        raw_text:         Raw text extracted from the image (empty until real OCR).
        notes:            Human-readable explanation of the result.
    """
    confidence: float
    requires_review: bool
    detected_amount: Decimal | None
    raw_text: str
    notes: str

    @property
    def is_auto_approved(self) -> bool:
        """True only if confidence meets threshold AND review is not needed."""
        return self.confidence >= OCR_AUTO_APPROVE_THRESHOLD and not self.requires_review


class OCRService:
    """
    Payment screenshot verification service.

    Sprint 4: Placeholder implementation — all payments routed to admin review.
    Sprint 5: Will integrate EasyOCR + template-based confidence scoring.
    """

    async def verify_payment(
        self,
        file_id: str,
        expected_amount: Decimal,
    ) -> OCRResult:
        """
        Analyse a payment screenshot and return a confidence score.

        Args:
            file_id:         Telegram file_id of the uploaded screenshot.
            expected_amount: The order amount to verify against.

        Returns:
            OCRResult with confidence score and review requirement.

        Note:
            Sprint 4 placeholder — always returns low confidence and
            requires_review=True. Real OCR will be implemented in Sprint 5.
        """
        logger.info(
            "OCR verification requested | file_id=%s | expected_amount=%s | "
            "event=ocr.requested",
            file_id,
            expected_amount,
        )

        # TODO (Sprint 5): Implement EasyOCR pipeline:
        # 1. Download image from Telegram using file_id
        # 2. Run EasyOCR text extraction
        # 3. Apply template parser (UPI, bank transfer formats)
        # 4. Score: receiver name, amount, date, time
        # 5. Secondary: UPI ID, UTR, transaction reference
        # 6. Return confidence score and extracted fields

        result = OCRResult(
            confidence=0.0,
            requires_review=True,
            detected_amount=None,
            raw_text="",
            notes=(
                "OCR not yet implemented (Sprint 4 placeholder). "
                "Payment routed to admin review queue."
            ),
        )

        logger.info(
            "OCR result | confidence=%.2f | requires_review=%s | "
            "event=ocr.completed",
            result.confidence,
            result.requires_review,
        )
        return result
