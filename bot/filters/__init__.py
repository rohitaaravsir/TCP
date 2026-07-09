"""
bot/filters package

Custom aiogram filters for targeted handler registration.

Future filters to implement here:
  - IsAdminFilter       — True if the user is in the admin list
  - IsBannedFilter      — True if the user is banned
  - IsPrivateChatFilter — True if the message is in a private chat
  - HasActiveOrderFilter — True if the user has a pending order

Usage in handlers:
    @router.message(Command("admin"), IsAdminFilter())
    async def handle_admin(message: Message): ...
"""
