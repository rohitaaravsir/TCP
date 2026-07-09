# Sprint 3 — Order Management

**Status:** ✅ Complete  
**Date:** 2026-07-09  
**Version:** 1.3.0  
**Tests:** 105/105 passing  

---

## What Was Built

Sprint 3 implemented the complete Order Management layer with full state machine.

### Files Created

**schemas/**
- `order.py` — `OrderStatus` (enum), `OrderSchema`, `OrderCreateSchema`, `OrderUpdateSchema`, `OrderSummarySchema`

**repositories/**
- `order_repository.py` — `OrderRepository` (Supabase async CRUD)
  - `get_by_id`, `list_by_user`, `list_by_status`, `create`, `update`, `update_status`

**services/**
- `order_service.py` — `OrderService` (business logic + state machine)
  - `place_order`, `get_order`, `list_user_orders`
  - `cancel_order`, `submit_payment_proof`
  - `confirm_order`, `mark_delivered`, `list_pending_payments`

**bot/handlers/**
- `orders.py` — `/order <id>`, `/myorders`, `/orderstatus <id>`, `/cancelorder <id>`

### Files Modified

- `bot/loader.py` — order router registered (routers=3)
- `app.py` — `OrderRepository` + `OrderService` wired + injected into dispatcher
- `core/constants.py` — `MSG_HELP` updated with order commands

### Database

```sql
CREATE TYPE order_status AS ENUM (
    'pending', 'payment_submitted', 'confirmed',
    'delivered', 'cancelled', 'refunded'
);

CREATE TABLE orders (
    id            BIGSERIAL     PRIMARY KEY,
    user_id       BIGINT        NOT NULL REFERENCES users(id),
    product_id    BIGINT        NOT NULL REFERENCES products(id),
    amount        NUMERIC(10,2) NOT NULL CHECK (amount >= 0),
    status        order_status  NOT NULL DEFAULT 'pending',
    payment_proof TEXT,
    notes         TEXT,
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status  ON orders(status);
```

---

## Architecture Decisions

| Decision | Rationale |
|---|---|
| Price snapshotted at order time | Protects against product price changes after ordering |
| Ownership check in cancel + submit_proof | Users can only modify their own orders |
| `OrderServiceError` separate exception | Business rule violations distinct from DB errors |
| `OrderStatus` as `str` Enum | Supabase PostgreSQL enum maps cleanly to Python str |
| `/orderstatus` hides other users' orders | Security — returns same "not found" for both missing and unauthorized |
| `list_by_user` returns `OrderSummarySchema` | No `payment_proof` or `notes` exposed to user-facing list view |

---

## Order State Machine

```
pending → payment_submitted → confirmed → delivered
   ↓                                         
cancelled (from pending only, user-initiated)
confirmed → refunded (admin)
```

---

## Tests Added

| File | Tests |
|---|---|
| `test_order_schema.py` | 24 tests — all 5 schemas + status displays |
| `test_order_service.py` | 15 tests — all 8 service methods + ownership/state guards |

**Total project tests: 105/105 ✅**

---

## What Comes Next

Sprint 4: Payment Verification (OCR)
- Payment screenshot submission flow (FSM states)
- `payment_proof` Telegram photo handler
- OCR pipeline integration placeholder (confidence scoring)
- Admin payment review queue (`/pendingpayments`, `/approvepayment <id>`, `/rejectpayment <id>`)
- Auto-notify user on payment status update
