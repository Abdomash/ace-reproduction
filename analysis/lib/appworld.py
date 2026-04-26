from __future__ import annotations

from .common import load_json
from .pricing import summarize_costs
from .telemetry import summarize_telemetry


def _difficulty_rate(difficulty: dict | None) -> float | None:
    if not difficulty:
        return None
    total = difficulty.get("total") or 0
    passed = difficulty.get("passed") or 0
    return (passed / total) if total else None


def summarize_run(run) -> dict:
    summary_dir = run.path / "summary"
    evaluation_summary = load_json(summary_dir / "evaluation_summary.json") or {}
    llm_summary = load_json(summary_dir / "llm_summary.json") or {}
    api_summary = load_json(summary_dir / "api_summary.json") or {}
    telemetry_summary = load_json(summary_dir / "telemetry_summary.json") or {}
    run_summary = load_json(summary_dir / "run_summary.json") or {}
    trace_files = sorted((run.path / "telemetry").glob("*.otel.jsonl"))
    metrics_files = sorted((run.path / "telemetry").glob("*.metrics.jsonl"))
    costs = summarize_costs(
        run.path,
        compact_jsonl=summary_dir / "llm_calls.compact.jsonl",
        trace_files=trace_files,
    )
    if costs["total"]["cost_source"] == "compact_jsonl":
        costs["total"]["cost_source"] = "summary/llm_calls.compact.jsonl"
        for role_data in costs["roles"].values():
            role_data["cost_source"] = "summary/llm_calls.compact.jsonl"
    stages = evaluation_summary.get("stages") or {}
    aggregate = evaluation_summary.get("aggregate") or ((stages.get("eval-normal") or {}).get("aggregate") or {})
    challenge_aggregate = evaluation_summary.get("challenge_aggregate") or (
        (stages.get("eval-challenge") or {}).get("aggregate") or {}
    )
    difficulty = evaluation_summary.get("difficulty") or ((stages.get("eval-normal") or {}).get("difficulty") or {})
    models_display = ", ".join(sorted((llm_summary.get("model_counts") or {}).keys()))
    summary = {
        "dataset": run_summary.get("dataset") or run_summary.get("split"),
        "task_goal_completion": aggregate.get("task_goal_completion"),
        "scenario_goal_completion": aggregate.get("scenario_goal_completion"),
        "challenge_task_goal_completion": challenge_aggregate.get("task_goal_completion"),
        "challenge_scenario_goal_completion": challenge_aggregate.get("scenario_goal_completion"),
        "failure_count": evaluation_summary.get("failure_count"),
        "task_count": evaluation_summary.get("task_count")
        or len((load_json(run.path / "evaluations" / "dev.json") or {}).get("individual", {})),
        "difficulty_1_pass_rate": _difficulty_rate(difficulty.get("1")),
        "difficulty_2_pass_rate": _difficulty_rate(difficulty.get("2")),
        "difficulty_3_pass_rate": _difficulty_rate(difficulty.get("3")),
        "status": run_summary.get("status") or "completed",
        "checkpointing_enabled": run_summary.get("checkpointing_enabled", False),
        "has_checkpoints": run_summary.get("has_checkpoints", False),
        "resume_count": run_summary.get("resume_count", 0),
        "active_runtime_seconds": run_summary.get("active_runtime_seconds"),
        "current_stage": run_summary.get("current_stage"),
        "last_completed_stage": run_summary.get("last_completed_stage"),
    }
    telemetry = summarize_telemetry(trace_files, metrics_files)
    if telemetry.get("span_count") in (None, 0):
        telemetry["span_count"] = telemetry_summary.get("span_count")
    if telemetry.get("agent_count") in (None, 0):
        telemetry["agent_count"] = len(telemetry_summary.get("agent_counts") or {})
    if telemetry.get("llm_wall_time_seconds") in (None, 0):
        telemetry["llm_wall_time_seconds"] = (telemetry_summary.get("llm_totals") or {}).get("wall_time_seconds")
    if telemetry.get("llm_cached_input_tokens") is None:
        telemetry["llm_cached_input_tokens"] = (telemetry_summary.get("llm_totals") or {}).get(
            "cached_input_tokens"
        )
    if telemetry.get("llm_cached_output_tokens") is None:
        telemetry["llm_cached_output_tokens"] = (telemetry_summary.get("llm_totals") or {}).get(
            "cached_output_tokens"
        )
    if telemetry.get("trace_wall_time_seconds") in (None, 0):
        telemetry["trace_wall_time_seconds"] = max(
            (telemetry_summary.get("wall_time_seconds_by_agent") or {}).values(),
            default=None,
        )
    if telemetry.get("llm_cost_usd") in (None, 0):
        telemetry["llm_cost_usd"] = (telemetry_summary.get("llm_totals") or {}).get("cost_usd")
    return {
        "summary": summary,
        "costs": costs,
        "telemetry": telemetry,
        "models": llm_summary.get("model_counts") or {},
        "models_display": models_display or "unknown",
        "api": api_summary,
        "llm": llm_summary,
        "run": run_summary,
        "stages": stages,
    }
