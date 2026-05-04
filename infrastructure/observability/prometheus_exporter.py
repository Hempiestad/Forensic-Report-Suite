"""
infrastructure/observability/prometheus_exporter.py

Converts the in-process MetricsCollector snapshot into Prometheus text format
(exposition format 0.0.4) so that a Prometheus scraper can ingest it without
any external dependency.

Only stdlib + the existing MetricsCollector are required.

Example output
--------------
# HELP forensic_counters_total Counter metrics
# TYPE forensic_counters_total counter
forensic_http_requests_total{endpoint="/cases",method="POST"} 7
# HELP forensic_histograms Summary of histogram observations
# TYPE forensic_http_latency_ms summary
forensic_http_latency_ms{quantile="0.5"} 42.1
forensic_http_latency_ms{quantile="0.95"} 55.3
forensic_http_latency_ms{quantile="0.99"} 59.8
forensic_http_latency_ms_sum 380.5
forensic_http_latency_ms_count 9
# HELP forensic_gauges Gauge metrics
# TYPE forensic_gauges gauge
forensic_cache_size 1024.0
"""

from __future__ import annotations

import re
from typing import Dict

from infrastructure.observability.metrics_collector import MetricsCollector, get_metrics

# Prometheus metric names must match [a-zA-Z_:][a-zA-Z0-9_:]*
_INVALID_CHARS = re.compile(r"[^a-zA-Z0-9_:]")
# Tags in Prometheus are enclosed in braces: {key="value",...}
_TAG_RE = re.compile(r"^\{(.+)\}$")


def _sanitize_name(name: str) -> str:
    """Replace characters invalid in Prometheus metric names with underscores."""
    return _INVALID_CHARS.sub("_", name)


def _parse_tags(tag_suffix: str) -> str:
    """Convert internal ``{k=v,k=v}`` tag format to Prometheus ``{k="v",k="v"}``."""
    m = _TAG_RE.match(tag_suffix)
    if not m:
        return ""
    pairs = m.group(1).split(",")
    prom_pairs = []
    for pair in pairs:
        if "=" in pair:
            k, v = pair.split("=", 1)
            prom_pairs.append(f'{k.strip()}="{v.strip()}"')
    return "{" + ",".join(prom_pairs) + "}" if prom_pairs else ""


def _split_key(key: str) -> tuple[str, str]:
    """Split ``metric_name{tags}`` into ``(metric_name, tag_suffix)``."""
    brace = key.find("{")
    if brace == -1:
        return key, ""
    return key[:brace], key[brace:]


def generate_prometheus_text(collector: MetricsCollector | None = None) -> str:
    """Return a Prometheus exposition-format string from *collector*.

    If *collector* is None, the process-wide singleton from
    :func:`~infrastructure.observability.metrics_collector.get_metrics` is used.
    """
    if collector is None:
        collector = get_metrics()

    stats = collector.get_stats()
    lines: list[str] = []
    prefix = "forensic"

    # ------------------------------------------------------------------
    # Counters
    # ------------------------------------------------------------------
    counters: Dict[str, int] = stats.get("counters", {})
    if counters:
        lines.append("# HELP forensic_counters_total Application counter metrics")
        lines.append("# TYPE forensic_counters_total counter")
        for key, value in sorted(counters.items()):
            base, tag_suffix = _split_key(key)
            prom_name = _sanitize_name(f"{prefix}_{base}_total")
            prom_tags = _parse_tags(tag_suffix)
            lines.append(f"{prom_name}{prom_tags} {value}")

    # ------------------------------------------------------------------
    # Gauges
    # ------------------------------------------------------------------
    gauges: Dict[str, float] = stats.get("gauges", {})
    if gauges:
        lines.append("# HELP forensic_gauges Application gauge metrics")
        lines.append("# TYPE forensic_gauges gauge")
        for key, value in sorted(gauges.items()):
            base, tag_suffix = _split_key(key)
            prom_name = _sanitize_name(f"{prefix}_{base}")
            prom_tags = _parse_tags(tag_suffix)
            lines.append(f"{prom_name}{prom_tags} {value}")

    # ------------------------------------------------------------------
    # Histograms — exposed as Prometheus summaries (no client-side buckets)
    # ------------------------------------------------------------------
    histograms: Dict[str, dict] = stats.get("histograms", {})
    if histograms:
        for key, snap in sorted(histograms.items()):
            base, tag_suffix = _split_key(key)
            prom_base = _sanitize_name(f"{prefix}_{base}")
            prom_tags = _parse_tags(tag_suffix)
            # Insert tag-separator handling
            if prom_tags:
                inner = prom_tags[1:-1]  # strip braces
                q50_tags = "{" + inner + ',quantile="0.5"}'
                q95_tags = "{" + inner + ',quantile="0.95"}'
                q99_tags = "{" + inner + ',quantile="0.99"}'
            else:
                q50_tags = '{quantile="0.5"}'
                q95_tags = '{quantile="0.95"}'
                q99_tags = '{quantile="0.99"}'

            lines.append(f"# HELP {prom_base} Histogram of {base} observations")
            lines.append(f"# TYPE {prom_base} summary")
            lines.append(f"{prom_base}{q50_tags} {snap['p50']}")
            lines.append(f"{prom_base}{q95_tags} {snap['p95']}")
            lines.append(f"{prom_base}{q99_tags} {snap['p99']}")
            lines.append(f"{prom_base}_sum{prom_tags} {snap['sum']}")
            lines.append(f"{prom_base}_count{prom_tags} {snap['count']}")

    # Prometheus text format ends with a newline
    return "\n".join(lines) + "\n" if lines else "# no metrics\n"
