# ARCHITECTURE MAP
# Telegram Commerce Platform (TCP) — v1.0.0

---

## Module Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        ENTRY POINT                          │
│                                                             │
│   main.py  ──────────────►  app.py                         │
│   (bootstrap)              (lifecycle: init/start/shutdown) │
└─────────────────────────────────────────────────────────────┘
                                │
              ┌─────────────────┼──────────────────┐
              ▼                 ▼                  ▼
        ┌──────────┐    ┌────────────┐    ┌─────────────┐
        │ config/  │    │   core/    │    │  health.py  │
        │          │    │            │    │             │
        │ settings │    │ logger     │    │ GET /health │
        └──────────┘    │ database   │    └─────────────┘
                        │ constants  │
                        │ exceptions │
                        └────────────┘
                                │
              ┌─────────────────┼──────────────────┐
              ▼                 ▼                  ▼
        ┌──────────┐    ┌────────────┐    ┌─────────────────┐
        │   bot/   │    │ services/  │    │ repositories/   │
        │          │    │            │    │                 │
        │ loader   │    │ (future)   │    │ (future)        │
        │ handlers │    │            │    │                 │
        │ middlewares   └────────────┘    └─────────────────┘
        │ filters  │            │                  │
        │ keyboards│            └──────────────────┘
        │ states   │                     │
        └──────────┘                     ▼
                              ┌────────────────────┐
                              │   Supabase (DB)     │
                              │   PostgreSQL        │
                              └────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                   SUPPORT LAYERS                             │
│                                                             │
│  schemas/      Pydantic request/response models             │
│  interfaces/   Abstract provider contracts (AI, OCR, etc.)  │
│  events/       Event-driven module communication            │
│  utils/        Stateless helper utilities                   │
│  storage/      Temporary local file storage                 │
└──────────────────────────────────────────────────────────────┘
```

---

## Dependency Map

```
main.py
  └── app.py
        ├── config/settings.py
        ├── core/logger.py
        ├── core/database.py
        │     └── core/exceptions.py
        ├── core/constants.py
        ├── bot/loader.py
        │     └── bot/handlers/common.py
        │           └── core/constants.py
        └── health.py
              ├── core/constants.py
              └── core/database.py
```

---

## Module Relationships

| Module | Depends On | Used By |
|---|---|---|
| `config/settings.py` | `pydantic-settings` | `app.py`, all modules |
| `core/logger.py` | `logging` (stdlib) | All modules |
| `core/database.py` | `supabase`, `core/exceptions` | `app.py`, repositories |
| `core/constants.py` | — | `bot/handlers`, `health.py`, `app.py` |
| `core/exceptions.py` | — | `core/database`, services, repositories |
| `bot/loader.py` | `aiogram`, `bot/handlers` | `app.py` |
| `bot/handlers/common.py` | `aiogram`, `core/constants` | `bot/loader.py` |
| `health.py` | `aiohttp`, `core/constants`, `core/database` | `app.py` |
| `app.py` | all of the above | `main.py` |
| `main.py` | `app.py`, `core/logger` | — (entry point) |

---

## Layer Rules

```
Telegram User
     │
     ▼
┌──────────────┐   Receives updates, calls services, sends responses.
│  bot/handlers │   NO business logic. NO direct DB access.
└──────────────┘
     │
     ▼
┌──────────────┐   All business operations live here.
│  services/   │   Calls repositories for data. Raises typed exceptions.
└──────────────┘
     │
     ▼
┌──────────────┐   All DB access lives here. Uses core/database.py client.
│ repositories/│   Never accessed by handlers directly.
└──────────────┘
     │
     ▼
┌──────────────┐   Supabase PostgreSQL
│  Supabase    │
└──────────────┘
```

---

## Future Integration Points

```
TCP Core
  ├── n8n Webhooks          → events/ layer
  ├── REST API              → new api/ module (future)
  ├── Web Dashboard         → external service via Supabase
  ├── Mobile App            → external service via Supabase
  ├── Additional Bots       → new bot instances via bot/loader.py
  └── AI Providers (Groq, Gemini, OpenRouter)
                            → interfaces/AIProviderInterface
```
