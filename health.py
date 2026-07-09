"""
health.py

Lightweight HTTP health check server.

Required by Render and Koyeb to determine service liveness.

Endpoint:
  GET /health → 200 {"status": "ok", "version": "1.0.0"}
  GET /        → 200 {"status": "ok"}  (alias)

Usage:
    from health import build_health_app
    app = build_health_app()
    # app is an aiohttp.web.Application, attach to a runner in app.py
"""

import json

from aiohttp import web

from core.constants import APP_VERSION, HEALTH_STATUS_OK
from core.database import db
from core.logger import get_logger

logger = get_logger(__name__)


async def handle_health(request: web.Request) -> web.Response:
    """
    Health check handler.

    Returns the current status of the service including:
    - Application version
    - Database connectivity status
    """
    db_status = "connected" if db.is_connected else "disconnected"

    payload = {
        "status": HEALTH_STATUS_OK,
        "version": APP_VERSION,
        "database": db_status,
    }

    return web.Response(
        status=200,
        content_type="application/json",
        body=json.dumps(payload),
    )


async def handle_root(request: web.Request) -> web.Response:
    """Root path alias for health check."""
    return web.Response(
        status=200,
        content_type="application/json",
        body=json.dumps({"status": HEALTH_STATUS_OK}),
    )


def build_health_app() -> web.Application:
    """
    Build and return the aiohttp health check application.

    Returns:
        Configured aiohttp Application with health routes.
    """
    app = web.Application()
    app.router.add_get("/health", handle_health)
    app.router.add_get("/", handle_root)
    logger.info("Health check app built | routes=[GET /, GET /health]")
    return app
