# Telegram Commerce Platform (TCP)

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-blue.svg)](https://aiogram.dev)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-green.svg)](https://supabase.com)

A production-grade Telegram Commerce Platform for selling digital products with automated payment verification, AI-assisted support, and full administrative control.

---

## Architecture

```
TCP/
├── main.py              Entry point (bootstrap only)
├── app.py               Application lifecycle (init, start, shutdown)
├── health.py            HTTP health check (GET /health)
│
├── config/              Typed environment configuration
├── core/                Infrastructure: logging, database, constants, exceptions
│
├── bot/
│   ├── loader.py        Bot + Dispatcher factory
│   ├── handlers/        Telegram update handlers
│   ├── middlewares/     Request interceptors
│   ├── filters/         Custom message filters
│   ├── keyboards/       Inline / reply keyboards
│   └── states/          FSM state groups
│
├── services/            Business logic layer
├── repositories/        Database access layer (Repository Pattern)
├── schemas/             Pydantic request/response models
├── interfaces/          Abstract provider interfaces
├── events/              Event-driven architecture
├── utils/               Reusable stateless helpers
└── storage/             Temporary file storage
```

---

## Quick Start

### 1. Clone and set up the environment

```bash
git clone <repo-url>
cd TCP
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your real Telegram token and Supabase credentials
```

### 4. Run the bot

```bash
python main.py
```

### 5. Health check

```
GET http://localhost:8080/health
→ {"status": "ok", "version": "1.0.0", "database": "connected"}
```

---

## Bot Commands

| Command | Description |
|---|---|
| `/start` | Open the main menu |
| `/help` | List available commands |
| `/ping` | Check bot latency |

---

## Running Tests

```bash
# Unit tests only (no credentials required)
pytest tests/unit/ -v

# All tests
pytest tests/ -v
```

---

## Environment Variables

See `.env.example` for the full list of required and optional variables.

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from @BotFather |
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_ANON_KEY` | ✅ | Supabase anonymous key |
| `SUPABASE_SERVICE_KEY` | ✅ | Supabase service role key |
| `APP_ENV` | — | `development` (default) |
| `LOG_LEVEL` | — | `INFO` (default) |
| `HEALTH_PORT` | — | `8080` (default) |

---

## Development Philosophy

- **Python controls every workflow** — AI is only an assistant
- **Service layer pattern** — all business logic in `services/`
- **Repository pattern** — all DB access in `repositories/`
- **No hardcoded secrets** — environment variables only
- **Logging first** — every important action is logged
- **Architecture first** — no shortcuts, no temporary fixes

See `PROJECT_CHARTER.md` and `PROJECT_RULES.md` for the full engineering philosophy.

---

## Sprint Status

| Sprint | Status | Description |
|---|---|---|
| Sprint 0 | ✅ Complete | Project Foundation |
| Sprint 1 | ✅ Complete | User Management |
| Sprint 2 | ✅ Complete | Product Catalogue |
| Sprint 3 | ✅ Complete | Order System |
| Sprint 4 | ✅ Complete | Payment Verification |
| Sprint 5 | ✅ Complete | AI Support |

---

## Deployment

Designed for deployment on **Render** or **Koyeb**.

Start command: `python main.py`

Health check: `GET /health`
