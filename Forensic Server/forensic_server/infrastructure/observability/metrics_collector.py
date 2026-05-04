from __future__ import annotations

import bisect
import threading
from typing import Dict, List, Optional


def _tag_suffix(tags: Optional[Dict[str, str]]) -> str:
    if not tags:
        return ""
    parts = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
    return "{" + parts + "}"


def _percentile(sorted_values: List[float], p: float) -> float:
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
    __slots__ = ("_lock", "_samples", "_total", "_count")

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._samples: List[float] = []
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
                return {"count": 0, "sum": 0.0, "min": 0.0, "max": 0.0, "mean": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0}
            samples = self._samples
            return {
                "count": self._count,
                "sum": round(self._total, 6),
                "min": round(samples[0], 6),
                "max": round(samples[-1], 6),
                "mean": round(self._total / self._count, 6),
                "p50": round(_percentile(samples, 50), 6),
                "p95": round(_percentile(samples, 95), 6),
                "p99": round(_percentile(samples, 99), 6),
            }

    def reset(self) -> None:
        with self._lock:
            self._samples.clear()
            self._total = 0.0
            self._count = 0


class MetricsCollector:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, _Histogram] = {}

    def increment(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        key = name + _tag_suffix(tags)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value

    def decrement(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        self.increment(name, -value, tags)

    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        key = name + _tag_suffix(tags)
        with self._lock:
            self._gauges[key] = value

    def histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        key = name + _tag_suffix(tags)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = _Histogram()
            hist = self._histograms[key]
        hist.record(value)

    def get_stats(self) -> dict:
        with self._lock:
            counters = dict(self._counters)
            gauges = dict(self._gauges)
            hist_refs = {key: self._histograms[key] for key in list(self._histograms.keys())}
        histograms = {key: hist.snapshot() for key, hist in hist_refs.items()}
        return {"counters": counters, "gauges": gauges, "histograms": histograms}

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            hist_refs = list(self._histograms.values())
            self._histograms.clear()
        for hist in hist_refs:
            hist.reset()


_default_collector: Optional[MetricsCollector] = None
_singleton_lock = threading.Lock()


def get_metrics() -> MetricsCollector:
    global _default_collector
    if _default_collector is None:
        with _singleton_lock:
            if _default_collector is None:
                _default_collector = MetricsCollector()
    return _default_collector
