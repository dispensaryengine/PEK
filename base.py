#!/usr/bin/env python3
"""Base scraper class shared by all platform adapters."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterator
import time, logging

log = logging.getLogger(__name__)

class BaseScraper(ABC):
    platform: str = "unknown"
    REQUEST_DELAY: float = 0.3

    def __init__(self, store: dict):
        self.store = store
        self.name  = store["name"]

    # ── Each adapter must implement this ─────────────────────────────────────
    @abstractmethod
    def scrape(self) -> list[dict]:
        """Return list of normalised RawProduct dicts."""

    # ── Shared helpers ────────────────────────────────────────────────────────
    def _sleep(self, seconds: float | None = None):
        time.sleep(seconds if seconds is not None else self.REQUEST_DELAY)

    @staticmethod
    def _safe(value, default=None):
        return value if value not in (None, "", "null", "None") else default

    @staticmethod
    def _cents_to_usd(cents) -> float | None:
        try:
            return round(float(cents) / 100, 2)
        except (TypeError, ValueError):
            return None

    def raw_product(self, **kwargs) -> dict:
        """Wrap any dict with required housekeeping fields."""
        return {
            "dispensary_name": self.name,
            "platform":        self.platform,
            **kwargs,
        }
