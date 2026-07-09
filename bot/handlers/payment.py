"""
bot/handlers/payment.py

Payment proof submission handlers (FSM-based flow).

Flow:
  1. /pay <order_id>   — Validates order, enters FSM state
  2. User sends photo  — Receives screenshot, submits payment proof,
                         runs OCR check, notifies admin queue

Rules (from PROJECT_RULES.md — Rule 5 & Rule 10):
  - Handlers receive updates and call services.
  - No business logic is permitted here.
  - FSM state must be respected — never bypass state transitions.
"""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, PhotoSize

from bot.states.payment import PaymentStates
from core.constants import MSG_ERROR_GENERIC
from services.ocr_service import OCRService
from services.order_service import OrderService, OrderServiceError

logger = logging.getLogger(__name__)

router = Router(name="payment")


# ---------------------------------------------------------------------------
# Step 1: /pay <order_id> — initiate payment proof submission
# ---------------------------------------------------------------------------

@router.message(Command("pay"))
async def handle_pay_initiate(
    message: Message,
    state: FSMContext,
    order_service: OrderService,
) -> None:
    """
    Handle /pay <order_id> — begin payment proof submission.

    Validates:
      - order_id argument is present and numeric
      - Order exists and belongs to the user
      - Order is in 'pending' status

    On success: enters PaymentStates.waiting_for_proof
    """
    user = message.from_user
    if user is None:
        return

    args = (message.text or "").split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer(
            "⚠️ Usage: <code>/pay &lt;order_id&gt;</code>\n\n"
            "Example: <code>/pay 12</code>\n\n"
            "Use /myorders to see your order IDs.",
            parse_mode="HTML",
        )
        return

    order_id = int(args[1])

    try:
        order = await order_service.get_order(order_id)

        if order is None or order.user_id != user.id:
            await message.answer(
                f"❌ Order <code>{order_id}</code> not found.\n\n"
                "Use /myorders to see your orders.",
                parse_mode="HTML",
            )
            return

        if order.status.value != "pending":
            await message.answer(
                f"❌ Cannot submit payment for this order.\n\n"
                f"Current status: {order.status_display}\n\n"
                "Only <b>pending</b> orders can receive payment proof.",
                parse_mode="HTML",
            )
            return

        # Store order context in FSM data
        await state.set_state(PaymentStates.waiting_for_proof)
        await state.update_data(order_id=order_id, amount=str(order.amount))

        await message.answer(
            f"💳 <b>Payment Submission</b>\n\n"
            f"📦 Order ID: <code>{order_id}</code>\n"
            f"💰 Amount: {order.amount_display}\n\n"
            f"📸 Please send a <b>clear screenshot</b> of your payment.\n\n"
            f"✅ The screenshot should show:\n"
            f"  • Receiver name\n"
            f"  • Amount paid\n"
            f"  • Date and time\n\n"
            f"Send the photo now, or /cancel to abort.",
            parse_mode="HTML",
        )
        logger.info(
            "Payment flow initiated | user_id=%s | order_id=%s",
            user.id, order_id,
        )
    except Exception:
        logger.exception("handle_pay_initiate failed | user_id=%s | order_id=%s", user.id, order_id)
        await message.answer(MSG_ERROR_GENERIC)


# ---------------------------------------------------------------------------
# Step 2: Photo received — submit proof
# ---------------------------------------------------------------------------

@router.message(PaymentStates.waiting_for_proof, F.photo)
async def handle_payment_photo(
    message: Message,
    state: FSMContext,
    order_service: OrderService,
    ocr_service: OCRService,
    bot: Bot,
) -> None:
    """
    Receive the payment screenshot and submit proof.

    - Gets the highest-resolution photo from Telegram
    - Calls OCRService.verify_payment() (Sprint 4: always routes to review)
    - Calls OrderService.submit_payment_proof()
    - Notifies the user of next steps
    """
    user = message.from_user
    if user is None:
        return

    # Retrieve FSM context data
    data = await state.get_data()
    order_id: int = data.get("order_id")
    amount_str: str = data.get("amount", "0")

    if not order_id:
        await state.clear()
        await message.answer("❌ Session expired. Please use /pay again.")
        return

    # Get highest resolution photo (last in list = largest)
    photos: list[PhotoSize] = message.photo
    if not photos:
        await message.answer("⚠️ No photo received. Please send a payment screenshot.")
        return

    best_photo = photos[-1]
    file_id = best_photo.file_id

    try:
        from decimal import Decimal
        expected_amount = Decimal(amount_str)

        # Run OCR verification (Sprint 4: placeholder — always requires review)
        ocr_result = await ocr_service.verify_payment(
            file_id=file_id,
            expected_amount=expected_amount,
        )

        # Submit payment proof to OrderService
        order = await order_service.submit_payment_proof(
            order_id=order_id,
            user_id=user.id,
            file_id=file_id,
        )

        # Clear FSM state
        await state.clear()

        if ocr_result.requires_review:
            # Notify user — under review
            await message.answer(
                f"✅ <b>Payment Screenshot Received!</b>\n\n"
                f"📦 Order ID: <code>{order.id}</code>\n"
                f"🔖 Status: {order.status_display}\n\n"
                f"⏳ Your payment is being reviewed by our team.\n"
                f"You will be notified once it is confirmed.\n\n"
                f"Use /orderstatus {order.id} to track your order.",
                parse_mode="HTML",
            )
        else:
            # Auto-approved path (Sprint 5 — OCR confidence >= threshold)
            await message.answer(
                f"✅ <b>Payment Verified!</b>\n\n"
                f"📦 Order ID: <code>{order.id}</code>\n"
                f"Your payment has been automatically verified.\n"
                f"Your order will be processed shortly.",
                parse_mode="HTML",
            )

        logger.info(
            "Payment proof submitted | user_id=%s | order_id=%s | "
            "ocr_confidence=%.2f | requires_review=%s | event=payment.proof_submitted",
            user.id, order_id,
            ocr_result.confidence,
            ocr_result.requires_review,
        )

    except OrderServiceError as exc:
        await state.clear()
        await message.answer(f"❌ {exc}")
    except Exception:
        logger.exception(
            "handle_payment_photo failed | user_id=%s | order_id=%s",
            user.id, order_id,
        )
        await state.clear()
        await message.answer(MSG_ERROR_GENERIC)


# ---------------------------------------------------------------------------
# Cancel FSM flow
# ---------------------------------------------------------------------------

@router.message(PaymentStates.waiting_for_proof, Command("cancel"))
async def handle_payment_cancel(message: Message, state: FSMContext) -> None:
    """Cancel the ongoing payment proof submission flow."""
    await state.clear()
    await message.answer(
        "❌ Payment submission cancelled.\n\n"
        "Your order remains in <b>pending</b> status.\n"
        "Use /pay to try again when ready.",
        parse_mode="HTML",
    )


@router.message(PaymentStates.waiting_for_proof)
async def handle_payment_wrong_input(message: Message) -> None:
    """Remind user to send a photo, not text."""
    await message.answer(
        "📸 Please send a <b>photo</b> of your payment screenshot.\n\n"
        "Use /cancel to abort the payment submission.",
        parse_mode="HTML",
    )
