"""
services/ocr_service.py

OCR (Optical Character Recognition) service for payment screenshot verification.

Architecture:
  Sprint 4: Placeholder — all payments routed to manual review.
  Sprint 7: Real implementation — EasyOCR + weighted confidence scoring.

Weighted Scoring (from OCR Philosophy in PROJECT_CHARTER.md):
  ┌────────────────────┬────────┬───────────┐
  │ Check              │ Weight │ Type      │
  ├────────────────────┼────────┼───────────┤
  │ Receiver Name      │  40%   │ Mandatory │
  │ Amount             │  30%   │ Mandatory │
  │ Date (today)       │  10%   │ Mandatory │
  │ Time freshness     │   5%   │ Soft      │
  │ UPI ID detected    │   5%   │ Soft      │
  │ UTR available      │   5%   │ Bonus     │
  │ App detected       │   5%   │ Bonus     │
  └────────────────────┴────────┴───────────┘

Rules:
  - Any Mandatory check fails → requires_review = True always.
  - Score ≥ 90% AND no mandatory fail → auto_approved = True.
  - Screenshot older than 2 hours → hard block, force manual review.

Usage:
    from services.ocr_service import OCRService
    result = await ocr_service.verify_payment(
        bot, file_id, expected_amount, order_created_at
    )
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────
OCR_AUTO_APPROVE_THRESHOLD = 0.90   # 90% → auto approve
OCR_NEAR_MISS_THRESHOLD = 0.85      # 85-89% → suggest full receipt
OCR_TIME_FRESHNESS_MINUTES = 30     # ≤30 min → full 5% bonus
OCR_TIME_HARD_BLOCK_HOURS = 2       # >2 hr → mandatory manual review

# ── Template Directory ────────────────────────────────────────────────────────
_TEMPLATES_DIR = Path(__file__).parent.parent / "data" / "ocr_templates"


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    """Represents one individual check in the scoring pipeline."""
    name: str
    passed: bool
    weight: float           # 0.0 – 1.0
    is_mandatory: bool
    detail: str = ""        # Human-readable reason


@dataclass
class OCRResult:
    """
    Full result of an OCR payment verification attempt.

    Attributes:
        confidence:        Score from 0.0 to 1.0.
        requires_review:   True if any mandatory check failed or score < threshold.
        is_near_miss:      True if score is 85-89% (ask user for full receipt).
        auto_approved:     True only if score ≥ threshold AND no mandatory fail.
        detected_amount:   Amount parsed from screenshot (None if undetected).
        detected_app:      Payment app name detected (e.g. 'GPay', 'PhonePe').
        utr_number:        Extracted UTR/Transaction ID (None if not found).
        raw_text:          Full text extracted by OCR.
        checks:            Detailed list of every individual check result.
        notes:             Human-readable summary for admin display.
    """
    confidence: float
    requires_review: bool
    is_near_miss: bool
    detected_amount: Decimal | None
    detected_app: str
    utr_number: str | None
    raw_text: str
    checks: list[CheckResult] = field(default_factory=list)
    notes: str = ""

    @property
    def auto_approved(self) -> bool:
        """True only if confidence meets threshold AND no mandatory fail."""
        return (
            self.confidence >= OCR_AUTO_APPROVE_THRESHOLD
            and not self.requires_review
        )

    @property
    def confidence_percent(self) -> int:
        """Confidence as integer percentage for display."""
        return int(self.confidence * 100)


# ── Template Loader ───────────────────────────────────────────────────────────

def _load_templates() -> dict[str, dict]:
    """Load all JSON app templates from data/ocr_templates/."""
    templates = {}
    if not _TEMPLATES_DIR.exists():
        logger.warning("OCR templates directory not found: %s", _TEMPLATES_DIR)
        return templates
    for path in _TEMPLATES_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            templates[path.stem] = data
        except Exception as exc:
            logger.warning("Failed to load OCR template %s: %s", path.name, exc)
    return templates


_APP_TEMPLATES: dict[str, dict] = _load_templates()


# ── OCR Service ───────────────────────────────────────────────────────────────

class OCRService:
    """
    Payment screenshot verification service.

    Sprint 7: Real implementation using EasyOCR + regex + weighted scoring.

    Note on EasyOCR import:
        EasyOCR is imported lazily inside verify_payment() so that the rest
        of the application starts normally even if the package is not yet
        installed (e.g., in the test environment or on a machine without a
        GPU).  If EasyOCR is missing, the service falls back gracefully to
        manual review with a clear log message.
    """

    def __init__(self, receiver_name: str, upi_id: str | None = None) -> None:
        """
        Args:
            receiver_name: Your merchant/bank account name to match in receipts.
            upi_id:        Your UPI ID (optional, used for soft UPI check).
        """
        self._receiver_name = receiver_name.lower().strip()
        self._upi_id = (upi_id or "").lower().strip()
        self._reader = None  # lazy-loaded EasyOCR reader

    # ── Public API ────────────────────────────────────────────────────────────

    async def verify_payment(
        self,
        image_bytes: bytes,
        expected_amount: Decimal,
        order_created_at: datetime | None = None,
    ) -> OCRResult:
        """
        Analyse a payment screenshot and return a weighted confidence score.

        Args:
            image_bytes:       Raw bytes of the uploaded image.
            expected_amount:   The order amount we expect to see (e.g. Decimal('20')).
            order_created_at:  When the order was placed (UTC). Used for time
                               freshness check. Pass None to skip.

        Returns:
            OCRResult with full scoring breakdown and admin-friendly notes.
        """
        logger.info(
            "OCR verification started | expected_amount=%s | event=ocr.started",
            expected_amount,
        )

        # ── Step 1: Extract text ──────────────────────────────────────────────
        raw_text = await self._extract_text(image_bytes)
        if not raw_text:
            return self._fallback_result(
                "OCR could not extract any text from the image."
            )

        normalized = raw_text.lower()
        logger.info("OCR raw text extracted:\n%s\n-------------------", raw_text)
        logger.debug("OCR raw text extracted | chars=%d", len(raw_text))

        # ── Step 2: Detect app ────────────────────────────────────────────────
        detected_app, template = self._detect_app(normalized)

        # ── Step 3: Run all checks ────────────────────────────────────────────
        checks: list[CheckResult] = []
        mandatory_failed = False

        # 3a. Receiver Name (40%) — Mandatory
        name_check = self._check_receiver_name(normalized)
        checks.append(name_check)
        if not name_check.passed:
            mandatory_failed = True

        # 3b. Amount (30%) — Mandatory
        detected_amount, amount_check = self._check_amount(normalized, expected_amount)
        checks.append(amount_check)
        if not amount_check.passed:
            mandatory_failed = True

        # 3c. Date — today's date (10%) — Mandatory
        date_check = self._check_date(normalized)
        checks.append(date_check)
        if not date_check.passed:
            mandatory_failed = True

        # 3d. Time freshness (5%) — Soft
        time_check = self._check_time_freshness(normalized, order_created_at)
        checks.append(time_check)

        # Hard block: screenshot older than 2 hours relative to order creation
        hard_block = self._is_hard_blocked(normalized, order_created_at)

        # 3e. UPI ID (5%) — Soft
        upi_check = self._check_upi_id(normalized)
        checks.append(upi_check)

        # 3f. UTR available (5%) — Bonus
        utr_number, utr_check = self._extract_utr(raw_text)
        checks.append(utr_check)

        # 3g. App detected (5%) — Bonus
        app_check = CheckResult(
            name="App Detected",
            passed=detected_app != "Unknown",
            weight=0.05,
            is_mandatory=False,
            detail=f"Detected: {detected_app}",
        )
        checks.append(app_check)

        # ── Step 4: Calculate confidence score ────────────────────────────────
        confidence = sum(
            c.weight for c in checks if c.passed
        )
        confidence = min(confidence, 1.0)

        # Hard block overrides everything
        requires_review = mandatory_failed or hard_block or (
            confidence < OCR_AUTO_APPROVE_THRESHOLD
        )
        is_near_miss = (
            not mandatory_failed
            and not hard_block
            and OCR_NEAR_MISS_THRESHOLD <= confidence < OCR_AUTO_APPROVE_THRESHOLD
        )

        # ── Step 5: Build notes ───────────────────────────────────────────────
        notes = self._build_notes(
            checks, confidence, detected_app, mandatory_failed, hard_block, is_near_miss
        )

        logger.info(
            "OCR result | app=%s | confidence=%.0f%% | mandatory_fail=%s | "
            "requires_review=%s | utr=%s | event=ocr.completed",
            detected_app, confidence * 100, mandatory_failed, requires_review, utr_number,
        )

        return OCRResult(
            confidence=confidence,
            requires_review=requires_review,
            is_near_miss=is_near_miss,
            detected_amount=detected_amount,
            detected_app=detected_app,
            utr_number=utr_number,
            raw_text=raw_text,
            checks=checks,
            notes=notes,
        )

    # ── Text Extraction ───────────────────────────────────────────────────────

    async def _extract_text(self, image_bytes: bytes) -> str:
        """
        Use EasyOCR to extract all text from the image.

        Falls back to empty string if EasyOCR is not installed.
        """
        try:
            import easyocr  # lazy import — not required for test suite
            import numpy as np
            from PIL import Image
            import io

            if self._reader is None:
                logger.info("Initialising EasyOCR reader (first-time, may take ~10s)")
                self._reader = easyocr.Reader(["en"], gpu=False, verbose=False)

            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_array = np.array(img)
            results = self._reader.readtext(img_array, detail=0, paragraph=True)
            return "\n".join(results)

        except ImportError:
            logger.warning(
                "EasyOCR not installed — OCR text extraction unavailable. "
                "Install with: pip install easyocr pillow"
            )
            return ""
        except Exception as exc:
            logger.error("EasyOCR extraction failed: %s", exc)
            return ""

    # ── App Detection ─────────────────────────────────────────────────────────

    def _detect_app(self, text_lower: str) -> tuple[str, dict]:
        """Identify which payment app the screenshot is from."""
        # Priority order: more specific apps first
        priority = ["phonepe", "gpay", "paytm", "bhim"]
        for key in priority:
            tmpl = _APP_TEMPLATES.get(key, {})
            keywords = [kw.lower() for kw in tmpl.get("app_keywords", [])]
            if any(kw in text_lower for kw in keywords):
                return tmpl.get("app_name", key.title()), tmpl

        # Fallback to unknown
        unknown = _APP_TEMPLATES.get("unknown", {})
        return "Unknown", unknown

    # ── Individual Checks ─────────────────────────────────────────────────────

    def _check_receiver_name(self, text_lower: str) -> CheckResult:
        """40% — Mandatory: receiver name must appear in screenshot."""
        if not self._receiver_name:
            return CheckResult(
                name="Receiver Name",
                passed=False,
                weight=0.40,
                is_mandatory=True,
                detail="Receiver name not configured in settings.",
            )

        # Allow partial match (first word of name is enough)
        name_parts = self._receiver_name.split()
        matched = any(part in text_lower for part in name_parts if len(part) > 2)

        return CheckResult(
            name="Receiver Name",
            passed=matched,
            weight=0.40,
            is_mandatory=True,
            detail=(
                f"Matched '{self._receiver_name}' in screenshot"
                if matched
                else f"Name '{self._receiver_name}' NOT found in screenshot"
            ),
        )

    @staticmethod
    def _strip_rupee_misread(text: str) -> str:
        """
        Pre-process raw OCR text to normalise ₹ symbol misreads.

        EasyOCR commonly reads ₹ as:  7  8  1  l  t  i  /  |
        e.g.  ₹20  ->  720  or  820  or  120
              ₹150 ->  7150  8150  1150

        Strategy: if we see a single 7/8 immediately followed by 2+ digits
        with no surrounding digits, replace it with 'RS <digits>' so that
        the currency-prefix regex in Tier-1 picks it up.
        """
        # Replace actual Unicode ₹ with safe ASCII marker
        text = re.sub(r'[\u20b9\ufe69\u0024]', ' RS ', text)
        # Strip common OCR misread: lone 7 or 8 glued to a 2+ digit number
        text = re.sub(r'(?<![\d])([78])(\d{2,})(?![\d])', r' RS \2 ', text)
        # Strip lone 1 glued to 2+ digits (₹ misread as 1)
        text = re.sub(r'(?<![\d])(1)(\d{2,})(?![\d])', r' RS \2 ', text)
        return text

    def _check_amount(
        self, text_lower: str, expected: Decimal
    ) -> tuple[Decimal | None, CheckResult]:
        """
        30% — Mandatory: amount must match expected value.

        Matching tiers (tried in order, first match wins):
          Tier 1 — Standard prefix  : Rs 20 / INR 20 / RS 20 (after ₹ normalisation)
          Tier 2 — Rupee-misread    : 720/820 where 7/8 is a ₹ misread prefix
          Tier 3 — Decimal dropped  : 15000 read instead of 150.00
          Tier 4 — Standalone scan  : any number within ±1 of expected
        """
        exp_int = int(expected)

        # Pre-process: normalise ₹ misreads, collapse whitespace
        pre = self._strip_rupee_misread(text_lower)
        cleaned = re.sub(r'\s+', ' ', pre)

        detected: Decimal | None = None
        passed = False

        # ── Tier 1: standard currency prefix (rs / inr / rp) ─────────────────
        tier1 = r'(?:rs\.?\s*|inr\s*|rp\s*|RS\s*)([\d,]+(?:\.[\d]{1,2})?)'
        for raw in re.findall(tier1, cleaned):
            try:
                val = Decimal(raw.replace(',', ''))
                if val == expected or abs(val - expected) <= Decimal('1'):
                    detected, passed = val, True
                    break
            except Exception:
                continue

        # ── Tier 2: rupee-misread prefix still present (7xx / 8xx) ───────────
        # e.g. expected=20  ->  720, 820, 7020, 8020
        # e.g. expected=150 ->  7150, 8150
        if not passed:
            tier2_pats = [
                rf'\b[78]0*{re.escape(str(exp_int))}\b',
                rf'\b10*{re.escape(str(exp_int))}\b',
            ]
            # Also try against ORIGINAL text_lower (before strip_rupee_misread)
            for source in (cleaned, text_lower):
                for pat in tier2_pats:
                    if re.search(pat, source):
                        detected, passed = expected, True
                        break
                if passed:
                    break

        # ── Tier 3: decimal point dropped (150.00 read as 15000) ─────────────
        if not passed and '.' in str(expected):
            nodot = str(expected).replace('.', '')
            for source in (cleaned, text_lower):
                if re.search(rf'\b{re.escape(nodot)}\b', source):
                    detected, passed = expected, True
                    break

        # ── Tier 4: exhaustive standalone ±1 scan ────────────────────────────
        if not passed:
            for source in (cleaned, text_lower):
                for num in re.findall(r'\b\d+(?:\.\d{1,2})?\b', source):
                    try:
                        val = Decimal(num)
                        if val == expected or abs(val - expected) <= Decimal('1'):
                            detected, passed = val, True
                            break
                    except Exception:
                        continue
                if passed:
                    break

        return detected, CheckResult(
            name='Amount',
            passed=passed,
            weight=0.30,
            is_mandatory=True,
            detail=(
                f'Detected \u20b9{detected} matches expected \u20b9{expected}'
                if passed
                else (
                    f'Expected \u20b9{expected} not found. '
                    f'Snippet: "{text_lower[:100]}"'
                )
            ),
        )

    def _check_date(self, text_lower: str) -> CheckResult:
        """10% — Mandatory: screenshot must show today's date."""
        now = datetime.now()
        
        # Helper to check if a specific datetime's date is in the text
        def check_dt(dt: datetime) -> bool:
            day = str(dt.day)
            month_short = dt.strftime("%b").lower()
            month_full = dt.strftime("%B").lower()
            year = str(dt.year)
            
            has_month = month_short in text_lower or month_full in text_lower
            has_day = re.search(rf"\b{day}\b", text_lower) is not None
            return has_month and has_day

        has_today = "today" in text_lower
        
        passed = has_today or check_dt(now)
        date_str_today = now.strftime('%d %b %Y')

        return CheckResult(
            name="Date (Today)",
            passed=passed,
            weight=0.10,
            is_mandatory=True,
            detail=(
                f"Matched date ({date_str_today}) in screenshot"
                if passed
                else f"Date must be today ({date_str_today})"
            ),
        )

    def _check_time_freshness(
        self, text_lower: str, order_created_at: datetime | None
    ) -> CheckResult:
        """5% — Soft: screenshot time should be within 30 minutes of now."""
        if order_created_at is None:
            return CheckResult(
                name="Time Freshness",
                passed=False,
                weight=0.05,
                is_mandatory=False,
                detail="Order timestamp not provided — skipped.",
            )

        # Try to extract time from screenshot text (e.g. "5:28 PM", "17:28", "1;08 pm")
        time_pattern = r"(\d{1,2})[:;.\-\s](\d{2})\s*(am|pm)?"
        match = re.search(time_pattern, text_lower)

        if not match:
            return CheckResult(
                name="Time Freshness",
                passed=False,
                weight=0.05,
                is_mandatory=False,
                detail="No time found in screenshot.",
            )

        hour = int(match.group(1))
        minute = int(match.group(2))
        ampm = (match.group(3) or "").strip().lower()

        if ampm == "pm" and hour != 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0

        now = datetime.now()
        screenshot_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        delta_minutes = abs((now - screenshot_time).total_seconds() / 60)

        passed = delta_minutes <= OCR_TIME_FRESHNESS_MINUTES

        return CheckResult(
            name="Time Freshness",
            passed=passed,
            weight=0.05,
            is_mandatory=False,
            detail=(
                f"Screenshot time {hour:02d}:{minute:02d} is "
                f"{delta_minutes:.0f} min old "
                f"({'✅ fresh' if passed else '⚠️ stale'})"
            ),
        )

    def _is_hard_blocked(
        self, text_lower: str, order_created_at: datetime | None = None
    ) -> bool:
        """
        Hard block: if the screenshot time is > 2 hours before the reference time.

        Reference time priority:
          1. order_created_at — most accurate (payment must be before order placement)
          2. datetime.now()   — fallback if order timestamp is not available
        """
        time_pattern = r"(\d{1,2})[:;.\-\s](\d{2})\s*(am|pm)?"
        match = re.search(time_pattern, text_lower)
        if not match:
            return False

        hour = int(match.group(1))
        minute = int(match.group(2))
        ampm = (match.group(3) or "").strip().lower()
        if ampm == "pm" and hour != 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0

        reference = order_created_at if order_created_at else datetime.now()
        screenshot_time = reference.replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
        # Screenshot should be BEFORE reference time (user pays first)
        delta_hours = (reference - screenshot_time).total_seconds() / 3600
        return delta_hours > OCR_TIME_HARD_BLOCK_HOURS

    def _normalize_upi_string(self, val: str) -> str:
        """Normalize UPI strings to handle dots, spaces, and letter/digit misreads."""
        val = val.lower().strip()
        val = re.sub(r'[^a-z0-9@]', '', val)
        val = val.replace('1', 'l').replace('i', 'l')
        val = val.replace('0', 'o')
        return val

    def _check_upi_id(self, text_lower: str) -> CheckResult:
        """5% — Soft: check if a UPI ID pattern is present in screenshot."""
        # Generic UPI ID pattern: word@word
        upi_pattern = r"\b[\w.\-]+@[\w.\-]+\b"
        matches = re.findall(upi_pattern, text_lower)

        passed = len(matches) > 0
        matched_id = matches[0] if matches else None

        if self._upi_id and matched_id:
            # Fuzzy match our own UPI ID
            norm_target = self._normalize_upi_string(self._upi_id)
            normalized_text = self._normalize_upi_string(text_lower)
            passed = norm_target in normalized_text

        return CheckResult(
            name="UPI ID",
            passed=passed,
            weight=0.05,
            is_mandatory=False,
            detail=(
                f"UPI ID detected: {matched_id}"
                if passed
                else "No matching UPI ID found"
            ),
        )

    def _extract_utr(self, raw_text: str) -> tuple[str | None, CheckResult]:
        """5% — Bonus: extract UTR/Transaction ID from text."""
        # UTR numbers are typically 12-digit numeric strings
        utr_patterns = [
            r"utr\s*(?:no\.?|number|#)?\s*:?\s*(\w{8,20})",
            r"transaction\s*id\s*:?\s*(\w{8,20})",
            r"ref\s*(?:no\.?|number|#)?\s*:?\s*(\w{8,20})",
            r"upi\s*(?:ref|transaction)\s*(?:id|no)?\s*:?\s*(\w{8,20})",
        ]
        text_lower = raw_text.lower()
        utr_found: str | None = None

        for pattern in utr_patterns:
            match = re.search(pattern, text_lower)
            if match:
                utr_found = match.group(1).upper()
                break

        return utr_found, CheckResult(
            name="UTR Available",
            passed=utr_found is not None,
            weight=0.05,
            is_mandatory=False,
            detail=(
                f"UTR extracted: {utr_found}"
                if utr_found
                else "No UTR/Transaction ID found"
            ),
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_notes(
        self,
        checks: list[CheckResult],
        confidence: float,
        app: str,
        mandatory_failed: bool,
        hard_block: bool,
        is_near_miss: bool,
    ) -> str:
        """Build a human-readable admin summary of the OCR result."""
        lines = [f"📱 App: {app}", f"🎯 Confidence: {int(confidence * 100)}%", ""]

        for c in checks:
            icon = "✅" if c.passed else ("❌" if c.is_mandatory else "⚠️")
            lines.append(f"{icon} {c.name}: {c.detail}")

        lines.append("")

        if hard_block:
            lines.append("🚫 HARD BLOCK: Screenshot is older than 2 hours. Manual review required.")
        elif mandatory_failed:
            lines.append("❌ MANDATORY CHECK FAILED: Payment requires manual admin review.")
        elif is_near_miss:
            lines.append(
                "⚠️ NEAR MISS (85-89%): Consider asking user to share full receipt with UTR."
            )
        elif confidence >= OCR_AUTO_APPROVE_THRESHOLD:
            lines.append("✅ AUTO-APPROVED: All mandatory checks passed, confidence ≥ 90%.")
        else:
            lines.append("🔍 MANUAL REVIEW: Confidence below threshold.")

        return "\n".join(lines)

    def _fallback_result(self, reason: str) -> OCRResult:
        """Return a safe fallback result when OCR completely fails."""
        logger.warning("OCR fallback triggered: %s", reason)
        return OCRResult(
            confidence=0.0,
            requires_review=True,
            is_near_miss=False,
            detected_amount=None,
            detected_app="Unknown",
            utr_number=None,
            raw_text="",
            notes=f"⚠️ OCR Failed: {reason}\nPayment routed to manual admin review.",
        )
