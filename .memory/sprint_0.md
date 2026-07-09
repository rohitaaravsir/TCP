# Sprint 0 — Project Foundation

**Status:** ✅ Complete
**Date:** 2026-07-09
**Version:** 1.0.0

---

## What Was Built

Sprint 0 established the complete project foundation for the Telegram Commerce Platform.

### Files Created

**Root**
- `requirements.txt` — pinned dependencies
- `.env.example` — environment variable template
- `.gitignore` — Python, venv, secrets, logs
- `main.py` — entry point (bootstrap only)
- `app.py` — application lifecycle
- `health.py` — HTTP health check server

**config/**
- `settings.py` — pydantic-settings typed config loader

**core/**
- `logger.py` — rotating file + console logger
- `database.py` — Supabase async client wrapper
- `constants.py` — centralised app constants
- `exceptions.py` — custom exception hierarchy

**bot/**
- `loader.py` — Bot + Dispatcher factory (aiogram 3.x)
- `handlers/common.py` — /start, /help, /ping
- Empty: `middlewares/`, `filters/`, `keyboards/`, `states/`

**Empty architecture folders**
- `services/`, `repositories/`, `schemas/`, `interfaces/`, `events/`, `utils/`, `storage/`

**tests/**
- `unit/test_config.py` — 9 unit tests for Settings

**Documentation**
- `README.md`, `CHANGELOG.md`, `ARCHITECTURE_MAP.md`

---

## Architecture Decisions

| Decision | Rationale |
|---|---|
| aiogram 3.x | Charter preferred; async-first |
| pydantic-settings | Type-safe config; fails fast |
| app.py + main.py split | Separation of concerns |
| repositories/ (not data/) | Repository Pattern |
| Single requirements.txt | Splitting intentionally postponed |

---

## What Comes Next

Sprint 1: User Management
- User registration
- User lookup
- Ban system
- UserRepository
- UserService
- UserSchema
