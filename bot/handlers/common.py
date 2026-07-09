"""
bot/handlers/common.py

Common bot command handlers.

Handlers:
  - /start  — Register/update user and send welcome message
  - /help   — List available commands
  - /ping   — Health check with latency display

Rules (from PROJECT_RULES.md — Rule 5):
  - Handlers receive updates and call services.
  - No business logic is permitted here.
  - No direct database access is permitted here.
"""

import time

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import settings
from core.constants import MSG_HELP_USER, MSG_HELP_ADMIN, MSG_PING, MSG_START
from core.logger import get_logger
from bot.keyboards import get_main_menu_keyboard
from services.user_service import UserService
from services.product_service import ProductService
from services.order_service import OrderService
from services.support_service import SupportService

logger = get_logger(__name__)

router = Router(name="common")


@router.message(Command("start"))
async def handle_start(message: Message, user_service: UserService) -> None:
    """
    Handle the /start command.

    Registers or updates the user in the database, then sends a
    personalised welcome message with the main menu keyboard.
    """
    tg_user = message.from_user
    if tg_user is None:
        return

    # Delegate to service — register new users or refresh existing ones
    user = await user_service.register_or_update(tg_user)

    logger.info(
        "User started bot | user_id=%s | username=%s",
        user.id,
        user.username,
    )

    is_admin = user.id in settings.admin_ids
    text = MSG_START.format(shop_name="TCP Shop", user_name=user.full_name)
    await message.answer(text, reply_markup=get_main_menu_keyboard(is_admin=is_admin))


@router.callback_query(F.data.startswith("menu:"))
async def handle_menu_callback(
    callback: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
    product_service: ProductService,
    order_service: OrderService,
    support_service: SupportService,
) -> None:
    """Handle menu inline button clicks by routing to corresponding handlers."""
    action = callback.data.split(":", 1)[1]
    await callback.answer()

    message = callback.message
    if not message:
        return
    # Map callback's user context using model_copy (pydantic frozen model safe)
    new_message = message.model_copy(update={"from_user": callback.from_user})

    if action == "catalogue":
        from bot.handlers.products import handle_products
        await handle_products(new_message, product_service)
    elif action == "orders":
        from bot.handlers.orders import handle_my_orders
        await handle_my_orders(new_message, order_service)
    elif action == "support":
        from bot.handlers.support import handle_support_start
        await handle_support_start(new_message, state, support_service)
    elif action == "main":
        is_admin = callback.from_user.id in settings.admin_ids
        text = MSG_START.format(shop_name="TCP Shop", user_name=callback.from_user.full_name or "User")
        try:
            await message.edit_text(text, reply_markup=get_main_menu_keyboard(is_admin=is_admin))
        except Exception:
            await message.answer(text, reply_markup=get_main_menu_keyboard(is_admin=is_admin))
    elif action == "admin":
        is_admin = callback.from_user.id in settings.admin_ids
        if not is_admin:
            return
        admin_text = "⚙️ <b>Admin Control Panel</b>\n\nSelect an option to manage the store:"
        from bot.keyboards import get_admin_panel_keyboard
        try:
            await message.edit_text(admin_text, parse_mode="HTML", reply_markup=get_admin_panel_keyboard())
        except Exception:
            await message.answer(admin_text, parse_mode="HTML", reply_markup=get_admin_panel_keyboard())



@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """
    Handle the /help command.

    Displays the list of available commands, customized by role.
    """
    user = message.from_user
    user_id = user.id if user else 0
    is_admin = user_id in settings.admin_ids

    logger.info(
        "User requested help | user_id=%s | is_admin=%s",
        user_id,
        is_admin,
    )

    text = MSG_HELP_USER
    if is_admin:
        text += "\n\n" + MSG_HELP_ADMIN

    await message.answer(text, parse_mode="HTML")



@router.message(Command("ping"))
async def handle_ping(message: Message) -> None:
    """
    Handle the /ping command.

    Measures round-trip latency by recording time before and after
    sending a temporary message, then editing it with the result.
    """
    start_time = time.monotonic()
    sent = await message.answer("🏓 Pinging...")
    latency_ms = round((time.monotonic() - start_time) * 1000)

    await sent.edit_text(MSG_PING.format(latency_ms=latency_ms))

    logger.info(
        "Ping handled | user_id=%s | latency_ms=%d",
        message.from_user.id if message.from_user else "unknown",
        latency_ms,
    )
