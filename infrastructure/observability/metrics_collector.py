"""
infrastructure/observability/metrics_collector.py

Thread-safe in-process metrics: counters, histograms, and gauges.

Usage
-----
    from infrastructure.observability import get_metrics

    metrics = get_metrics()
    metrics.increment("http.requests", tags={"method": "POST", "endpoint": "/cases"})
    metrics.histogram("db.query_ms", 42.5, tags={"table": "cases"})
    metrics.gauge("cache.size", 1024)

    stats = metrics.get_stats()
    # {
    #   "counters": {"http.requests{endpoint=/cases,method=POST}": 7},
    #   "gauges":   {"cache.size": 1024},
    #   "histograms": {
    #       "db.query_ms{table=cases}": {
    #           "count": 3, "sum": 120.0, "min": 22.0, "max": 55.0, "mean": 40.0,
    #           "p50": 43.0, "p95": 54.5, "p99": 54.9
    #       }
    #   }
    # }
"""

from __future__ import annotations

import bisect
import threading
from typing import Dict, List, Optional


def _tag_suffix(tags: Optional[Dict[str, str]]) -> str:
    """Return a deterministic label suffix like ``{a=1,b=2}``."""
    if not tags:
        return ""
    parts = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
    return "{" + parts + "}"


def _percentile(sorted_values: List[float], p: float) -> float:
    """Return the *p*-th percentile (0–100) of an already-sorted list."""
    if not sorted_values:
        return 0.0
    index = (p / 100) * (len(sorted_values) - 1)
    lower = int(index)
    upper = lower + 1
    if upper >= len(sorted_values):
        return sorted_values[-1]
    frac = index - lower
    return sorted_values[lower] + frac * (sorted_values[upper] - sorted_values[lower])


class _Histogram:
    """Accumulates float samples; computes summary statistics on demand."""

    __slots__ = ("_lock", "_samples", "_total", "_count")

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._samples: List[float] = []   # kept sorted for percentile queries
        self._total: float = 0.0
        self._count: int = 0

    def record(self, value: float) -> None:
        with self._lock:
            bisect.insort(self._samples, value)
            self._total += value
            self._count += 1

    def snapshot(self) -> dict:
        with self._lock:
            if self._count == 0:
                return {"count": 0, "sum": 0.0, "min": 0.0, "max": 0.0,
                        "mean": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0}
            s = self._samples  # already sorted
            return {
                "count": self._count,
                "sum": round(self._total, 6),
                "min": round(s[0], 6),
                "max": round(s[-1], 6),
                "mean": round(self._total / self._count, 6),
                "p50": round(_percentile(s, 50), 6),
                "p95": round(_percentile(s, 95), 6),
                "p99": round(_percentile(s, 99), 6),
            }

    def reset(self) -> None:
        with self._lock:
            self._samples.clear()
            self._total = 0.0
            self._count = 0


class MetricsCollector:
    """Thread-safe collector for counters, histograms, and gauges.

    All methods are safe to call from multiple threads simultaneously.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, _Histogram] = {}

    # ------------------------------------------------------------------
    # Counter — monotonically increasing integer
    # ------------------------------------------------------------------

    def increment(
        self,
        name: str,
        value: int = 1,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Increment counter *name* by *value* (default 1)."""
        key = name + _tag_suffix(tags)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value

    def decrement(
        self,
        name: str,
        value: int = 1,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Decrement counter *name* by *value* (useful for queue depth etc.)."""
        self.increment(name, -value, tags)

    # ------------------------------------------------------------------
    # Gauge — arbitrary float, last-write-wins
    # ------------------------------------------------------------------

    def gauge(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record gauge *name* = *value*."""
        key = name + _tag_suffix(tags)
        with self._lock:
            self._gauges[key] = value

    # ------------------------------------------------------------------
    # Histogram — distribution of float samples
    # ------------------------------------------------------------------

    def histogram(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a single observation in histogram *name*."""
        key = name + _tag_suffix(tags)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = _Histogram()
            hist = self._histograms[key]
        hist.record(value)

    # ------------------------------------------------------------------
    # Query / reset
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Return a snapshot of all metrics.

        Returns
        -------
        dict with keys ``counters``, ``gauges``, ``histograms``.
        """
        with self._lock:
            counters_snap = dict(self._counters)
            gauges_snap = dict(self._gauges)
            hist_keys = list(self._histograms.keys())
            hist_refs = {k: self._histograms[k] for k in hist_keys}

        histograms_snap = {k: h.snapshot() for k, h in hist_refs.items()}

        return {
            "counters": counters_snap,
            "gauges": gauges_snap,
            "histograms": histograms_snap,
        }

    def reset(self) -> None:
        """Clear all recorded metrics (useful between tests)."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            hist_refs = list(self._histograms.values())
            self._histograms.clear()
        for h in hist_refs:
            h.reset()

    def counter_value(self, name: str, tags: Optional[Dict[str, str]] = None) -> int:
        """Convenience: return the current value of a single counter."""
        key = name + _tag_suffix(tags)
        with self._lock:
            return self._counters.get(key, 0)

    def gauge_value(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """Convenience: return the current value of a single gauge."""
        key = name + _tag_suffix(tags)
        with self._lock:
            return self._gauges.get(key, 0.0)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_default_collector: Optional[MetricsCollector] = None
_singleton_lock = threading.Lock()


def get_metrics() -> MetricsCollector:
    """Return the process-wide singleton :class:`MetricsCollector`."""
    global _default_collector
    if _default_collector is None:
        with _singleton_lock:
            if _default_collector is None:
                _default_collector = MetricsCollector()
    return _default_collector
