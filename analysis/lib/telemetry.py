from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path

from .common import iter_jsonl


def _iter_metric_entries(metrics_files: list[Path]):
    for path in metrics_files:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, list):
                    items = payload
                elif isinstance(payload, dict):
                    items = [payload]
                else:
                    continue
                for item in items:
                    if isinstance(item, dict):
                        yield item


def _summarize_metric_series(metrics_files: list[Path]) -> dict[str, dict]:
    series: dict[str, list[float]] = defaultdict(list)
    units: dict[str, str] = {}
    for item in _iter_metric_entries(metrics_files):
        metric_name = str(item.get("metric_name") or "")
        if not metric_name:
            continue
        units[metric_name] = str(item.get("unit") or "")
        for data_point in item.get("data_points") or []:
            value = data_point.get("value")
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            series[metric_name].append(numeric)
    summary = {}
    for metric_name, values in series.items():
        if not values:
            continue
        ordered = sorted(values)
        p95_index = min(len(ordered) - 1, max(0, int(round(0.95 * (len(ordered) - 1)))))
        summary[metric_name] = {
            "count": len(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "p95": ordered[p95_index],
            "unit": units.get(metric_name, ""),
        }
    return summary


def summarize_telemetry(trace_files: list[Path], metrics_files: list[Path]) -> dict:
    agent_counts: Counter[str] = Counter()
    span_name_counts: Counter[str] = Counter()
    wall_time_by_agent: defaultdict[str, float] = defaultdict(float)
    llm_cost_usd = 0.0
    llm_wall_time_seconds = 0.0
    llm_cached_input_tokens = 0
    llm_cached_output_tokens = 0
    llm_cached_input_tokens_seen = False
    llm_cached_output_tokens_seen = False
    span_count = 0
    timestamps: list[int] = []

    for path in trace_files:
        for item in iter_jsonl(path):
            attrs = item.get("attributes") or {}
            agent = str(item.get("agent_name") or attrs.get("agent.name") or "unknown")
            op_name = str(attrs.get("gen_ai.operation.name") or item.get("name") or "unknown")
            agent_counts[agent] += 1
            span_name_counts[f"{agent}.{op_name}"] += 1
            span_count += 1
            duration_ns = int(item.get("duration_ns") or 0)
            wall_time_by_agent[agent] += duration_ns / 1_000_000_000
            llm_cost_usd += float(attrs.get("llm.cost_usd") or 0.0)
            llm_wall_time_seconds += float(attrs.get("llm.call_time_seconds") or 0.0)
            if attrs.get("llm.usage.cached_input_tokens") is not None:
                llm_cached_input_tokens_seen = True
                llm_cached_input_tokens += int(attrs.get("llm.usage.cached_input_tokens") or 0)
            if attrs.get("llm.usage.cached_output_tokens") is not None:
                llm_cached_output_tokens_seen = True
                llm_cached_output_tokens += int(attrs.get("llm.usage.cached_output_tokens") or 0)
            start_time = item.get("start_time")
            end_time = item.get("end_time")
            if start_time:
                timestamps.append(int(start_time))
            if end_time:
                timestamps.append(int(end_time))

    trace_wall_time_seconds = None
    if timestamps:
        trace_wall_time_seconds = (max(timestamps) - min(timestamps)) / 1_000_000_000
    metric_summary = _summarize_metric_series(metrics_files)
    cpu = metric_summary.get("process.cpu.usage") or {}
    memory = metric_summary.get("process.memory.usage_bytes") or {}

    return {
        "trace_file_count": len(trace_files),
        "metrics_file_count": len(metrics_files),
        "trace_bytes": sum(path.stat().st_size for path in trace_files),
        "metrics_bytes": sum(path.stat().st_size for path in metrics_files),
        "span_count": span_count,
        "agent_count": len(agent_counts),
        "agent_counts": dict(agent_counts),
        "span_name_counts": dict(span_name_counts),
        "llm_cost_usd": llm_cost_usd,
        "llm_cached_input_tokens": (
            llm_cached_input_tokens if llm_cached_input_tokens_seen else None
        ),
        "llm_cached_output_tokens": (
            llm_cached_output_tokens if llm_cached_output_tokens_seen else None
        ),
        "llm_wall_time_seconds": llm_wall_time_seconds,
        "trace_wall_time_seconds": trace_wall_time_seconds,
        "wall_time_seconds_by_agent": dict(wall_time_by_agent),
        "metrics": metric_summary,
        "cpu_usage_avg": cpu.get("avg"),
        "cpu_usage_max": cpu.get("max"),
        "memory_usage_avg_bytes": memory.get("avg"),
        "memory_usage_max_bytes": memory.get("max"),
    }


def ordered_labels(trace_files: list[Path]) -> list[str]:
    spans: list[tuple[int, str]] = []
    for path in trace_files:
        for item in iter_jsonl(path):
            attrs = item.get("attributes") or {}
            agent = str(item.get("agent_name") or attrs.get("agent.name") or "unknown")
            operation = str(attrs.get("gen_ai.operation.name") or item.get("name") or "unknown")
            spans.append((int(item.get("start_time") or 0), f"{agent}:{operation}"))
    spans.sort(key=lambda entry: entry[0])
    return [label for _, label in spans]


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    if not union:
        return 1.0
    return len(left & right) / len(union)


def lcs_length(left: list[str], right: list[str]) -> int:
    if not left or not right:
        return 0
    previous = [0] * (len(right) + 1)
    for left_item in left:
        current = [0]
        for idx, right_item in enumerate(right, start=1):
            if left_item == right_item:
                current.append(previous[idx - 1] + 1)
            else:
                current.append(max(previous[idx], current[-1]))
        previous = current
    return previous[-1]


def normalized_lcs(left: list[str], right: list[str]) -> float:
    denom = max(len(left), len(right))
    if denom == 0:
        return 1.0
    return lcs_length(left, right) / denom


def pairwise_call_graph_similarity(runs) -> list[dict]:
    labels_by_run = {}
    for run in runs:
        trace_files = sorted((run.path / "telemetry").glob("*.otel.jsonl"))
        labels_by_run[run] = ordered_labels(trace_files)
    rows = []
    ordered_runs = list(runs)
    for idx, left in enumerate(ordered_runs):
        for right in ordered_runs[idx + 1 :]:
            left_labels = labels_by_run[left]
            right_labels = labels_by_run[right]
            if not left_labels and not right_labels:
                continue
            rows.append(
                {
                    "left_run": left.run_leaf,
                    "right_run": right.run_leaf,
                    "left_span_count": len(left_labels),
                    "right_span_count": len(right_labels),
                    "label_jaccard": jaccard(set(left_labels), set(right_labels)),
                    "normalized_lcs": normalized_lcs(left_labels, right_labels),
                }
            )
    return rows
