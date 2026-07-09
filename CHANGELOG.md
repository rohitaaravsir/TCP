# Changelog

All notable changes to the Telegram Commerce Platform are documented here.

Format: [Semantic Versioning](https://semver.org)

---

## [1.0.0] — Sprint 0 — 2026-07-09

### Added

**Project Foundation**

- Complete modular folder structure following clean architecture principles
- Virtual environment support with `requirements.txt`
- `.env.example` with all required and optional environment variables
- `.gitignore` for Python, venv, secrets, logs, and storage

**Configuration (`config/`)**
- `Settings` class using `pydantic-settings` — typed, validated, fails fast on missing vars
- Feature flags: `FEATURE_AI_ENABLED`, `FEATURE_OCR_ENABLED`, `FEATURE_SUPPORT_ENABLED`
- Convenience properties: `is_production`, `is_development`

**Core Infrastructure (`core/`)**
- `logger.py` — structured logger with rotating file + console handlers
- `database.py` — Supabase async client wrapper with singleton pattern
- `constants.py` — centralised application constants and log event names
- `exceptions.py` — custom exception hierarchy (`TCPBaseException` root)

**Application Bootstrap**
- `app.py` — full application lifecycle: initialise → start → shutdown
- `main.py` — minimal entry point: bootstrap only
- `health.py` — aiohttp HTTP server: `GET /health`, `GET /`

**Bot Layer (`bot/`)**
- `loader.py` — Bot + Dispatcher factory (aiogram 3.x)
- `handlers/common.py` — `/start`, `/help`, `/ping` handlers
- Empty architecture folders: `middlewares/`, `filters/`, `keyboards/`, `states/`

**Architecture Folders (empty, ready for future sprints)**
- `services/` — business logic services
- `repositories/` — Repository Pattern for database access
- `schemas/` — Pydantic request/response models
- `interfaces/` — abstract provider interfaces
- `events/` — event-driven architecture
- `utils/` — reusable helper utilities
- `storage/` — temporary file storage

**Tests**
- `tests/unit/test_config.py` — 9 unit tests for Settings validation
- `tests/unit/` and `tests/integration/` — structured test directories

**Documentation**
- `README.md` — project overview, quick-start, commands, sprint status
- `CHANGELOG.md` — this file
- `ARCHITECTURE_MAP.md` — module diagram and dependency map
- `.memory/sprint_0.md` — sprint state log

## [1.1.0] — Sprint 1 — User Management — 2026-07-09

### Added
- Supabase `users` table schema
- `UserSchema`, `UserCreateSchema`, and `UserUpdateSchema`
- `UserRepository` (get, create, upsert, update, ban/unban)
- `UserService` (register_or_update, is_banned, ban_user, unban_user)
- `BanCheckMiddleware` to check for and block banned users on every Telegram update
- User auto-registration on `/start` command

---

## [1.2.0] — Sprint 2 — Product Catalogue — 2026-07-09

### Added
- Supabase `products` table schema
- `ProductSchema`, `ProductCreateSchema`, `ProductUpdateSchema`, and `ProductListItemSchema`
- `ProductRepository` and `ProductService`
- Public `/products` and `/product_<id>` deep-link command handlers
- Admin `/toggleproduct <id>` handler to activate/deactivate products

---

## [1.3.0] — Sprint 3 — Order System — 2026-07-09

### Added
- Supabase `orders` table schema and `order_status` PostgreSQL enum
- `OrderSchema`, `OrderCreateSchema`, `OrderUpdateSchema`, and `OrderSummarySchema`
- `OrderRepository` (CRUD, status updates) and `OrderService` (ownership checks, cancellation, confirmation rules)
- User commands: `/myorders`, `/orderstatus <id>`, `/cancelorder <id>`

---

## [1.4.0] — Sprint 4 — Payment Verification & Admin Queue — 2026-07-09

### Added
- FSM-based `/pay <order_id>` flow with image proof submission handler
- `OCRService` placeholder with auto-review routing
- Admin commands: `/pendingpayments`, `/proof_<id>`, `/approvepayment <id>`, `/rejectpayment <id>`
- Auto-notification of users on payment status confirmation/rejection

---

## [1.5.0] — Sprint 5 — AI Support System & Broadcasts — 2026-07-09

### Added
- Pydantic validation schemas (`SupportTicketSchema`, `SupportMessageSchema`)
- `SupportRepository` wrapping ticket lookup/updates and support messages logging
- Abstract `AIProviderInterface` and `GeminiProvider` service using asynchronous direct REST endpoint connection
- User `/support` command implementing support FSM state, chat history payload mapping, and direct Gemini responses
- `/human` command routing user request to a human agent, pausing Gemini, and alerting admins via direct message
- Live support forwarding alerts letting admins see incoming handoff messages in real-time
- Admin commands: `/tickets`, `/replyticket <id> <message>`, `/closeticket <id>`
- Admin `/broadcast <message>` command to dispatch system announcements to all users in the system

---

## [1.7.0] — Sprint 7 — OCR Verification & PDF Auto-Delivery — 2026-07-09

### Added
- **OCR Engine Implementation:** Integrated EasyOCR in `services/ocr_service.py` with templates for PhonePe, GPay, Paytm, and BHIM to extract Receiver, Amount, Date, Time, and UTR metrics.
- **₹ Character & Decimal Normalization:** Added regex algorithms to normalize rupee signs (frequently misread as `7`, `8`, or `1` by OCR) and decimal point drops (e.g. `15000` instead of `150.00`).
- **Fraud Prevention:** Added `UTRRepository` to track and prevent duplicate transaction reuse (double-spending protection).
- **Auto-Fulfillment Engine:** Added `bot/handlers/fulfillment.py` to automatically confirm orders, deliver PDF documents (`bot.send_document`), and mark them as delivered.
- **Admin File Linking:** Created an interactive `📁 Link PDF File` button in product details for admins to upload and associate PDF documents via FSM.
- **Help Menu Expansion:** Updated `/help` output to list the new `/setproductfile` command.

---

_Next: Production Deployment & Maintenance_

