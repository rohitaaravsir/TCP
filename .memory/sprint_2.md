# Sprint 2 — Product Catalog

**Status:** ✅ Complete  
**Date:** 2026-07-09  
**Version:** 1.2.0  
**Tests:** 66/66 passing  

---

## What Was Built

Sprint 2 implemented the complete Product Catalog layer following TCP architecture.

### Files Created

**schemas/**
- `product.py` — `ProductSchema`, `ProductCreateSchema`, `ProductUpdateSchema`, `ProductListItemSchema`

**repositories/**
- `product_repository.py` — `ProductRepository` (Supabase async CRUD)
  - `get_by_id`, `list_active`, `list_all`, `list_by_category`, `create`, `update`, `set_active`

**services/**
- `product_service.py` — `ProductService` (business logic)
  - `get_catalogue`, `get_catalogue_by_category`, `get_product`
  - `create_product`, `update_product`, `activate_product`, `deactivate_product`, `get_all_products_admin`

**bot/handlers/**
- `products.py` — Public: `/products`, `/product_<id>` | Admin: `/toggleproduct <id>`

### Files Modified

- `bot/loader.py` — product router registered (routers=2)
- `app.py` — `ProductRepository` + `ProductService` wired + injected into dispatcher
- `core/constants.py` — `MSG_HELP` updated with `/products` command

### Database

Supabase `products` table created:

```sql
CREATE TABLE products (
    id          BIGSERIAL     PRIMARY KEY,
    name        TEXT          NOT NULL,
    description TEXT,
    price       NUMERIC(10,2) NOT NULL CHECK (price >= 0),
    category    TEXT          DEFAULT 'general',
    file_id     TEXT,
    is_active   BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
```

---

## Architecture Decisions

| Decision | Rationale |
|---|---|
| `ProductListItemSchema` separate from `ProductSchema` | Catalogue view never exposes `file_id` — security by design |
| `price_display` as property on schema | Formatting logic stays in schema layer, not in handlers |
| `Decimal` for price | Avoids floating-point rounding errors in financial data |
| `/product_<id>` deep-link pattern | Extensible; each product gets a unique command without FSM |
| `float()` conversion before Supabase insert | JSON serialisation requires float, Decimal is not JSON-native |

---

## Tests Added

| File | Tests |
|---|---|
| `test_product_schema.py` | 17 tests — all 4 schemas + price_display |
| `test_product_service.py` | 14 tests — all 6 service methods |

**Total project tests: 66/66 ✅**

---

## What Comes Next

Sprint 3: Order Management
- `orders` Supabase table
- `OrderSchema`, `OrderCreateSchema`
- `OrderRepository` (create, get_by_id, list_by_user, update_status)
- `OrderService` (place_order, get_order, list_user_orders)
- `/order <product_id>` handler — initiate purchase flow
- Order status tracking (pending → confirmed → delivered)
