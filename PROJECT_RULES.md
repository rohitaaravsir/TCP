```markdown
---
Project: Telegram Commerce Platform (TCP)
Version: 1.0.0
Document: PROJECT_RULES.md
Status: Approved
Priority: Highest
---

# PROJECT RULES

## Purpose

This document defines the mandatory engineering rules that every developer and AI coding assistant must follow.

These rules are not suggestions.

They are mandatory project constraints.

---

# Rule 1 — Architecture First

Never implement code that violates the architecture.

Temporary shortcuts are forbidden.

---

# Rule 2 — Sprint Based Development

Implement only the current sprint.

Do not generate future modules.

Stop after the assigned sprint is complete.

---

# Rule 3 — Python Controls Everything

Python is the workflow controller.

AI is only an assistant.

---

# Rule 4 — AI Limitations

AI MUST NEVER:

- Approve payments
- Modify the database directly
- Ban users
- Change settings
- Skip validation
- Control business workflows

AI may only:

- Understand language
- Classify intent
- Generate replies
- Suggest actions

---

# Rule 5 — Telegram Layer

Telegram handlers are only responsible for:

- Receiving updates
- Calling services
- Sending responses

Business logic is forbidden inside handlers.

---

# Rule 6 — Service Layer

Every business operation belongs inside a service.

Examples:

- PaymentService
- OCRService
- AIService
- ProductService
- OrderService
- SupportService

---

# Rule 7 — Database Access

All database operations must pass through the data layer.

Direct SQL inside handlers is forbidden.

---

# Rule 8 — Configuration

Never hardcode:

- API Keys
- Tokens
- Database URLs
- Secrets
- Passwords

Everything must use environment variables.

---

# Rule 9 — Security

Always validate:

- User input
- Uploaded files
- Image size
- File type
- Permissions

---

# Rule 10 — State Machine

Every user action must belong to a valid state.

Never bypass state transitions.

---

# Rule 11 — Event Driven Design

Modules communicate through events whenever possible.

Avoid tightly coupled modules.

---

# Rule 12 — Logging

Every important action must generate logs.

Examples:

- Payment submitted
- OCR completed
- Order approved
- Content delivered
- User banned
- Broadcast sent

---

# Rule 13 — Error Handling

The system must never crash because of user input.

Errors must be handled gracefully.

---

# Rule 14 — OCR Rules

OCR never blindly approves payments.

Confidence scoring is mandatory.

Manual review must always remain available.

---

# Rule 15 — AI Routing

AI request priority:

1. Rule Engine
2. Intent JSON
3. Cache
4. AI Provider
5. Human Support

AI should be the final option.

---

# Rule 16 — Support

Every conversation must remain linked to its ticket.

Conversation history must never be lost.

---

# Rule 17 — Documentation

Every sprint must update:

- README.md
- .memory
- Changelog

Documentation is part of development.

---

# Rule 18 — Code Quality

Every module must be:

- Modular
- Reusable
- Testable
- Readable

Avoid duplicate code.

---

# Rule 19 — Performance

Avoid unnecessary API calls.

Prefer caching when appropriate.

Avoid repeated OCR on identical screenshots.

---

# Rule 20 — Future Compatibility

Design every module so it can later integrate with:

- n8n
- Additional Telegram Bots
- REST APIs
- Web Dashboard
- Mobile Applications

---

# Definition of Done

A sprint is complete only when:

- Code works
- Tests pass
- Documentation updated
- No placeholder code
- No TODO comments
- Architecture respected

---

# Final Principle

Build for maintainability first.

Optimize only after correctness.

Never trade long-term architecture for short-term speed.
```
