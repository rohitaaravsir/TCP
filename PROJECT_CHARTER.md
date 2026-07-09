```markdown
---
Project: Telegram Commerce Platform (TCP)
Version: 1.0.0
Document: PROJECT_CHARTER.md
Status: Approved
Architecture: Python First
Database: Supabase
Hosting: Render / Koyeb
Last Updated: 2026-07-07
---

# PROJECT CHARTER

## Purpose

This document is the single source of truth for the entire project.

Every AI coding assistant, developer, or contributor MUST read this document before generating, modifying, or reviewing any code.

This document defines the project vision, architecture, engineering philosophy, and implementation rules.

---

# Project Vision

Build a production-grade Telegram Commerce Platform capable of selling digital products through Telegram with automated workflows, OCR-based payment verification, AI-assisted customer support, human support, broadcasting, administrative tools, and future scalability.

The platform should remain modular, maintainable, secure, and easy to extend.

---

# Primary Objectives

- Sell digital products
- Automate payment verification
- Deliver purchased content
- Support AI-assisted conversations
- Allow seamless human takeover
- Manage users
- Manage products
- Broadcast announcements
- Maintain complete logs
- Remain scalable

---

# Long-Term Vision

The current project targets Telegram.

Future expansion may include:

- Website
- WhatsApp
- Mobile App
- API
- n8n Integration
- Multiple Telegram Bots
- Multiple Businesses

The architecture must support future expansion without major rewrites.

---

# Core Engineering Philosophy

Deterministic Logic First.

Artificial Intelligence Second.

Python controls every workflow.

AI never controls the workflow.

---

# Architecture Principles

- Modular Architecture
- Service Layer Pattern
- Event Driven Design
- State Machine Based Workflow
- Feature Flag Support
- Configuration Over Hardcoding
- Logging First
- Security First

---

# Technology Stack

Language:
Python

Telegram:
aiogram (preferred) or python-telegram-bot

Database:
Supabase (PostgreSQL)

Storage:
Supabase Storage

OCR:
EasyOCR + Template Parser

AI Providers:

- Groq
- Gemini
- OpenRouter

Hosting:

- Render
- Koyeb

Configuration:

Environment Variables

---

# AI Philosophy

Artificial Intelligence is an assistant.

It is NOT the system controller.

Priority:

1. Rule Engine
2. Intent Detection
3. Cache
4. AI Provider
5. Human Support

AI should only be used when deterministic logic cannot solve the problem.

---

# Security Principles

- No hardcoded secrets
- Environment variables only
- Role based permissions
- Rate limiting
- Ban system
- Audit logs
- Duplicate detection
- Input validation
- File validation

---

# OCR Philosophy

OCR must never blindly approve payments.

Verification should use confidence scoring.

Primary Checks:

- Receiver Name
- Amount
- Date
- Time

Secondary Checks:

- Receiver UPI
- UTR
- Transaction Reference

If confidence is below threshold:

Manual Review.

---

# Human Support Philosophy

AI should always attempt first.

If AI confidence is low:

Create Support Ticket.

Human support must always be able to continue the same conversation.

---

# Development Rules

- One responsibility per module
- No business logic inside Telegram handlers
- No direct database access from handlers
- All business logic belongs to services
- Every important action must be logged
- Every module must be testable
- Never skip architecture

---

# Sprint Strategy

Development follows sprint-based implementation.

Each sprint must produce:

- Working code
- Updated documentation
- Passing tests
- Clean project structure

Future modules must NOT be implemented before the current sprint is completed.

---

# Project Memory

The project maintains its own memory.

Every completed sprint updates:

.memory/

This allows any future AI coding assistant to continue development without losing context.

---

# Documentation Hierarchy

This document has the highest priority.

After reading this document:

Read README.md

Then follow the current sprint.

Do not implement future phases.

---

# Definition of Success

The project is considered successful when:

- Stable
- Modular
- Production Ready
- Secure
- Easy to Maintain
- AI Optimized
- Cost Efficient
- Easily Expandable

---

# Final Rule

Never sacrifice architecture for speed.

Build once.

Scale forever.
```
