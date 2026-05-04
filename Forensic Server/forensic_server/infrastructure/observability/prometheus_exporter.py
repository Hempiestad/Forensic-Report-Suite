from __future__ import annotations

import re
from typing import Dict

from .metrics_collector import MetricsCollector, get_metrics


_INVALID_CHARS = re.compile(r"[^a-zA-Z0-9_:]")
_TAG_RE = re.compile(r"^\{(.+)\}$")


def _sanitize_name(name: str) -> str:
    return _INVALID_CHARS.sub("_", name)


def _parse_tags(tag_suffix: str) -> str:
    match = _TAG_RE.match(tag_suffix)
    if not match:
        return ""
    pairs = match.group(1).split(",")
    prom_pairs = []
    for pair in pairs:
        if "=" in pair:
            key, value = pair.split("=", 1)
            prom_pairs.append(f'{key.strip()}="{value.strip()}"')
    return "{" + ",".join(prom_pairs) + "}" if prom_pairs else ""


def _split_key(key: str) -> tuple[str, str]:
    brace = key.find("{")
    if brace == -1:
        return key, ""
    return key[:brace], key[brace:]


def generate_prometheus_text(collector: MetricsCollector | None = None) -> str:
    collector = collector or get_metrics()
    stats = collector.get_stats()
    lines = []
    prefix = "forensic"

    counters: Dict[str, int] = stats.get("counters", {})
    if counters:
        lines.append("# HELP forensic_counters_total Application counter metrics")
        lines.append("# TYPE forensic_counters_total counter")
        for key, value in sorted(counters.items()):
            base, tag_suffix = _split_key(key)
            prom_name = _sanitize_name(f"{prefix}_{base}_total")
            prom_tags = _parse_tags(tag_suffix)
            lines.append(f"{prom_name}{prom_tags} {value}")

    gauges: Dict[str, float] = stats.get("gauges", {})
    if gauges:
        lines.append("# HELP forensic_gauges Application gauge metrics")
        lines.append("# TYPE forensic_gauges gauge")
        for key, value in sorted(gauges.items()):
            base, tag_suffix = _split_key(key)
            prom_name = _sanitize_name(f"{prefix}_{base}")
            prom_tags = _parse_tags(tag_suffix)
            lines.append(f"{prom_name}{prom_tags} {value}")

    histograms: Dict[str, dict] = stats.get("histograms", {})
    if histograms:
        for key, snap in sorted(histograms.items()):
            base, tag_suffix = _split_key(key)
            prom_base = _sanitize_name(f"{prefix}_{base}")
            prom_tags = _parse_tags(tag_suffix)
            if prom_tags:
                inner = prom_tags[1:-1]
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

    return "\n".join(lines) + "\n" if lines else "# no metrics\n"
