"""
bot/loader.py

Bot and Dispatcher factory.

Responsibilities:
  - Create the aiogram Bot instance
  - Create the aiogram Dispatcher instance
  - Register all handler routers
  - This is the ONLY place where Bot and Dispatcher are instantiated

Rules:
  - No business logic here
  - No direct database access here
  - Handlers are registered via include_router()

Usage:
    from bot.loader import create_bot, create_dispatcher
    bot = create_bot(token)
    dp = create_dispatcher()
"""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import common as common_handlers
from bot.handlers import products as product_handlers
from bot.handlers import orders as order_handlers
from bot.handlers import payment as payment_handlers
from bot.handlers import admin as admin_handlers
from bot.handlers import support as support_handlers
from core.logger import get_logger

logger = get_logger(__name__)


def create_bot(token: str) -> Bot:
    """
    Create and return a configured aiogram Bot instance.

    Args:
        token: Telegram Bot API token.

    Returns:
        Configured Bot instance with HTML parse mode as default.
    """
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    logger.info("Telegram Bot instance created.")
    return bot


def create_dispatcher() -> Dispatcher:
    """
    Create and return a configured aiogram Dispatcher instance.

    All handler routers are registered here.
    Storage uses MemoryStorage for Sprint 0; replace with
    RedisStorage or similar for production state persistence.

    Returns:
        Configured Dispatcher with all routers registered.
    """
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # --- Register routers ---
    # Order matters: more specific routers should be registered first.
    dp.include_router(admin_handlers.router)
    dp.include_router(payment_handlers.router)
    dp.include_router(support_handlers.router)
    dp.include_router(order_handlers.router)
    dp.include_router(product_handlers.router)
    dp.include_router(common_handlers.router)

    logger.info("Dispatcher created | routers=6")
    return dp
