"""
events package

Event-driven architecture (PROJECT_CHARTER.md — Event Driven Design).

Purpose:
  - Modules communicate through events to remain loosely coupled.
  - Event classes carry all data needed for subscribers to act.

Future events:
  - PaymentSubmitted    — user submitted a payment screenshot
  - PaymentApproved     — payment verified and approved
  - PaymentRejected     — payment failed verification
  - OrderCreated        — new order placed
  - OrderFulfilled      — digital product delivered
  - OCRCompleted        — OCR analysis finished
  - SupportCreated      — new support ticket opened
  - SupportResolved     — support ticket closed
  - BroadcastSent       — broadcast message dispatched
  - UserBanned          — user account banned
"""
