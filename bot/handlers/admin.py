"""
bot/handlers/admin.py

Admin commands for order approval, rejection, and queue management.

Commands:
  - /pendingpayments  — List all orders awaiting payment verification
  - /approvepayment <id> — Confirm payment and update order to confirmed
  - /rejectpayment <id>  — Reject payment and cancel order

Rules (from PROJECT_RULES.md — Rule 5):
  - Handlers receive updates and call services.
  - No business logic is permitted here.
  - Verification of admin privilege uses settings.admin_ids.
"""

from __future__ import annotations

import logging

from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.types import Message

from config import settings
from core.constants import MSG_ERROR_GENERIC
from services.order_service import OrderService, OrderServiceError
from services.support_service import SupportService
from services.user_service import UserService


logger = logging.getLogger(__name__)

router = Router(name="admin")


# ---------------------------------------------------------------------------
# Authorization Decorator/Check
# ---------------------------------------------------------------------------

def is_admin(user_id: int | None) -> bool:
    """Check if the Telegram user ID is registered in settings.admin_ids."""
    if user_id is None:
        return False
    return user_id in settings.admin_ids


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

@router.message(Command("pendingpayments"))
async def handle_pending_payments(
    message: Message, order_service: OrderService
) -> None:
    """
    Handle /pendingpayments — list all orders in payment_submitted status.
    """
    user = message.from_user
    if not user or not is_admin(user.id):
        return  # Silently ignore non-admins to prevent discovery

    try:
        orders = await order_service.list_pending_payments()

        if not orders:
            await message.answer("📥 <b>Pending Payments</b>\n\nNo payments are awaiting review.")
            return

        lines = ["📥 <b>Pending Payments Awaiting Review</b>\n"]
        for o in orders:
            lines.append(
                f"▪️ <b>Order #{o.id}</b>\n"
                f"   👤 User ID: <code>{o.user_id}</code>\n"
                f"   💰 Amount: {o.amount_display}\n"
                f"   📸 Proof: /proof_{o.id}\n"
                f"   ⚙️ Actions: /approvepayment {o.id} or /rejectpayment {o.id}"
            )
            lines.append("")

        await message.answer("\n".join(lines), parse_mode="HTML")
    except Exception:
        logger.exception("handle_pending_payments failed")
        await message.answer(MSG_ERROR_GENERIC)


@router.message(Command("proof"))
@router.message(F.text.startswith("/proof_"))
async def handle_view_proof(
    message: Message, order_service: OrderService, bot: Bot
) -> None:
    """
    Handle /proof_<id> deep-link to view the uploaded payment screenshot.
    """
    user = message.from_user
    if not user or not is_admin(user.id):
        return

    text = message.text or ""
    if text.startswith("/proof_"):
        text = text.replace("/proof_", "/proof ", 1)

    parts = text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("⚠️ Invalid command. Format: /proof_&lt;order_id&gt;", parse_mode="HTML")
        return

    order_id = int(parts[1])

    try:
        order = await order_service.get_order(order_id)
        if order is None:
            await message.answer(f"❌ Order #{order_id} not found.")
            return

        if not order.payment_proof:
            await message.answer(f"❌ No payment proof submitted for Order #{order_id}.")
            return

        await bot.send_photo(
            chat_id=message.chat.id,
            photo=order.payment_proof,
            caption=f"📸 Payment proof for <b>Order #{order.id}</b>\n💰 Amount: {order.amount_display}",
            parse_mode="HTML",
        )
    except Exception:
        logger.exception("handle_view_proof failed | order_id=%s", order_id)
        await message.answer(MSG_ERROR_GENERIC)


@router.message(Command("approvepayment"))
async def handle_approve_payment(
    message: Message, order_service: OrderService, bot: Bot
) -> None:
    """
    Handle /approvepayment <id> — confirm the order and notify the user.
    """
    user = message.from_user
    if not user or not is_admin(user.id):
        return

    args = (message.text or "").split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("⚠️ Usage: <code>/approvepayment &lt;order_id&gt;</code>", parse_mode="HTML")
        return

    order_id = int(args[1])

    try:
        # Confirm the order via service
        order = await order_service.confirm_order(order_id)
        await message.answer(
            f"🟢 <b>Order #{order.id} Approved!</b>\n\nStatus updated to: {order.status_display}",
            parse_mode="HTML",
        )

        # Notify the buyer
        try:
            await bot.send_message(
                chat_id=order.user_id,
                text=(
                    f"🎉 <b>Payment Approved!</b>\n\n"
                    f"📦 Order ID: <code>{order.id}</code>\n"
                    f"💰 Amount: {order.amount_display}\n"
                    f"🔖 Status: {order.status_display}\n\n"
                    f"Your order is now being processed. Thank you for your purchase!"
                ),
                parse_mode="HTML",
            )
            logger.info("Buyer notified of payment approval | order_id=%s | buyer_id=%s", order.id, order.user_id)
        except Exception as notify_exc:
            logger.error("Failed to notify buyer | order_id=%s | error=%s", order.id, notify_exc)

    except OrderServiceError as exc:
        await message.answer(f"❌ {exc}")
    except Exception:
        logger.exception("handle_approve_payment failed | order_id=%s", order_id)
        await message.answer(MSG_ERROR_GENERIC)


@router.message(Command("rejectpayment"))
async def handle_reject_payment(
    message: Message, order_service: OrderService, bot: Bot
) -> None:
    """
    Handle /rejectpayment <id> [reason] — reject payment, cancel order, and notify user.
    """
    user = message.from_user
    if not user or not is_admin(user.id):
        return

    args = (message.text or "").split(maxsplit=2)
    if len(args) < 2 or not args[1].isdigit():
        await message.answer(
            "⚠️ Usage: <code>/rejectpayment &lt;order_id&gt; [reason]</code>", parse_mode="HTML"
        )
        return

    order_id = int(args[1])
    reason = args[2] if len(args) > 2 else "Invalid or unreadable screenshot."

    try:
        # Update order status to cancelled
        # Admin rejection cancels the order
        order = await order_service.get_order(order_id)
        if order is None:
            await message.answer(f"❌ Order #{order_id} not found.")
            return

        # Explicitly cancel the order using state update (notes can hold the reason)
        from schemas.order import OrderUpdateSchema, OrderStatus
        # We can update notes and set status to CANCELLED directly
        await order_service._orders.update(
            order_id,
            OrderUpdateSchema(status=OrderStatus.CANCELLED, notes=f"Rejected: {reason}"),
        )

        await message.answer(
            f"🔴 <b>Order #{order_id} Rejected</b>\n\n"
            f"Status updated to: ❌ Cancelled\n"
            f"Reason: {reason}",
            parse_mode="HTML",
        )

        # Notify the buyer
        try:
            await bot.send_message(
                chat_id=order.user_id,
                text=(
                    f"⚠️ <b>Payment Rejected</b>\n\n"
                    f"❌ Your payment proof for <b>Order #{order.id}</b> was rejected.\n"
                    f"📝 Reason: <i>{reason}</i>\n\n"
                    f"Please double check the details and submit again using <code>/pay {order.id}</code>."
                ),
                parse_mode="HTML",
            )
            logger.info("Buyer notified of payment rejection | order_id=%s | buyer_id=%s", order.id, order.user_id)
        except Exception as notify_exc:
            logger.error("Failed to notify buyer | order_id=%s | error=%s", order.id, notify_exc)

    except Exception:
        logger.exception("handle_reject_payment failed | order_id=%s", order_id)
        await message.answer(MSG_ERROR_GENERIC)


# ---------------------------------------------------------------------------
# Support and Broadcast Handlers
# ---------------------------------------------------------------------------

@router.message(Command("tickets"))
async def handle_tickets_list(
    message: Message, support_service: SupportService
) -> None:
    """List all open support tickets."""
    user = message.from_user
    if not user or not is_admin(user.id):
        return

    try:
        tickets = await support_service.list_open_tickets()
        if not tickets:
            await message.answer("🎫 <b>Support Tickets</b>\n\nNo open tickets at the moment.")
            return

        lines = ["🎫 <b>Open Support Tickets:</b>\n"]
        for t in tickets:
            assigned = "👨‍💻 Human Support" if t.is_assigned_to_human else "🤖 AI Support"
            lines.append(
                f"▪️ <b>Ticket #{t.id}</b>\n"
                f"   👤 User ID: <code>{t.user_id}</code>\n"
                f"   ⚙️ Routing: {assigned}\n"
                f"   ✏️ Reply: <code>/replyticket {t.id} &lt;message&gt;</code>"
            )
            lines.append("")

        await message.answer("\n".join(lines), parse_mode="HTML")
    except Exception:
        logger.exception("handle_tickets_list failed")
        await message.answer(MSG_ERROR_GENERIC)


@router.message(Command("replyticket"))
async def handle_reply_ticket(
    message: Message, support_service: SupportService, bot: Bot
) -> None:
    """Reply to a user support ticket and forward to user."""
    user = message.from_user
    if not user or not is_admin(user.id):
        return

    args = (message.text or "").split(maxsplit=2)
    if len(args) < 3 or not args[1].isdigit():
        await message.answer("⚠️ Usage: <code>/replyticket &lt;ticket_id&gt; &lt;message&gt;</code>", parse_mode="HTML")
        return

    ticket_id = int(args[1])
    reply_text = args[2]

    try:
        ticket = await support_service.get_ticket_with_messages(ticket_id)
        if not ticket:
            await message.answer(f"❌ Support ticket #{ticket_id} not found.")
            return

        if ticket.status.value != "open":
            await message.answer(f"❌ Ticket #{ticket_id} is already closed.")
            return

        # Add message to ticket history
        await support_service.add_message(ticket_id, "admin", reply_text)

        # Notify the user
        try:
            await bot.send_message(
                chat_id=ticket.user_id,
                text=(
                    f"👨‍💻 <b>Support Reply:</b>\n\n"
                    f"{reply_text}\n\n"
                    f"<i>You can reply to this message directly to continue support.</i>"
                ),
                parse_mode="HTML",
            )
            await message.answer(f"✅ Reply sent to ticket #{ticket_id}.")
        except Exception as notify_exc:
            logger.error("Failed to notify user for ticket %s | error=%s", ticket_id, notify_exc)
            await message.answer(f"❌ Reply logged in history, but failed to notify user on Telegram: {notify_exc}")

    except Exception:
        logger.exception("handle_reply_ticket failed | ticket_id=%s", ticket_id)
        await message.answer(MSG_ERROR_GENERIC)


@router.message(Command("closeticket"))
async def handle_close_ticket(
    message: Message, support_service: SupportService, bot: Bot
) -> None:
    """Close an open support ticket and notify user."""
    user = message.from_user
    if not user or not is_admin(user.id):
        return

    args = (message.text or "").split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("⚠️ Usage: <code>/closeticket &lt;ticket_id&gt;</code>", parse_mode="HTML")
        return

    ticket_id = int(args[1])

    try:
        ticket = await support_service.get_ticket_with_messages(ticket_id)
        if not ticket:
            await message.answer(f"❌ Ticket #{ticket_id} not found.")
            return

        await support_service.close_ticket(ticket_id)
        await message.answer(f"✅ Ticket #{ticket_id} has been closed.")

        # Notify the user
        try:
            await bot.send_message(
                chat_id=ticket.user_id,
                text=(
                    f"❌ <b>Support Ticket Closed</b>\n\n"
                    f"Your support ticket #{ticket_id} has been marked as resolved and closed. "
                    f"If you have further questions, you can open a new session with /support."
                ),
                parse_mode="HTML",
            )
        except Exception as notify_exc:
            logger.error("Failed to notify user of ticket closure %s | error=%s", ticket_id, notify_exc)

    except Exception:
        logger.exception("handle_close_ticket failed | ticket_id=%s", ticket_id)
        await message.answer(MSG_ERROR_GENERIC)


@router.message(Command("broadcast"))
async def handle_broadcast(
    message: Message, user_service: UserService, bot: Bot
) -> None:
    """Broadcast an announcement message to all registered users."""
    user = message.from_user
    if not user or not is_admin(user.id):
        return

    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ Usage: <code>/broadcast &lt;message&gt;</code>", parse_mode="HTML")
        return

    broadcast_text = args[1]

    try:
        users = await user_service.list_all_users()
        if not users:
            await message.answer("❌ No registered users found in the database.")
            return

        await message.answer(f"📢 Starting broadcast to {len(users)} users...")

        success_count = 0
        fail_count = 0

        for u in users:
            try:
                await bot.send_message(
                    chat_id=u.id,
                    text=f"📢 <b>Announcement</b>\n\n{broadcast_text}",
                    parse_mode="HTML",
                )
                success_count += 1
            except Exception as exc:
                logger.warning("Broadcast failed for user_id=%s | error=%s", u.id, exc)
                fail_count += 1

        await message.answer(
            f"✅ <b>Broadcast Completed!</b>\n\n"
            f"📈 Success: <code>{success_count}</code>\n"
            f"📉 Failed: <code>{fail_count}</code>",
            parse_mode="HTML",
        )

    except Exception:
        logger.exception("handle_broadcast failed")
        await message.answer(MSG_ERROR_GENERIC)


@router.message(Command("ban"))
async def handle_ban_user(
    message: Message, user_service: UserService
) -> None:
    """Ban a user from the platform."""
    user = message.from_user
    if not user or not is_admin(user.id):
        return

    args = (message.text or "").split(maxsplit=2)
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("⚠️ Usage: <code>/ban &lt;user_id&gt; &lt;reason&gt;</code>", parse_mode="HTML")
        return

    target_user_id = int(args[1])
    reason = args[2] if len(args) > 2 else "No reason provided."

    try:
        target_user = await user_service.get_user(target_user_id)
        if not target_user:
            await message.answer(f"❌ User <code>{target_user_id}</code> not found in the database.", parse_mode="HTML")
            return

        await user_service.ban_user(target_user_id, reason)
        await message.answer(f"🔴 User <code>{target_user_id}</code> has been <b>banned</b>.\n📝 Reason: <i>{reason}</i>", parse_mode="HTML")

    except Exception:
        logger.exception("handle_ban_user failed | target_user_id=%s", target_user_id)
        await message.answer(MSG_ERROR_GENERIC)


@router.message(Command("unban"))
async def handle_unban_user(
    message: Message, user_service: UserService
) -> None:
    """Unban a user from the platform."""
    user = message.from_user
    if not user or not is_admin(user.id):
        return

    args = (message.text or "").split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("⚠️ Usage: <code>/unban &lt;user_id&gt;</code>", parse_mode="HTML")
        return

    target_user_id = int(args[1])

    try:
        target_user = await user_service.get_user(target_user_id)
        if not target_user:
            await message.answer(f"❌ User <code>{target_user_id}</code> not found in the database.", parse_mode="HTML")
            return

        await user_service.unban_user(target_user_id)
        await message.answer(f"🟢 User <code>{target_user_id}</code> has been <b>unbanned</b>.", parse_mode="HTML")

    except Exception:
        logger.exception("handle_unban_user failed | target_user_id=%s", target_user_id)
        await message.answer(MSG_ERROR_GENERIC)


