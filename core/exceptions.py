"""
core/exceptions.py

Custom application exceptions for the Telegram Commerce Platform.

Exception Hierarchy:

    TCPBaseException
    ├── ConfigurationError
    ├── DatabaseError
    │   ├── DatabaseConnectionError
    │   └── DatabaseQueryError
    ├── BotError
    │   └── HandlerError
    ├── ServiceError
    │   ├── ValidationError
    │   └── NotFoundError
    └── StorageError

Rules:
  - All custom exceptions inherit from TCPBaseException.
  - Always include a human-readable message.
  - Never swallow exceptions silently — log before raising.
"""


# ------------------------------------------------------------------
# Base
# ------------------------------------------------------------------


class TCPBaseException(Exception):
    """Root exception for all TCP application errors."""

    def __init__(self, message: str = "An unexpected error occurred.") -> None:
        self.message = message
        super().__init__(self.message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r})"


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------


class ConfigurationError(TCPBaseException):
    """Raised when the application configuration is invalid or incomplete."""


# ------------------------------------------------------------------
# Database
# ------------------------------------------------------------------


class DatabaseError(TCPBaseException):
    """Base class for all database-related errors."""


class DatabaseConnectionError(DatabaseError):
    """Raised when the application cannot connect to Supabase."""

    def __init__(self, message: str = "Failed to connect to the database.") -> None:
        super().__init__(message)


class DatabaseQueryError(DatabaseError):
    """Raised when a database query fails."""

    def __init__(self, message: str = "Database query failed.") -> None:
        super().__init__(message)


# ------------------------------------------------------------------
# Bot / Handler
# ------------------------------------------------------------------


class BotError(TCPBaseException):
    """Base class for Telegram bot errors."""


class HandlerError(BotError):
    """Raised when an error occurs inside a Telegram handler."""


# ------------------------------------------------------------------
# Service Layer
# ------------------------------------------------------------------


class ServiceError(TCPBaseException):
    """Base class for business service errors."""


class ValidationError(ServiceError):
    """Raised when input validation fails in a service."""

    def __init__(self, message: str = "Validation failed.", field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class NotFoundError(ServiceError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str = "Resource", identifier: str | None = None) -> None:
        message = f"{resource} not found."
        if identifier:
            message = f"{resource} '{identifier}' not found."
        super().__init__(message)


# ------------------------------------------------------------------
# Storage
# ------------------------------------------------------------------


class StorageError(TCPBaseException):
    """Raised when a file storage operation fails."""

    def __init__(self, message: str = "Storage operation failed.") -> None:
        super().__init__(message)
