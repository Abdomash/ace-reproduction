from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .common import iter_jsonl


TOKEN_FIELDS = {
    "prompt_tokens": ("prompt_num_tokens", "gen_ai.usage.input_tokens"),
    "response_tokens": ("response_num_tokens", "gen_ai.usage.output_tokens"),
    "reasoning_tokens": ("reasoning_num_tokens", "gen_ai.usage.reasoning_tokens"),
    "total_tokens": ("total_num_tokens", "gen_ai.usage.total_tokens"),
}


def _empty_role(cost_source: str) -> dict:
    return {
        "calls": 0,
        "prompt_tokens": 0,
        "response_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
        "cost_source": cost_source,
    }


def _update_role(row: dict, item: dict, field_names: dict[str, str]) -> None:
    row["calls"] += 1
    row["prompt_tokens"] += int(item.get(field_names["prompt_tokens"]) or 0)
    row["response_tokens"] += int(item.get(field_names["response_tokens"]) or 0)
    row["reasoning_tokens"] += int(item.get(field_names["reasoning_tokens"]) or 0)
    row["total_tokens"] += int(item.get(field_names["total_tokens"]) or 0)
    row["cost_usd"] += float(item.get(field_names["cost_usd"]) or 0.0)


def _rollup_roles(roles: dict[str, dict], cost_source: str) -> dict:
    total = _empty_role(cost_source)
    for role_data in roles.values():
        total["calls"] += role_data["calls"]
        total["prompt_tokens"] += role_data["prompt_tokens"]
        total["response_tokens"] += role_data["response_tokens"]
        total["reasoning_tokens"] += role_data["reasoning_tokens"]
        total["total_tokens"] += role_data["total_tokens"]
        total["cost_usd"] += role_data["cost_usd"]
    return {"roles": dict(roles), "total": total}


def _from_compact_jsonl(path: Path) -> dict | None:
    if not path.exists():
        return None
    roles: dict[str, dict] = defaultdict(lambda: _empty_role("compact_jsonl"))
    found = False
    for item in iter_jsonl(path):
        found = True
        role = str(item.get("role") or "unknown")
        _update_role(
            roles[role],
            item,
            {
                "prompt_tokens": "prompt_num_tokens",
                "response_tokens": "response_num_tokens",
                "reasoning_tokens": "reasoning_num_tokens",
                "total_tokens": "total_num_tokens",
                "cost_usd": "cost_usd",
            },
        )
    return _rollup_roles(roles, "compact_jsonl") if found else None


def _from_telemetry(trace_files: list[Path]) -> dict | None:
    if not trace_files:
        return None
    roles: dict[str, dict] = defaultdict(lambda: _empty_role("telemetry"))
    found = False
    for path in trace_files:
        for item in iter_jsonl(path):
            attrs = item.get("attributes") or {}
            if not (
                "gen_ai.usage.total_tokens" in attrs
                or item.get("name") == "call_llm"
                or attrs.get("gen_ai.operation.name") == "call_llm"
            ):
                continue
            found = True
            role = str(item.get("agent_name") or attrs.get("agent.name") or "unknown")
            _update_role(
                roles[role],
                {
                    "prompt_num_tokens": attrs.get("gen_ai.usage.input_tokens"),
                    "response_num_tokens": attrs.get("gen_ai.usage.output_tokens"),
                    "reasoning_num_tokens": attrs.get("gen_ai.usage.reasoning_tokens"),
                    "total_num_tokens": attrs.get("gen_ai.usage.total_tokens"),
                    "cost_usd": attrs.get("llm.cost_usd"),
                },
                {
                    "prompt_tokens": "prompt_num_tokens",
                    "response_tokens": "response_num_tokens",
                    "reasoning_tokens": "reasoning_num_tokens",
                    "total_tokens": "total_num_tokens",
                    "cost_usd": "cost_usd",
                },
            )
    return _rollup_roles(roles, "telemetry") if found else None


def summarize_costs(
    run_dir: Path,
    *,
    compact_jsonl: Path | None = None,
    trace_files: list[Path] | None = None,
) -> dict:
    return (
        (compact_jsonl and _from_compact_jsonl(compact_jsonl))
        or _from_telemetry(trace_files or [])
        or {"roles": {}, "total": _empty_role("unavailable")}
    )
