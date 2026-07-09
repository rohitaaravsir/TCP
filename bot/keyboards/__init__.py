"""
bot/keyboards

Keyboards package initialization.
"""

from bot.keyboards.builders import (
    get_main_menu_keyboard,
    get_catalogue_keyboard,
    get_product_detail_keyboard,
    get_order_checkout_keyboard,
    get_support_menu_keyboard,
    get_admin_panel_keyboard,
    get_back_to_admin_keyboard,
    get_generic_main_menu_keyboard,
    get_admin_review_keyboard,
)

__all__ = [
    "get_main_menu_keyboard",
    "get_catalogue_keyboard",
    "get_product_detail_keyboard",
    "get_order_checkout_keyboard",
    "get_support_menu_keyboard",
    "get_admin_panel_keyboard",
    "get_back_to_admin_keyboard",
    "get_generic_main_menu_keyboard",
    "get_admin_review_keyboard",
]
