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
from aiogram.types import Message, PhotoSize, CallbackQuery

from config import settings

from bot.states.payment import PaymentStates
from core.constants import MSG_ERROR_GENERIC
from services.ocr_service import OCRService
from services.order_service import OrderService, OrderServiceError
from services.product_service import ProductService

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
        await state.update_data(
            order_id=order_id,
            amount=str(order.amount),
            order_created_at=order.created_at,
        )

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
    product_service: ProductService,
    utr_repo=None,  # UTRRepository — injected via dispatcher workflow data
) -> None:
    """
    Receive the payment screenshot and submit proof.

    Sprint 7 flow:
    1. Download image bytes from Telegram
    2. Run real OCR weighted scoring
    3. Check UTR duplicate (fraud prevention)
    4. Submit payment proof to OrderService
    5. Route to auto-approve OR manual review based on confidence
    """
    user = message.from_user
    if user is None:
        return

    # Retrieve FSM context data
    data = await state.get_data()
    order_id: int = data.get("order_id")
    amount_str: str = data.get("amount", "0")
    order_created_at = data.get("order_created_at")  # datetime stored at order placement

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

    # Processing indicator
    processing_msg = await message.answer("🔍 Verifying your payment screenshot...")

    try:
        from decimal import Decimal
        from datetime import datetime

        expected_amount = Decimal(amount_str)

        if settings.feature_ocr_enabled:
            # ── Step 1: Download image bytes from Telegram ────────────────────
            image_bytes: bytes = b""
            try:
                tg_file = await bot.get_file(file_id)
                image_bytes = await bot.download_file(tg_file.file_path)
                if hasattr(image_bytes, "read"):
                    image_bytes = image_bytes.read()
            except Exception as dl_exc:
                logger.warning(
                    "Image download failed | file_id=%s | error=%s — OCR will fallback",
                    file_id, dl_exc,
                )

            # ── Step 2: Run OCR weighted scoring ─────────────────────────────
            ocr_result = await ocr_service.verify_payment(
                image_bytes=image_bytes,
                expected_amount=expected_amount,
                order_created_at=order_created_at,
            )
        else:
            # Fallback when OCR is disabled
            from services.ocr_service import OCRResult
            ocr_result = OCRResult(
                confidence=0.0,
                requires_review=True,
                is_near_miss=False,
                detected_amount=None,
                detected_app="Unknown",
                utr_number=None,
                raw_text="",
                notes="OCR is disabled. Payment routed to manual review."
            )

        # ── Step 3: UTR Duplicate fraud check ─────────────────────────────
        utr_is_duplicate = False
        if ocr_result.utr_number and utr_repo:
            try:
                utr_is_duplicate = await utr_repo.exists(ocr_result.utr_number)
            except Exception as utr_exc:
                logger.error("UTR duplicate check failed: %s", utr_exc)

        if utr_is_duplicate:
            await processing_msg.delete()
            await state.clear()
            await message.answer(
                "❌ <b>Duplicate Transaction Detected!</b>\n\n"
                "This payment proof has already been submitted for another order.\n\n"
                "If you believe this is an error, please contact support.",
                parse_mode="HTML",
            )
            logger.warning(
                "Duplicate UTR blocked | user_id=%s | order_id=%s | utr=%s | "
                "event=payment.duplicate_utr",
                user.id, order_id, ocr_result.utr_number,
            )
            return

        # ── Step 4: Submit payment proof ──────────────────────────────────
        order = await order_service.submit_payment_proof(
            order_id=order_id,
            user_id=user.id,
            file_id=file_id,
        )

        # Clear FSM state
        await state.clear()
        await processing_msg.delete()

        # ── Step 5: Route based on OCR result ─────────────────────────────

        if ocr_result.auto_approved:
            # ✅ Auto-approved — high confidence, save UTR
            if ocr_result.utr_number and utr_repo:
                try:
                    await utr_repo.save(ocr_result.utr_number, order_id)
                except Exception:
                    pass  # Non-critical, log only

            from bot.handlers.fulfillment import fulfill_and_notify_order
            await fulfill_and_notify_order(
                order_id=order_id,
                order_service=order_service,
                product_service=product_service,
                bot=bot,
            )

            await message.answer(
                f"⚡ <b>Payment Automatically Verified!</b>\n\n"
                f"📦 Order ID: <code>{order.id}</code>\n"
                f"🎯 Confidence: {ocr_result.confidence_percent}%\n"
                f"📱 App: {ocr_result.detected_app}\n\n"
                f"Your order has been automatically processed and delivered.",
                parse_mode="HTML",
            )

        elif ocr_result.is_near_miss:
            # ⚠️ Near miss — ask for full receipt, but also alert admin
            await message.answer(
                f"⚠️ <b>Partial Verification</b>\n\n"
                f"📦 Order ID: <code>{order.id}</code>\n"
                f"🎯 Confidence: {ocr_result.confidence_percent}%\n\n"
                f"Your payment was partially verified. For <b>faster processing</b>, "
                f"please also share the complete receipt with UTR/Transaction ID.\n\n"
                f"Otherwise, your order will be manually reviewed within <b>6 hours</b>.\n\n"
                f"Use /orderstatus {order.id} to track your order.",
                parse_mode="HTML",
            )
            # Still alert admins
            await _alert_admins(bot, order, user, ocr_result, is_near_miss=True)

        else:
            # 🔍 Manual review required
            await message.answer(
                f"✅ <b>Payment Screenshot Received!</b>\n\n"
                f"📦 Order ID: <code>{order.id}</code>\n"
                f"🔖 Status: {order.status_display}\n\n"
                f"⏳ Your payment is being reviewed by our team.\n"
                f"You will be notified once it is confirmed.\n\n"
                f"Use /orderstatus {order.id} to track your order.",
                parse_mode="HTML",
            )
            await _alert_admins(bot, order, user, ocr_result, is_near_miss=False)

        logger.info(
            "Payment proof submitted | user_id=%s | order_id=%s | "
            "app=%s | confidence=%.0f%% | auto_approved=%s | utr=%s | "
            "event=payment.proof_submitted",
            user.id, order_id,
            ocr_result.detected_app,
            ocr_result.confidence * 100,
            ocr_result.auto_approved,
            ocr_result.utr_number,
        )

    except OrderServiceError as exc:
        await state.clear()
        try:
            await processing_msg.delete()
        except Exception:
            pass
        await message.answer(f"❌ {exc}")
    except Exception:
        logger.exception(
            "handle_payment_photo failed | user_id=%s | order_id=%s",
            user.id, order_id,
        )
        await state.clear()
        try:
            await processing_msg.delete()
        except Exception:
            pass
        await message.answer(MSG_ERROR_GENERIC)


async def _alert_admins(bot, order, user, ocr_result, *, is_near_miss: bool) -> None:
    """Send payment review alert to all configured admins."""
    icon = "⚠️" if is_near_miss else "🔔"
    tag = "NEAR MISS" if is_near_miss else "REVIEW REQUIRED"

    admin_text = (
        f"{icon} <b>Payment Proof — {tag}</b>\n\n"
        f"📦 Order ID: <code>{order.id}</code>\n"
        f"💰 Amount: {order.amount_display}\n"
        f"👤 User: <b>{getattr(user, 'full_name', None) or user.first_name}</b> "
        f"(ID: <code>{user.id}</code>)\n"
        f"📱 App: {ocr_result.detected_app}\n"
        f"🎯 OCR Confidence: {ocr_result.confidence_percent}%\n"
    )
    if ocr_result.utr_number:
        admin_text += f"🔑 UTR: <code>{ocr_result.utr_number}</code>\n"

    admin_text += "\nUse the buttons below to review:"

    for admin_id in settings.admin_ids:
        try:
            from bot.keyboards import get_admin_review_keyboard
            await bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode="HTML",
                reply_markup=get_admin_review_keyboard(order.id),
            )
        except Exception as alert_exc:
            logger.error(
                "Failed to alert admin %s | error=%s", admin_id, alert_exc
            )




@router.callback_query(F.data.startswith("pay_proof:"))
async def handle_pay_proof_callback(
    callback: CallbackQuery,
    state: FSMContext,
    order_service: OrderService,
) -> None:
    """Handle click on Submit Payment Proof inline button."""
    order_id = int(callback.data.split(":", 1)[1])
    await callback.answer()

    message = callback.message
    if not message:
        return
    new_message = message.model_copy(update={"from_user": callback.from_user, "text": f"/pay {order_id}"})

    from bot.handlers.payment import handle_pay_initiate
    await handle_pay_initiate(new_message, state, order_service)


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
