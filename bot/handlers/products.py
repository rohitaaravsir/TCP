"""
bot/handlers/products.py

Product catalogue and admin command handlers.

Public commands (any user):
  - /products  — Browse the active product catalogue

Admin commands (admin users only — validated via ADMIN_IDS in settings):
  - /addproduct   — Add a new product (guided conversation via FSM)
  - /toggleproduct <id> — Activate or deactivate a product by ID

Rules (from PROJECT_RULES.md — Rule 5):
  - Handlers receive updates and call services.
  - No business logic is permitted here.
  - No direct database access is permitted here.
"""

from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from config import settings
from core.constants import MSG_ERROR_GENERIC
from bot.keyboards import get_product_detail_keyboard, get_catalogue_keyboard
from services.product_service import ProductService
from services.order_service import OrderService

logger = logging.getLogger(__name__)

router = Router(name="products")

# Maximum products shown per catalogue message to stay under Telegram limit
_CATALOGUE_PAGE_SIZE = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_catalogue(products) -> str:
    """Format a list of ProductListItemSchema into a readable message."""
    if not products:
        return (
            "🛒 <b>Product Catalogue</b>\n\n"
            "No products are currently available.\n"
            "Check back soon! 🔜"
        )

    lines = ["🛒 <b>Product Catalogue</b>\n"]
    for p in products:
        lines.append(
            f"<b>{p.name}</b> — {p.price_display}\n"
            f"  📂 {p.category} | /product_{p.id}"
        )
    lines.append("\n💡 Send /product_&lt;id&gt; to view details.")
    return "\n".join(lines)


def _format_product_detail(product) -> str:
    """Format a full ProductSchema into a detail message."""
    status = "✅ Available" if product.is_active else "❌ Unavailable"
    desc = product.description or "No description provided."
    return (
        f"🏷️ <b>{product.name}</b>\n\n"
        f"📝 {desc}\n\n"
        f"💰 Price: <b>{product.price_display}</b>\n"
        f"📂 Category: {product.category}\n"
        f"🔖 Status: {status}\n"
        f"🆔 ID: <code>{product.id}</code>"
    )


# ---------------------------------------------------------------------------
# Public handlers
# ---------------------------------------------------------------------------

@router.message(Command("products"))
async def handle_products(message: Message, product_service: ProductService) -> None:
    """
    Handle /products — display the active product catalogue.

    Lists all currently active products with name, price, and a
    deep-link command (/product_<id>) for detailed views.
    """
    try:
        products = await product_service.get_catalogue()
        text = "🛒 <b>Product Catalogue</b>\n\nSelect a product to view its details:"
        try:
            await message.edit_text(text, parse_mode="HTML", reply_markup=get_catalogue_keyboard(products[:_CATALOGUE_PAGE_SIZE]))
        except Exception:
            await message.answer(text, parse_mode="HTML", reply_markup=get_catalogue_keyboard(products[:_CATALOGUE_PAGE_SIZE]))

        logger.info(
            "Catalogue displayed | user_id=%s | count=%d",
            message.from_user.id if message.from_user else "unknown",
            len(products),
        )
    except Exception:
        logger.exception("handle_products failed")
        await message.answer(MSG_ERROR_GENERIC)


@router.message(Command("product"))
@router.message(F.text.startswith("/product_"))
async def handle_product_detail_by_command(
    message: Message, product_service: ProductService
) -> None:
    """
    Handle /product_<id> deep-link commands.

    Example: /product_3 → shows full details for product ID 3.
    """
    # Extract the product ID from the command text (e.g. '/product_3')
    text = message.text or ""
    if text.startswith("/product_"):
        text = text.replace("/product_", "/product ", 1)

    parts = text.strip().split()

    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer(
            "⚠️ Invalid product link.\n\n"
            "Use /products to browse the catalogue."
        )
        return

    product_id = int(parts[1])

    try:
        product = await product_service.get_product(product_id)

        if product is None or not product.is_active:
            await message.answer(
                "❌ Product not found or no longer available.\n\n"
                "Use /products to browse the current catalogue."
            )
            return

        await message.answer(
            _format_product_detail(product),
            parse_mode="HTML",
            reply_markup=get_product_detail_keyboard(product.id, product.price_display),
        )
        logger.info(
            "Product detail viewed | user_id=%s | product_id=%s",
            message.from_user.id if message.from_user else "unknown",
            product_id,
        )
    except Exception:
        logger.exception("handle_product_detail failed | product_id=%s", product_id)
        await message.answer(MSG_ERROR_GENERIC)


@router.callback_query(F.data.startswith("buy:"))
async def handle_buy_callback(
    callback: CallbackQuery,
    order_service: OrderService,
) -> None:
    """Handle click on Buy Now inline button by initiating order creation."""
    product_id = int(callback.data.split(":", 1)[1])
    await callback.answer()

    message = callback.message
    if not message:
        return
    new_message = message.model_copy(update={"from_user": callback.from_user, "text": f"/order {product_id}"})

    from bot.handlers.orders import handle_place_order
    await handle_place_order(new_message, order_service)


# ---------------------------------------------------------------------------
# Admin handlers
# ---------------------------------------------------------------------------

@router.message(Command("toggleproduct"))
async def handle_toggle_product(
    message: Message, product_service: ProductService
) -> None:
    """
    Handle /toggleproduct <id> — activate or deactivate a product.

    Usage: /toggleproduct 3
    Only works when called with a valid numeric product ID by an admin.
    """
    user = message.from_user
    if not user or user.id not in settings.admin_ids:
        return  # Silently ignore unauthorized requests

    args = (message.text or "").split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer(
            "⚠️ Usage: <code>/toggleproduct &lt;product_id&gt;</code>",
            parse_mode="HTML",
        )
        return

    product_id = int(args[1])

    try:
        product = await product_service.get_product(product_id)
        if product is None:
            await message.answer(f"❌ Product <code>{product_id}</code> not found.", parse_mode="HTML")
            return

        if product.is_active:
            updated = await product_service.deactivate_product(product_id)
            await message.answer(
                f"🔴 Product <b>{updated.name}</b> (<code>{product_id}</code>) has been "
                f"<b>deactivated</b> and hidden from the catalogue.",
                parse_mode="HTML",
            )
        else:
            updated = await product_service.activate_product(product_id)
            await message.answer(
                f"🟢 Product <b>{updated.name}</b> (<code>{product_id}</code>) has been "
                f"<b>activated</b> and is now visible in the catalogue.",
                parse_mode="HTML",
            )

        logger.info(
            "Product toggled | admin_id=%s | product_id=%s | is_active=%s",
            message.from_user.id if message.from_user else "unknown",
            product_id,
            updated.is_active,
        )
    except Exception:
        logger.exception("handle_toggle_product failed | product_id=%s", product_id)
        await message.answer(MSG_ERROR_GENERIC)


@router.callback_query(F.data.startswith("product_detail:"))
async def handle_product_detail_callback(
    callback: CallbackQuery,
    product_service: ProductService,
) -> None:
    """Handle product details selection from the catalogue list."""
    product_id = int(callback.data.split(":", 1)[1])
    await callback.answer()

    message = callback.message
    if not message:
        return
    new_message = message.model_copy(update={"from_user": callback.from_user, "text": f"/product {product_id}"})
    await handle_product_detail_by_command(new_message, product_service)
