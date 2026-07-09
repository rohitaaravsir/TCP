"""
repositories/utr_repository.py

Supabase-backed repository for UTR (Unique Transaction Reference) records.

Purpose:
  Prevents double-spending fraud by storing every approved payment's
  UTR/Transaction ID. Before auto-approving any payment, the OCR pipeline
  checks this repository to ensure the UTR has not been used before.

Supabase Table Required:
  CREATE TABLE utr_records (
      id          BIGSERIAL PRIMARY KEY,
      utr         TEXT NOT NULL UNIQUE,
      order_id    BIGINT NOT NULL REFERENCES orders(id),
      created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
  );
  CREATE UNIQUE INDEX utr_records_utr_idx ON utr_records(utr);

Rules (from PROJECT_RULES.md — Rule 7):
  - Only repositories may touch the database.
  - No business logic here — only data access.

Usage:
    from repositories.utr_repository import UTRRepository
    repo = UTRRepository(db.client)
    is_dupe = await repo.exists("123456789012")
    await repo.save("123456789012", order_id=42)
"""

from __future__ import annotations

import logging

from supabase import AsyncClient

from core.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)

_TABLE = "utr_records"


class UTRRepository:
    """
    Data-access layer for UTR duplicate-fraud prevention.

    Args:
        client: An authenticated Supabase AsyncClient.
    """

    def __init__(self, client: AsyncClient) -> None:
        self._db = client

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def exists(self, utr: str) -> bool:
        """
        Check whether a UTR/Transaction ID has already been used.

        Args:
            utr: The UTR string to look up (case-insensitive).

        Returns:
            True if the UTR already exists in the database (duplicate fraud).
            False if this is a fresh, unseen UTR.

        Raises:
            DatabaseConnectionError: On Supabase failure.
        """
        try:
            response = (
                await self._db
                .table(_TABLE)
                .select("utr")
                .eq("utr", utr.upper().strip())
                .limit(1)
                .execute()
            )
            found = bool(response.data)
            logger.debug(
                "UTR lookup | utr=%s | found=%s | event=utr.lookup",
                utr, found,
            )
            return found
        except Exception as exc:
            logger.error(
                "UTR lookup failed | utr=%s | error=%s | event=utr.lookup.error",
                utr, exc,
            )
            raise DatabaseConnectionError(
                f"UTR lookup failed for '{utr}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def save(self, utr: str, order_id: int) -> None:
        """
        Persist a UTR after a payment is approved to prevent reuse.

        Args:
            utr:      The UTR/Transaction ID to save.
            order_id: The order this payment belongs to.

        Raises:
            DatabaseConnectionError: On Supabase failure.
        """
        try:
            await self._db.table(_TABLE).insert(
                {
                    "utr": utr.upper().strip(),
                    "order_id": order_id,
                }
            ).execute()
            logger.info(
                "UTR saved | utr=%s | order_id=%s | event=utr.saved",
                utr, order_id,
            )
        except Exception as exc:
            logger.error(
                "UTR save failed | utr=%s | order_id=%s | error=%s | "
                "event=utr.save.error",
                utr, order_id, exc,
            )
            raise DatabaseConnectionError(
                f"UTR save failed for '{utr}': {exc}"
            ) from exc
