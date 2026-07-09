"""
bot/states/support.py

FSM (Finite State Machine) states for the customer support conversation flow.
"""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class SupportStates(StatesGroup):
    """States for the customer support conversation flow."""

    # Active customer support state where user messages are routed to AI / Human.
    waiting_for_user = State()
