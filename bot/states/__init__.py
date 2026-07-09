"""
bot/states package

aiogram FSM state groups.

Every user action belongs to a valid state (PROJECT_RULES.md — Rule 10).
State transitions are never bypassed.

Future state groups to implement here:
  - OrderStates         — browsing, selecting, confirming, paying
  - PaymentStates       — awaiting screenshot, verifying
  - SupportStates       — awaiting issue description, in-ticket
  - RegistrationStates  — onboarding flow

Usage:
    from aiogram.fsm.state import State, StatesGroup

    class OrderStates(StatesGroup):
        browsing = State()
        selecting_product = State()
        awaiting_payment = State()
"""
from bot.states.payment import PaymentStates
from bot.states.support import SupportStates

__all__ = [
    "PaymentStates",
    "SupportStates",
]
