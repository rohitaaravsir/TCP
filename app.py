"""
app.py

Application bootstrap module.

Responsibilities:
  - Initialise the logger
  - Load and validate configuration
  - Connect to the database
  - Create the Bot and Dispatcher
  - Start the health check server
  - Orchestrate graceful startup and shutdown

main.py calls create_application() and start().

This separation ensures:
  - main.py stays clean (single responsibility: entry point)
  - app.py is fully testable without running main.py
  - Future: app.py can be wrapped by a web framework or task runner
"""

from __future__ import annotations

import asyncio

from aiohttp import web

from bot.loader import create_bot, create_dispatcher
from bot.middlewares.ban_check import BanCheckMiddleware
from config import settings
from core.constants import (
    APP_NAME,
    APP_VERSION,
    LOG_EVENT_BOT_STARTED,
    LOG_EVENT_BOT_STOPPED,
)
from core.database import db
from core.exceptions import DatabaseConnectionError
from core.logger import configure_logging, get_logger
from health import build_health_app
from repositories.user_repository import UserRepository
from repositories.product_repository import ProductRepository
from repositories.order_repository import OrderRepository
from repositories.utr_repository import UTRRepository
from services.user_service import UserService
from services.product_service import ProductService
from services.order_service import OrderService
from services.ocr_service import OCRService
from services.ai_provider_service import GeminiProvider
from services.support_service import SupportService
from repositories.support_repository import SupportRepository

logger = get_logger(__name__)


class Application:
    """
    Central application object.

    Holds references to all top-level components and orchestrates
    the startup and shutdown lifecycle.
    """

    def __init__(self) -> None:
        self.bot = None
        self.dispatcher = None
        self._health_runner: web.AppRunner | None = None
        self.user_service: UserService | None = None
        self.product_service: ProductService | None = None
        self.order_service: OrderService | None = None
        self.ocr_service: OCRService | None = None
        self.utr_repo: UTRRepository | None = None
        self.support_service: SupportService | None = None
        self.ai_provider: GeminiProvider | None = None

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    async def initialise(self) -> None:
        """
        Initialise all application components.

        Order:
          1. Logging (must come first — everything else logs)
          2. Configuration is already loaded by pydantic-settings at import
          3. Database
          4. Bot + Dispatcher
          5. Health server
        """
        # 1. Logging
        configure_logging(
            log_level=settings.log_level,
            log_dir=settings.log_dir,
        )

        logger.info("=" * 60)
        logger.info("Starting %s v%s", APP_NAME, APP_VERSION)
        logger.info("Environment: %s", settings.app_env)
        logger.info("=" * 60)

        # 2. Database
        await self._init_database()

        # 3. Services
        self._init_services()

        # 4. Bot + Dispatcher
        self.bot = create_bot(settings.telegram_bot_token)
        self.dispatcher = create_dispatcher()

        # 5. Register middlewares
        self.dispatcher.message.middleware(BanCheckMiddleware(self.user_service))

        # 6. Inject services into dispatcher workflow data
        self.dispatcher["user_service"] = self.user_service
        self.dispatcher["product_service"] = self.product_service
        self.dispatcher["order_service"] = self.order_service
        self.dispatcher["ocr_service"] = self.ocr_service
        self.dispatcher["utr_repo"] = self.utr_repo
        self.dispatcher["support_service"] = self.support_service
        self.dispatcher["ai_provider"] = self.ai_provider

        logger.info("Application initialised successfully.")

    async def _init_database(self) -> None:
        """Connect to Supabase. Uses connect_no_verify before schema verification."""
        try:
            await db.connect_no_verify(
                url=settings.supabase_url,
                key=settings.supabase_service_key,
            )
        except DatabaseConnectionError as exc:
            logger.critical("Database initialisation failed: %s", exc.message)
            raise

    def _init_services(self) -> None:
        """Instantiate repositories and services after DB is connected."""
        user_repo = UserRepository(db.client)
        self.user_service = UserService(user_repo)

        product_repo = ProductRepository(db.client)
        self.product_service = ProductService(product_repo)

        order_repo = OrderRepository(db.client)
        self.order_service = OrderService(order_repo, product_repo)

        # UTR fraud-prevention repository
        self.utr_repo = UTRRepository(db.client)

        # OCR service — receiver name and UPI ID come from .env
        self.ocr_service = OCRService(
            receiver_name=settings.ocr_receiver_name,
            upi_id=settings.ocr_upi_id,
        )

        support_repo = SupportRepository(db.client)
        self.support_service = SupportService(support_repo)
        self.ai_provider = GeminiProvider()

        logger.info(
            "Services initialised | ocr_receiver='%s' | ocr_upi='%s'",
            settings.ocr_receiver_name or "(not set)",
            settings.ocr_upi_id or "(not set)",
        )

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """
        Start all application services.

        1. Start the health check HTTP server (non-blocking background task)
        2. Start the Telegram bot polling (blocking — runs until shutdown)
        """
        await self._start_health_server()
        await self._start_polling()

    async def _start_health_server(self) -> None:
        """Start the aiohttp health check server as a background task."""
        app = build_health_app()
        self._health_runner = web.AppRunner(app)
        await self._health_runner.setup()
        site = web.TCPSite(
            self._health_runner,
            host=settings.health_host,
            port=settings.health_port,
        )
        await site.start()
        logger.info(
            "Health server started | host=%s | port=%d",
            settings.health_host,
            settings.health_port,
        )

    async def _start_polling(self) -> None:
        """Start aiogram long-polling."""
        logger.info("Bot polling started | event=%s", LOG_EVENT_BOT_STARTED)
        try:
            await self.dispatcher.start_polling(
                self.bot,
                allowed_updates=self.dispatcher.resolve_used_update_types(),
            )
        finally:
            await self.shutdown()

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    async def shutdown(self) -> None:
        """
        Graceful shutdown sequence.

        Order (reverse of startup):
          1. Stop health server
          2. Close bot session
          3. Disconnect database
        """
        logger.info("Shutting down %s...", APP_NAME)

        if self._health_runner:
            await self._health_runner.cleanup()
            logger.info("Health server stopped.")

        if self.bot:
            await self.bot.session.close()
            logger.info("Bot session closed | event=%s", LOG_EVENT_BOT_STOPPED)

        await db.disconnect()
        logger.info("Shutdown complete.")


# ------------------------------------------------------------------
# Factory
# ------------------------------------------------------------------


async def create_application() -> Application:
    """
    Create and initialise the application.

    Returns:
        A fully initialised Application instance ready to start.
    """
    application = Application()
    await application.initialise()
    return application
