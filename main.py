"""
main.py

Application entry point.

Single responsibility: bootstrap and start the application.

All initialisation logic belongs in app.py.
This file must remain minimal and clean.

Usage:
    python main.py
"""

import asyncio
import sys

from app import create_application
from core.constants import APP_NAME
from core.logger import get_logger

logger = get_logger(__name__)


async def main() -> None:
    """Bootstrap and run the application."""
    application = await create_application()
    await application.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("%s stopped by user (KeyboardInterrupt).", APP_NAME)
        sys.exit(0)
    except Exception as exc:
        logger.critical("Fatal error during startup: %s", exc, exc_info=True)
        sys.exit(1)
