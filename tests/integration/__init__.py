"""
tests/integration package

Integration tests — test components together with real external services.

Examples (future sprints):
  - test_database_connection.py — verify Supabase connection
  - test_bot_startup.py         — verify bot polling starts cleanly
  - test_health_endpoint.py     — verify GET /health returns 200

Integration tests require a real .env file with valid credentials.
Run with: pytest tests/integration/ --env=.env.test
"""
