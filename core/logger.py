"""
core/logger.py

Application-wide structured logger factory.

Features:
  - Console handler (StreamHandler) with coloured level names in dev
  - Rotating file handler — never fills disk
  - Log format includes timestamp, level, module, and message
  - Single get_logger() factory used by every module

Usage:
    from core.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Bot started", extra={"event": "bot.started"})
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_MAX_BYTES = 10 * 1024 * 1024   # 10 MB per log file
_BACKUP_COUNT = 5                # keep 5 rotated files


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _get_log_level(level_str: str) -> int:
    """Convert a level string to a logging level integer."""
    level = logging.getLevelName(level_str.upper())
    if not isinstance(level, int):
        return logging.INFO
    return level


def _build_formatter() -> logging.Formatter:
    return logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)


def _build_console_handler(level: int) -> logging.StreamHandler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(_build_formatter())
    return handler


def _build_file_handler(log_dir: str, level: int) -> RotatingFileHandler:
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "app.log")
    handler = RotatingFileHandler(
        filename=log_path,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(_build_formatter())
    return handler


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def configure_logging(log_level: str = "INFO", log_dir: str = "logs") -> None:
    """
    Configure the root logger for the entire application.

    Call this once during application startup (in app.py) before
    any other module writes log messages.

    Args:
        log_level: One of DEBUG | INFO | WARNING | ERROR | CRITICAL
        log_dir:   Directory where rotating log files are stored.
    """
    level = _get_log_level(log_level)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Prevent duplicate handlers when called more than once
    if root_logger.handlers:
        root_logger.handlers.clear()

    root_logger.addHandler(_build_console_handler(level))
    root_logger.addHandler(_build_file_handler(log_dir, level))

    # Suppress overly verbose third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.WARNING)

    root_logger.info(
        "Logging configured | level=%s | log_dir=%s",
        log_level.upper(),
        log_dir,
    )


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.

    Args:
        name: Typically __name__ of the calling module.

    Returns:
        A configured logging.Logger instance.
    """
    return logging.getLogger(name)
