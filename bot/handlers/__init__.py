"""
bot/handlers package

Handler modules are registered in bot/loader.py via include_router().

Each handler module must:
  - Define a module-level `router = Router()`
  - Contain ONLY: receive update → call service → send response
  - Never contain business logic
  - Never access the database directly
"""
