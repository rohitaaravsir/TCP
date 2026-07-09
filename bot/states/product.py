"""
bot/states/product.py

FSM state groups for product administration.
"""

from aiogram.fsm.state import State, StatesGroup


class AdminProductStates(StatesGroup):
    """States for the product administration flows."""
    waiting_for_pdf = State()
