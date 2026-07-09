"""
bot/keyboards/builders.py

Factory methods for building bot keyboards (Inline & Reply).
"""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Build the main menu inline keyboard with optional Admin Panel option."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛒 Browse Catalogue", callback_data="menu:catalogue")
    )
    builder.row(
        InlineKeyboardButton(text="📋 My Orders", callback_data="menu:orders"),
        InlineKeyboardButton(text="💬 AI Support", callback_data="menu:support"),
    )
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="⚙️ Admin Panel", callback_data="menu:admin")
        )
    return builder.as_markup()


def get_catalogue_keyboard(products: list) -> InlineKeyboardMarkup:
    """Build inline keyboard containing a list of products and a main menu button."""
    builder = InlineKeyboardBuilder()
    for product in products:
        # Each product gets a dedicated button routing to details
        builder.row(
            InlineKeyboardButton(
                text=f"{product.name} — {product.price_display}",
                callback_data=f"product_detail:{product.id}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu:main")
    )
    return builder.as_markup()


def get_product_detail_keyboard(product_id: int, price_display: str, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Build the product detail purchase inline keyboard with navigation."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=f"🛒 Buy Now ({price_display})", callback_data=f"buy:{product_id}")
    )
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="📁 Link PDF File", callback_data=f"prod_set_file:{product_id}")
        )
    builder.row(
        InlineKeyboardButton(text="⬅ Back to Catalogue", callback_data="menu:catalogue"),
        InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu:main"),
    )
    return builder.as_markup()


def get_order_checkout_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Build checkout instructions inline keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Submit Payment Proof", callback_data=f"pay_proof:{order_id}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Cancel Order", callback_data=f"cancel_order:{order_id}")
    )
    return builder.as_markup()


def get_support_menu_keyboard() -> ReplyKeyboardMarkup:
    """Build persistent reply keyboard for support options."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="👨‍💻 Speak to Human"))
    builder.row(KeyboardButton(text="❌ Exit Support"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Build the authorized admin control panel keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Pending Payments Queue", callback_data="admin_menu:payments")
    )
    builder.row(
        InlineKeyboardButton(text="🎫 Open Support Tickets", callback_data="admin_menu:tickets")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Send Broadcast message", callback_data="admin_menu:broadcast")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 User Main Menu", callback_data="menu:main")
    )
    return builder.as_markup()


def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    """Build a helper keyboard to return to the Admin Panel."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⚙️ Admin Panel", callback_data="menu:admin"),
        InlineKeyboardButton(text="🏠 User Menu", callback_data="menu:main"),
    )
    return builder.as_markup()


def get_generic_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Build standard main menu return button."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu:main")
    )
    return builder.as_markup()


def get_admin_review_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Build inline keyboard for admin verification queue messages."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📸 View Proof", callback_data=f"admin_proof:{order_id}")
    )
    builder.row(
        InlineKeyboardButton(text="✅ Approve", callback_data=f"admin_approve:{order_id}"),
        InlineKeyboardButton(text="❌ Reject", callback_data=f"admin_reject:{order_id}"),
    )
    return builder.as_markup()
