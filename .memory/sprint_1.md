# Sprint 1 — User Management

**Status:** ✅ Complete  
**Date:** 2026-07-09  
**Version:** 1.1.0  
**Tests:** 35/35 passing  

---

## What Was Built

Sprint 1 implemented the complete User Management layer following the strict
TCP architecture: **Handler → Service → Repository → Supabase**.

### Files Created

**schemas/**
- `user.py` — `UserSchema`, `UserCreateSchema`, `UserUpdateSchema`

**repositories/**
- `user_repository.py` — `UserRepository` (Supabase async CRUD)
  - `get_by_id`, `create`, `upsert`, `update`, `ban`, `unban`

**services/**
- `user_service.py` — `UserService` (business logic)
  - `register_or_update`, `get_user`, `is_banned`, `ban_user`, `unban_user`

**bot/middlewares/**
- `ban_check.py` — `BanCheckMiddleware` (blocks banned users on every update)

**Root**
- `pytest.ini` — asyncio_mode=auto, loop scope config

### Files Modified

- `bot/handlers/common.py` — `/start` calls `UserService.register_or_update()`
- `app.py` — wires `UserRepository` → `UserService` → `BanCheckMiddleware`

### Database

Supabase `users` table created:

```sql
CREATE TABLE users (
    id            BIGINT PRIMARY KEY,
    username      TEXT,
    full_name     TEXT        NOT NULL,
    language_code TEXT        DEFAULT 'en',
    is_banned     BOOLEAN     NOT NULL DEFAULT FALSE,
    ban_reason    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## Architecture Decisions

| Decision | Rationale |
|---|---|
| `upsert` on `/start` | Idempotent — safe to call on every /start without duplicate rows |
| `is_banned` fails open | DB failure must not block legitimate users |
| Service injected via dispatcher data | Handlers receive service through aiogram DI — no direct import coupling |
| `updated_at` set in Python | Consistent across all Supabase tiers (no trigger dependency) |
| Outer middleware for ban check | Runs before any handler — banned users never reach business logic |

---

## Tests Added

| File | Tests |
|---|---|
| `test_user_schema.py` | 12 tests — UserSchema, UserCreateSchema, UserUpdateSchema |
| `test_user_service.py` | 14 tests — all 5 service methods + fail-open behaviour |

**Total project tests: 35/35 ✅**

---

## What Comes Next

Sprint 2: Product Catalog
- `products` Supabase table
- `ProductSchema`, `ProductCreateSchema`
- `ProductRepository` (list, get_by_id, create, toggle_active)
- `ProductService`
- `/products` handler — browse catalog
- Admin: `/addproduct`, `/toggleproduct`
