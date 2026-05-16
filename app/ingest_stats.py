from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.models import CellularMeasurement


@dataclass
class IngestionStats:
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_summary_at: float = field(default_factory=time.monotonic)
    last_inserted_at: datetime | None = None
    totals: Counter[str] = field(default_factory=Counter)
    interval: Counter[str] = field(default_factory=Counter)
    interval_topics: Counter[str] = field(default_factory=Counter)
    interval_rats: Counter[str] = field(default_factory=Counter)
    interval_providers: Counter[str] = field(default_factory=Counter)

    def record_received(self) -> None:
        self._increment("received")

    def record_measurement(
        self, measurement: CellularMeasurement, *, inserted: bool
    ) -> None:
        self._increment("inserted" if inserted else "duplicate")
        if inserted:
            self.last_inserted_at = datetime.now(UTC)
        self.interval_topics[measurement.topic] += 1
        self.interval_rats[measurement.rat] += 1
        self.interval_providers[measurement.provider or "unknown"] += 1

    def record_parse_failed(self) -> None:
        self._increment("parse_failed")

    def record_store_failed(self) -> None:
        self._increment("store_failed")

    def should_emit_summary(self, *, now: float, interval_seconds: int) -> bool:
        return now - self.last_summary_at >= interval_seconds

    def emit_summary(self, *, now: float) -> dict[str, Any]:
        interval_seconds = round(now - self.last_summary_at, 3)
        self.last_summary_at = now
        summary = {
            "interval_seconds": interval_seconds,
            "received": self.interval["received"],
            "inserted": self.interval["inserted"],
            "duplicate": self.interval["duplicate"],
            "parse_failed": self.interval["parse_failed"],
            "store_failed": self.interval["store_failed"],
            "total_received": self.totals["received"],
            "total_inserted": self.totals["inserted"],
            "total_duplicate": self.totals["duplicate"],
            "total_parse_failed": self.totals["parse_failed"],
            "total_store_failed": self.totals["store_failed"],
            "topics": dict(self.interval_topics),
            "rats": dict(self.interval_rats),
            "providers": dict(self.interval_providers),
            "last_inserted_at": (
                self.last_inserted_at.isoformat()
                if self.last_inserted_at is not None
                else None
            ),
        }
        self.interval.clear()
        self.interval_topics.clear()
        self.interval_rats.clear()
        self.interval_providers.clear()
        return summary

    def _increment(self, key: str) -> None:
        self.totals[key] += 1
        self.interval[key] += 1
