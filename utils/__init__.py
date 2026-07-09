"""
utils package

Reusable, stateless helper utilities.

Rules:
  - No business logic here.
  - No database access here.
  - All functions must be pure (same input → same output).
  - All functions must be independently testable.

Future utilities:
  - date_helpers.py    — timezone-aware datetime formatting
  - hash_helpers.py    — file hashing (SHA256) for duplicate detection
  - validators.py      — phone, email, UPI ID, amount validators
  - formatters.py      — currency, message text, truncation helpers
  - file_helpers.py    — safe file path handling, extension checks
"""
