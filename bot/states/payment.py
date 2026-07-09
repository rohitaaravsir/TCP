"""
bot/states/payment.py

FSM (Finite State Machine) states for the payment submission flow.

Flow:
  1. User sends /pay <order_id>
  2. Bot validates the order and enters WaitingForPaymentProof state
  3. User sends a photo (payment screenshot)
  4. Bot receives the photo, calls submit_payment_proof, exits FSM

Rules (from PROJECT_RULES.md — Rule 10):
  - Every user action must belong to a valid state.
  - Never bypass state transitions.

Usage:
    from bot.states.payment import PaymentStates
    await state.set_state(PaymentStates.waiting_for_proof)
"""

from aiogram.fsm.state import State, StatesGroup


class PaymentStates(StatesGroup):
    """States for the payment proof submission flow."""

    # Waiting for the user to send a payment screenshot photo
    waiting_for_proof = State()
