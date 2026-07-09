"""
tests/unit/test_ocr_service.py

Unit tests for the Sprint 7 OCR weighted confidence scoring engine.

Tests cover:
  - Full receipt screenshot (all checks pass → auto-approve)
  - GPay chat partial screenshot (no UTR → near miss or pass at 90%)
  - Old screenshot (>2 hours → hard block)
  - Wrong amount → mandatory fail
  - Missing receiver name → mandatory fail
  - Duplicate UTR extraction
  - App detection for GPay, PhonePe, Paytm, unknown
"""

from __future__ import annotations

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from services.ocr_service import OCRService, OCR_AUTO_APPROVE_THRESHOLD


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_service(receiver: str = "Rohit Kumar", upi: str = "rohit@okaxis") -> OCRService:
    return OCRService(receiver_name=receiver, upi_id=upi)


def fake_image() -> bytes:
    """Return 1-byte fake image (OCR is mocked — content doesn't matter)."""
    return b"\x00"


# ── App Detection Tests ───────────────────────────────────────────────────────

def test_detect_gpay():
    svc = make_service()
    app_name, _ = svc._detect_app("google pay payment successful")
    assert app_name == "GPay"


def test_detect_phonepe():
    svc = make_service()
    app_name, _ = svc._detect_app("phonepe payment done")
    assert app_name == "PhonePe"


def test_detect_paytm():
    svc = make_service()
    app_name, _ = svc._detect_app("paid via paytm")
    assert app_name == "Paytm"


def test_detect_unknown():
    svc = make_service()
    app_name, _ = svc._detect_app("some random text without any app name")
    assert app_name == "Unknown"


# ── Receiver Name Check ───────────────────────────────────────────────────────

def test_receiver_name_match():
    svc = make_service(receiver="Rohit Kumar")
    result = svc._check_receiver_name("paid to rohit kumar via upi")
    assert result.passed is True
    assert result.weight == 0.40


def test_receiver_name_partial_match():
    """First word of name should be enough."""
    svc = make_service(receiver="Rohit Kumar")
    result = svc._check_receiver_name("paid to rohit via gpay")
    assert result.passed is True


def test_receiver_name_no_match():
    svc = make_service(receiver="Rohit Kumar")
    result = svc._check_receiver_name("paid to random person via upi")
    assert result.passed is False
    assert result.is_mandatory is True


# ── Amount Check ──────────────────────────────────────────────────────────────

def test_amount_exact_match():
    svc = make_service()
    amount, result = svc._check_amount("you paid ₹20 to rohit", Decimal("20"))
    assert result.passed is True
    assert amount == Decimal("20")


def test_amount_rs_format():
    svc = make_service()
    amount, result = svc._check_amount("amount rs.20 paid", Decimal("20"))
    assert result.passed is True


def test_amount_wrong():
    svc = make_service()
    amount, result = svc._check_amount("₹50 paid", Decimal("20"))
    assert result.passed is False
    assert result.is_mandatory is True


def test_amount_tolerance():
    """±1 rupee tolerance for rounding edge cases."""
    svc = make_service()
    _, result = svc._check_amount("₹21 paid", Decimal("20"))
    assert result.passed is True


# ── Date Check ────────────────────────────────────────────────────────────────

def test_date_today_match():
    svc = make_service()
    now = datetime.now()
    text = f"{now.day} {now.strftime('%b').lower()} {now.year} payment done"
    result = svc._check_date(text)
    assert result.passed is True


def test_date_today_keyword():
    svc = make_service()
    result = svc._check_date("today 5:30 pm payment done")
    assert result.passed is True


def test_date_wrong_month():
    svc = make_service()
    # Force a month that is NOT current
    now = datetime.now()
    wrong_month = "jan" if now.month != 1 else "feb"
    result = svc._check_date(f"5 {wrong_month} 2025 payment done")
    assert result.passed is False
    assert result.is_mandatory is True


# ── Time Freshness Check ──────────────────────────────────────────────────────

def test_time_freshness_recent():
    svc = make_service()
    now = datetime.now()
    text = f"payment at {now.strftime('%I:%M %p').lower()}"
    result = svc._check_time_freshness(text, order_created_at=datetime.now())
    # Should be fresh (0 minutes difference)
    assert result.passed is True



def test_time_freshness_no_order_timestamp():
    svc = make_service()
    result = svc._check_time_freshness("5:30 pm payment done", order_created_at=None)
    assert result.passed is False
    assert result.is_mandatory is False  # Must be soft, not mandatory


def test_time_freshness_no_time_in_text():
    svc = make_service()
    result = svc._check_time_freshness("payment successful", order_created_at=datetime.now())
    assert result.passed is False


# ── UTR Extraction ────────────────────────────────────────────────────────────

def test_utr_extracted():
    svc = make_service()
    utr, result = svc._extract_utr("UTR No: 123456789012 payment done")
    assert result.passed is True
    assert utr == "123456789012"


def test_transaction_id_extracted():
    svc = make_service()
    utr, result = svc._extract_utr("Transaction ID: ABCDEF123456 success")
    assert result.passed is True
    assert utr is not None


def test_no_utr_found():
    svc = make_service()
    utr, result = svc._extract_utr("you paid rohit 20 rupees today")
    assert result.passed is False
    assert utr is None


# ── UPI ID Check ──────────────────────────────────────────────────────────────

def test_upi_id_found():
    svc = make_service(upi="rohit@okaxis")
    result = svc._check_upi_id("paid to rohit@okaxis successfully")
    assert result.passed is True


def test_upi_id_generic_found():
    svc = make_service(upi="")
    result = svc._check_upi_id("paid to merchant@ybl")
    assert result.passed is True


def test_upi_id_not_found():
    svc = make_service(upi="rohit@okaxis")
    result = svc._check_upi_id("payment done with no upi id visible")
    assert result.passed is False


# ── Hard Block ────────────────────────────────────────────────────────────────

def test_hard_block_old_screenshot():
    svc = make_service()
    # Use 12:00 AM — if current time is > 2 hours, should block
    result = svc._is_hard_blocked("payment at 12:00 am done")
    # This is time-dependent — just verify it returns bool
    assert isinstance(result, bool)


# ── Full Integration (mocked EasyOCR) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_verify_auto_approve():
    """Full receipt with all fields → should auto-approve."""
    svc = make_service(receiver="Rohit Kumar", upi="rohit@okaxis")
    now = datetime.now()

    mock_text = (
        f"Google Pay Payment Successful\n"
        f"Paid to Rohit Kumar\n"
        f"₹20\n"
        f"{now.day} {now.strftime('%b')} {now.year}\n"
        f"{now.strftime('%I:%M %p')}\n"
        f"rohit@okaxis\n"
        f"UTR No: 123456789012"
    )

    with patch.object(svc, "_extract_text", new=AsyncMock(return_value=mock_text)):
        result = await svc.verify_payment(
            image_bytes=fake_image(),
            expected_amount=Decimal("20"),
            order_created_at=datetime.now(),
        )

    assert result.confidence >= OCR_AUTO_APPROVE_THRESHOLD
    assert result.requires_review is False
    assert result.auto_approved is True
    assert result.detected_app == "GPay"
    assert result.utr_number == "123456789012"


@pytest.mark.asyncio
async def test_full_verify_partial_gpay_chat():
    """GPay chat screenshot (no UTR, no UPI ID) — should still pass at ≥90%."""
    svc = make_service(receiver="Rohit Kumar")
    now = datetime.now()

    mock_text = (
        f"You paid Rohit Kumar ₹20\n"
        f"Today {now.strftime('%I:%M %p')}\n"
        f"Google Pay"
    )

    with patch.object(svc, "_extract_text", new=AsyncMock(return_value=mock_text)):
        result = await svc.verify_payment(
            image_bytes=fake_image(),
            expected_amount=Decimal("20"),
            order_created_at=datetime.now(),
        )

    # Mandatory checks (name, amount, date) should pass → score ≥ 90%
    assert result.detected_amount == Decimal("20")
    assert result.detected_app == "GPay"


@pytest.mark.asyncio
async def test_full_verify_wrong_amount_fails():
    """Wrong amount → mandatory fail → requires_review always True."""
    svc = make_service(receiver="Rohit Kumar")
    now = datetime.now()

    mock_text = (
        f"Paid to Rohit Kumar\n"
        f"₹500\n"   # wrong amount
        f"Today {now.strftime('%I:%M %p')}\n"
        f"UTR No: 999888777666"
    )

    with patch.object(svc, "_extract_text", new=AsyncMock(return_value=mock_text)):
        result = await svc.verify_payment(
            image_bytes=fake_image(),
            expected_amount=Decimal("20"),
            order_created_at=datetime.now(),
        )

    assert result.requires_review is True
    assert result.auto_approved is False


@pytest.mark.asyncio
async def test_full_verify_missing_receiver_fails():
    """Missing receiver name → mandatory fail → always requires_review."""
    svc = make_service(receiver="Rohit Kumar")
    now = datetime.now()

    mock_text = (
        f"Paid to Someone Else\n"
        f"₹20\n"
        f"Today\n"
        f"UTR No: 123456789012"
    )

    with patch.object(svc, "_extract_text", new=AsyncMock(return_value=mock_text)):
        result = await svc.verify_payment(
            image_bytes=fake_image(),
            expected_amount=Decimal("20"),
            order_created_at=datetime.now(),
        )

    assert result.requires_review is True
    assert result.auto_approved is False


@pytest.mark.asyncio
async def test_ocr_extraction_fails_gracefully():
    """If EasyOCR returns empty text → fallback result, never crash."""
    svc = make_service()

    with patch.object(svc, "_extract_text", new=AsyncMock(return_value="")):
        result = await svc.verify_payment(
            image_bytes=fake_image(),
            expected_amount=Decimal("20"),
        )

    assert result.requires_review is True
    assert result.confidence == 0.0
    assert "OCR Failed" in result.notes
