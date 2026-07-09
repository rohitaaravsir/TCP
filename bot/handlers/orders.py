"""
bot/handlers/orders.py

Order management handlers.

User commands:
  - /order <product_id>  — Place a new order
  - /myorders            — View order history
  - /orderstatus <id>    — Check status of a specific order
  - /cancelorder <id>    — Cancel a pending order

Rules (from PROJECT_RULES.md — Rule 5):
  - Handlers receive updates and call services.
  - No business logic is permitted here.
  - No direct database access is permitted here.
"""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from core.constants import MSG_ERROR_GENERIC
from schemas.order import OrderSummarySchema
from services.order_service import OrderService, OrderServiceError

logger = logging.getLogger(__name__)

router = Router(name="orders")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_order_summary(order: OrderSummarySchema, index: int) -> str:
    """Format a single order summary line for /myorders."""
    return (
        f"<b>#{index}. Order {order.id}</b>\n"
        f"   📦 Product ID: <code>{order.product_id}</code>\n"
        f"   💰 Amount: {order.amount_display}\n"
        f"   🔖 Status: {order.status_display}\n"
        f"   🕐 Placed: {order.created_at.strftime('%d %b %Y, %H:%M')} UTC"
    )


def _parse_int_arg(text: str, command_word: str) -> int | None:
    """
    Extract a single integer argument from a command message.

    Returns None if the argument is missing or not a digit.
    """
    parts = text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        return None
    return int(parts[1])


# ---------------------------------------------------------------------------
# User handlers
# ---------------------------------------------------------------------------

@router.message(Command("order"))
async def handle_place_order(
    message: Message, order_service: OrderService
) -> None:
    """
    Handle /order <product_id> — place a new order.

    Usage: /order 3
    Creates a pending order for the given product.
    """
    user = message.from_user
    if user is None:
        return

    product_id = _parse_int_arg(message.text or "", "/order")
    if product_id is None:
        await message.answer(
            "⚠️ Usage: <code>/order &lt;product_id&gt;</code>\n\n"
            "Example: <code>/order 3</code>\n\n"
            "Use /products to browse the catalogue.",
            parse_mode="HTML",
        )
        return

    try:
        order = await order_service.place_order(
            user_id=user.id,
            product_id=product_id,
        )
        await message.answer(
            f"✅ <b>Order Placed!</b>\n\n"
            f"🆔 Order ID: <code>{order.id}</code>\n"
            f"💰 Amount: {order.amount_display}\n"
            f"🔖 Status: {order.status_display}\n\n"
            f"📸 To complete your purchase, send your payment screenshot.\n"
            f"Your order ID is <code>{order.id}</code> — keep it safe.",
            parse_mode="HTML",
        )
        logger.info(
            "Order placed via handler | user_id=%s | product_id=%s | order_id=%s",
            user.id, product_id, order.id,
        )
    except OrderServiceError as exc:
        await message.answer(f"❌ {exc}")
    except Exception:
        logger.exception("handle_place_order failed | user_id=%s", user.id)
        await message.answer(MSG_ERROR_GENERIC)


@router.message(Command("myorders"))
async def handle_my_orders(
    message: Message, order_service: OrderService
) -> None:
    """
    Handle /myorders — display the user's recent order history.

    Shows up to 10 most recent orders with status and amount.
    """
    user = message.from_user
    if user is None:
        return

    try:
        orders = await order_service.list_user_orders(user.id)

        if not orders:
            await message.answer(
                "📋 <b>My Orders</b>\n\n"
                "You have not placed any orders yet.\n\n"
                "Browse our catalogue with /products.",
                parse_mode="HTML",
            )
            return

        lines = ["📋 <b>My Orders</b> (last 10)\n"]
        for i, order in enumerate(orders, start=1):
            lines.append(_format_order_summary(order, i))
            lines.append("")  # blank line between orders

        lines.append("💡 Use <code>/orderstatus &lt;id&gt;</code> for full details.")
        await message.answer("\n".join(lines), parse_mode="HTML")

        logger.info(
            "Order history displayed | user_id=%s | count=%d",
            user.id, len(orders),
        )
    except Exception:
        logger.exception("handle_my_orders failed | user_id=%s", user.id)
        await message.answer(MSG_ERROR_GENERIC)


@router.message(Command("orderstatus"))
async def handle_order_status(
    message: Message, order_service: OrderService
) -> None:
    """
    Handle /orderstatus <id> — show full details of a specific order.

    Usage: /orderstatus 12
    """
    user = message.from_user
    if user is None:
        return

    order_id = _parse_int_arg(message.text or "", "/orderstatus")
    if order_id is None:
        await message.answer(
            "⚠️ Usage: <code>/orderstatus &lt;order_id&gt;</code>\n\n"
            "Example: <code>/orderstatus 12</code>",
            parse_mode="HTML",
        )
        return

    try:
        order = await order_service.get_order(order_id)

        if order is None or order.user_id != user.id:
            # Do not reveal whether the order exists for other users
            await message.answer(
                f"❌ Order <code>{order_id}</code> not found.\n\n"
                f"Use /myorders to view your orders.",
                parse_mode="HTML",
            )
            return

        await message.answer(
            f"📦 <b>Order #{order.id}</b>\n\n"
            f"📂 Product ID: <code>{order.product_id}</code>\n"
            f"💰 Amount: {order.amount_display}\n"
            f"🔖 Status: {order.status_display}\n"
            f"🕐 Placed: {order.created_at.strftime('%d %b %Y, %H:%M')} UTC\n"
            f"🔄 Updated: {order.updated_at.strftime('%d %b %Y, %H:%M')} UTC",
            parse_mode="HTML",
        )
    except Exception:
        logger.exception("handle_order_status failed | user_id=%s | order_id=%s", user.id, order_id)
        await message.answer(MSG_ERROR_GENERIC)


@router.message(Command("cancelorder"))
async def handle_cancel_order(
    message: Message, order_service: OrderService
) -> None:
    """
    Handle /cancelorder <id> — cancel a pending order.

    Only orders in 'pending' status can be cancelled.
    Usage: /cancelorder 12
    """
    user = message.from_user
    if user is None:
        return

    order_id = _parse_int_arg(message.text or "", "/cancelorder")
    if order_id is None:
        await message.answer(
            "⚠️ Usage: <code>/cancelorder &lt;order_id&gt;</code>\n\n"
            "Example: <code>/cancelorder 12</code>",
            parse_mode="HTML",
        )
        return

    try:
        order = await order_service.cancel_order(
            order_id=order_id,
            user_id=user.id,
        )
        await message.answer(
            f"✅ Order <code>{order.id}</code> has been <b>cancelled</b>.\n\n"
            f"If you paid, please contact support.",
            parse_mode="HTML",
        )
        logger.info(
            "Order cancelled via handler | user_id=%s | order_id=%s",
            user.id, order_id,
        )
    except OrderServiceError as exc:
        await message.answer(f"❌ {exc}")
    except Exception:
        logger.exception("handle_cancel_order failed | user_id=%s | order_id=%s", user.id, order_id)
        await message.answer(MSG_ERROR_GENERIC)
