"""
core/constants.py

Centralised application-level constants.

Rules:
  - No logic here — values only.
  - No secrets — use config/settings.py for those.
  - Group related constants in named blocks for readability.
"""

# ------------------------------------------------------------------
# Application
# ------------------------------------------------------------------

APP_NAME = "Telegram Commerce Platform"
APP_SHORT_NAME = "TCP"
APP_VERSION = "1.0.0"

# ------------------------------------------------------------------
# Bot Messages (base responses for handlers)
# ------------------------------------------------------------------

MSG_START = (
    "👋 Welcome to {shop_name}, {user_name}!\n\n"
    "Use the menu below to browse products, track orders, or get support."
)

MSG_HELP_USER = (
    "ℹ️ <b>Available Commands</b>\n\n"
    "🛒 <b>General:</b>\n"
    "/start - Show the main menu / welcome\n"
    "/products - Browse the product catalogue\n"
    "/order &lt;id&gt; - Place an order for a product\n"
    "/myorders - View your order history\n"
    "/orderstatus &lt;id&gt; - Check order status\n"
    "/cancelorder &lt;id&gt; - Cancel a pending order\n"
    "/pay &lt;order_id&gt; - Submit payment screenshot proof\n\n"
    "💬 <b>Support:</b>\n"
    "/support - Connect to customer support chat (AI)\n"
    "  • <code>/human</code> - Request a human agent during support\n"
    "  • <code>/exit</code> - Exit active support session\n\n"
    "ℹ️ <b>Utility:</b>\n"
    "/help - Show this help message\n"
    "/ping - Check bot latency"
)

MSG_HELP_ADMIN = (
    "⚙️ <b>Admin Commands:</b>\n\n"
    "💳 <b>Payments Queue:</b>\n"
    "/pendingpayments - List all pending payments\n"
    "/proof_&lt;order_id&gt; - View payment proof details\n"
    "/approvepayment &lt;order_id&gt; - Approve payment and confirm order\n"
    "/rejectpayment &lt;order_id&gt; &lt;reason&gt; - Reject payment with reason\n\n"
    "🎫 <b>Support Tickets:</b>\n"
    "/tickets - List all open support tickets\n"
    "/replyticket &lt;ticket_id&gt; &lt;message&gt; - Reply to user support ticket\n"
    "/closeticket &lt;ticket_id&gt; - Close support ticket\n\n"
    "📢 <b>Marketing & System:</b>\n"
    "/broadcast &lt;message&gt; - Send announcement to all users\n"
    "/toggleproduct &lt;product_id&gt; - Activate/deactivate a product\n"
    "/setproductfile &lt;product_id&gt; - Link PDF file (or click button in details)\n\n"
    "👤 <b>User Management & Security:</b>\n"
    "/ban &lt;user_id&gt; &lt;reason&gt; - Ban a user from the platform\n"
    "/unban &lt;user_id&gt; - Remove ban restriction from a user"
)


MSG_PING = "🏓 Pong! Latency: {latency_ms}ms"

MSG_ERROR_GENERIC = (
    "⚠️ Something went wrong. Please try again later.\n"
    "If the issue persists, contact support."
)

MSG_MAINTENANCE = "🔧 The bot is currently under maintenance. Please try again later."

# ------------------------------------------------------------------
# Timeouts & Limits
# ------------------------------------------------------------------

# Default request timeout in seconds
DEFAULT_TIMEOUT_SECONDS = 30

# Maximum file size for uploads (10 MB)
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

# Maximum message length (Telegram limit)
TELEGRAM_MAX_MESSAGE_LENGTH = 4096

# ------------------------------------------------------------------
# Health Check
# ------------------------------------------------------------------

HEALTH_STATUS_OK = "ok"
HEALTH_STATUS_DEGRADED = "degraded"
HEALTH_STATUS_DOWN = "down"

# ------------------------------------------------------------------
# Log Event Names (structured logging keys)
# ------------------------------------------------------------------

LOG_EVENT_BOT_STARTED = "bot.started"
LOG_EVENT_BOT_STOPPED = "bot.stopped"
LOG_EVENT_DB_CONNECTED = "database.connected"
LOG_EVENT_DB_DISCONNECTED = "database.disconnected"
LOG_EVENT_DB_CONNECTION_FAILED = "database.connection_failed"
LOG_EVENT_HEALTH_CHECK_STARTED = "health.server.started"
LOG_EVENT_UNHANDLED_EXCEPTION = "exception.unhandled"
