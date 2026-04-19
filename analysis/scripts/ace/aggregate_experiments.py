#!/usr/bin/env python3
"""Aggregate ACE experiment run directories into a campaign CSV."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

from _provenance import (
    finalize_output,
    existing_file_records,
    output_dir_for,
    repo_relative,
    result_label,
    result_path,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def load_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def find_campaign(path_or_name: str) -> Path:
    return result_path(path_or_name)


def find_runs(campaign_dir: Path) -> list[Path]:
    if (campaign_dir / "run_config.json").exists():
        return [campaign_dir]
    return sorted(
        p for p in campaign_dir.rglob("run_config.json")
        if "analysis" not in p.parts
        for p in [p.parent]
    )


def accuracy_result(run_dir: Path) -> dict[str, Any]:
    final_results = load_json(run_dir / "final_results.json") or {}
    candidates = [
        final_results.get("final_test_results"),
        final_results.get("test_results"),
        (final_results.get("results") or {}).get("final_test_results"),
        (final_results.get("results") or {}).get("test_results"),
        (load_json(run_dir / "final_test_results.json") or {}).get("test_results"),
        load_json(run_dir / "test_results.json"),
    ]
    for candidate in candidates:
        if isinstance(candidate, dict) and (
            "accuracy" in candidate or "total" in candidate
        ):
            total = candidate.get("total") or 0
            no_answer = candidate.get("no_answer") or 0
            return {
                "accuracy": candidate.get("accuracy"),
                "correct": candidate.get("correct"),
                "total": total,
                "no_answer": no_answer,
                "no_answer_rate": (no_answer / total) if total else None,
            }
    return {
        "accuracy": None,
        "correct": None,
        "total": None,
        "no_answer": None,
        "no_answer_rate": None,
    }


def summarize_playbook(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"chars": 0, "bullets": 0}
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "chars": len(text),
        "bullets": len(re.findall(r"\[[a-zA-Z]+-\d+\]\s+helpful=", text)),
    }


def llm_log_summary(run_dir: Path) -> dict[str, Any]:
    summary: dict[str, dict[str, float]] = {}
    for path in sorted((run_dir / "detailed_llm_logs").glob("*.json")):
        data = load_json(path)
        if not isinstance(data, dict):
            continue
        role = str(data.get("role") or "unknown")
        row = summary.setdefault(
            role,
            {
                "calls": 0,
                "prompt_tokens": 0,
                "response_tokens": 0,
                "reasoning_tokens": 0,
                "total_tokens": 0,
                "total_latency": 0.0,
                "cost_usd": 0.0,
            },
        )
        row["calls"] += 1
        row["prompt_tokens"] += int(data.get("prompt_num_tokens") or 0)
        row["response_tokens"] += int(data.get("response_num_tokens") or 0)
        row["reasoning_tokens"] += int(data.get("reasoning_num_tokens") or 0)
        row["total_tokens"] += int(data.get("total_num_tokens") or 0)
        row["total_latency"] += float(data.get("total_time") or data.get("call_time") or 0.0)
        row["cost_usd"] += float(data.get("cost_usd") or 0.0)
    return summary


def telemetry_summary(run_dir: Path) -> dict[str, Any]:
    telemetry_dir = run_dir / "telemetry"
    trace_files = sorted(telemetry_dir.glob("*.otel.jsonl"))
    metrics_files = sorted(telemetry_dir.glob("*.metrics.jsonl"))
    span_counts: dict[str, int] = {}
    for path in trace_files:
        for span in iter_jsonl(path):
            attrs = span.get("attributes") or {}
            label = f"{span.get('agent_name') or attrs.get('agent.name') or 'unknown'}:{attrs.get('gen_ai.operation.name') or span.get('name') or 'unknown'}"
            span_counts[label] = span_counts.get(label, 0) + 1
    return {
        "trace_file_count": len(trace_files),
        "metrics_file_count": len(metrics_files),
        "trace_bytes": sum(p.stat().st_size for p in trace_files),
        "metrics_bytes": sum(p.stat().st_size for p in metrics_files),
        "span_total": sum(span_counts.values()),
        "span_counts": span_counts,
    }


def flatten_role_metrics(prefix: str, logs: dict[str, Any], row: dict[str, Any]) -> None:
    total_cost = 0.0
    for role in ("generator", "reflector", "curator"):
        data = logs.get(role) or {}
        calls = int(data.get("calls") or 0)
        total_cost += float(data.get("cost_usd") or 0.0)
        row[f"{prefix}_{role}_calls"] = calls
        row[f"{prefix}_{role}_tokens"] = int(data.get("total_tokens") or 0)
        row[f"{prefix}_{role}_prompt_tokens"] = int(data.get("prompt_tokens") or 0)
        row[f"{prefix}_{role}_response_tokens"] = int(data.get("response_tokens") or 0)
        row[f"{prefix}_{role}_reasoning_tokens"] = int(data.get("reasoning_tokens") or 0)
        row[f"{prefix}_{role}_avg_latency_s"] = (
            float(data.get("total_latency") or 0.0) / calls if calls else None
        )
        row[f"{prefix}_{role}_cost_usd"] = float(data.get("cost_usd") or 0.0)
    row[f"{prefix}_total_cost_usd"] = total_cost


def summarize_run(run_dir: Path) -> dict[str, Any]:
    run_config = load_json(run_dir / "run_config.json") or {}
    path_identity = load_json(run_dir / "result_path.json") or {}
    config = run_config.get("config") or {}
    accuracy = accuracy_result(run_dir)
    initial_playbook = summarize_playbook(run_dir / "initial_playbook.txt")
    final_playbook = summarize_playbook(run_dir / "final_playbook.txt")
    if final_playbook["chars"] == 0:
        final_playbook = summarize_playbook(run_dir / "best_playbook.txt")
    telemetry = telemetry_summary(run_dir)
    row = {
        "run_id": run_config.get("run_id") or run_dir.name,
        "run_dir": repo_relative(run_dir),
        "benchmark": path_identity.get("benchmark"),
        "run_type": path_identity.get("run_type"),
        "config_slug": path_identity.get("config_slug"),
        "run_leaf": path_identity.get("run_leaf") or run_dir.name,
        "result_path": path_identity.get("run_dir") or repo_relative(run_dir),
        "task_name": run_config.get("task_name"),
        "mode": run_config.get("mode"),
        "config_name": config.get("config_name"),
        "seed": config.get("seed"),
        "api_provider": run_config.get("api_provider") or config.get("api_provider"),
        "generator_provider": run_config.get("generator_provider") or config.get("generator_provider"),
        "reflector_provider": run_config.get("reflector_provider") or config.get("reflector_provider"),
        "curator_provider": run_config.get("curator_provider") or config.get("curator_provider"),
        "generator_model": run_config.get("generator_model") or config.get("generator_model"),
        "reflector_model": run_config.get("reflector_model") or config.get("reflector_model"),
        "curator_model": run_config.get("curator_model") or config.get("curator_model"),
        **accuracy,
        "span_total": telemetry["span_total"],
        "span_counts_json": json.dumps(telemetry["span_counts"], sort_keys=True),
        "playbook_initial_chars": initial_playbook["chars"],
        "playbook_final_chars": final_playbook["chars"],
        "playbook_growth_chars": final_playbook["chars"] - initial_playbook["chars"],
        "playbook_initial_bullets": initial_playbook["bullets"],
        "playbook_final_bullets": final_playbook["bullets"],
        "playbook_growth_bullets": final_playbook["bullets"] - initial_playbook["bullets"],
        "trace_file_count": telemetry["trace_file_count"],
        "metrics_file_count": telemetry["metrics_file_count"],
        "trace_bytes": telemetry["trace_bytes"],
        "metrics_bytes": telemetry["metrics_bytes"],
    }
    flatten_role_metrics("llm", llm_log_summary(run_dir), row)
    return row


def input_paths_for_run(run_dir: Path) -> list[tuple[Path, str]]:
    paths: list[tuple[Path, str]] = [
        (run_dir / "run_config.json", "run_config"),
        (run_dir / "result_path.json", "result_path"),
        (run_dir / "final_results.json", "final_results"),
        (run_dir / "final_test_results.json", "final_test_results"),
        (run_dir / "test_results.json", "test_results"),
        (run_dir / "initial_playbook.txt", "initial_playbook"),
        (run_dir / "final_playbook.txt", "final_playbook"),
        (run_dir / "best_playbook.txt", "best_playbook"),
    ]
    paths.extend((path, "llm_log") for path in sorted((run_dir / "detailed_llm_logs").glob("*.json")))
    paths.extend((path, "telemetry_trace") for path in sorted((run_dir / "telemetry").glob("*.otel.jsonl")))
    paths.extend((path, "telemetry_metrics") for path in sorted((run_dir / "telemetry").glob("*.metrics.jsonl")))
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", help="Campaign directory path or name under ./results")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path (default: analysis/outputs/<analysis_id>/tables/experiment_summary.csv)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Analysis output directory (default: analysis/outputs/<analysis_id>)",
    )
    args = parser.parse_args()

    campaign_dir = find_campaign(args.campaign)
    runs = find_runs(campaign_dir)
    if not runs:
        raise FileNotFoundError(f"No run_config.json files found under {campaign_dir}")

    rows = [summarize_run(run_dir) for run_dir in runs]
    label = result_label(args.campaign, campaign_dir)
    analysis_id, created_at, output_dir = output_dir_for(
        "aggregate_experiments",
        label,
        args.output_dir,
    )
    tables_dir = output_dir / "tables"
    reports_dir = output_dir / "reports"
    output = args.output or (tables_dir / "experiment_summary.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary_path = reports_dir / "summary.md"
    summary_path.write_text(
        "# Experiment Summary\n\n"
        f"- Campaign: `{repo_relative(campaign_dir)}`\n"
        f"- Runs: {len(rows)}\n"
        f"- Table: `{repo_relative(output)}`\n",
        encoding="utf-8",
    )
    input_records = existing_file_records(
        item for run_dir in runs for item in input_paths_for_run(run_dir)
    )
    try:
        output_entry = output.relative_to(output_dir).as_posix()
    except ValueError:
        output_entry = repo_relative(output)
    report_rel = summary_path.relative_to(output_dir).as_posix()
    finalize_output(
        output_dir,
        analysis_id=analysis_id,
        analysis_kind="aggregate_experiments",
        label=label,
        created_at=created_at,
        command="python " + " ".join(sys.argv),
        parameters={"campaigns": [args.campaign]},
        input_records=input_records,
        outputs=[output_entry, report_rel],
    )
    print(f"Wrote {len(rows)} rows to {output}")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
