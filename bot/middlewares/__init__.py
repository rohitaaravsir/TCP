"""
bot/middlewares package

Middlewares intercept every incoming update before it reaches a handler.

Future middlewares to register here:
  - ThrottlingMiddleware  — rate limiting per user
  - AuthMiddleware        — verify user permissions and ban status
  - LoggingMiddleware     — structured request/response logging
  - MaintenanceMiddleware — block all updates during maintenance

Registration:
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())
"""
