#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
            count += 1
    return count


def iter_jsonl(path: Path) -> Iterable[Any]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                yield {"_parse_error": True, "path": str(path), "line_number": line_number}


def file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += file_size(item)
    return total


def stage_run_dirs(run_dir: Path) -> list[tuple[str | None, Path]]:
    direct_tasks = run_dir / "tasks"
    if direct_tasks.exists():
        return [(None, run_dir)]
    stages_dir = run_dir / "stages"
    if not stages_dir.exists():
        return []
    stage_dirs: list[tuple[str | None, Path]] = []
    for stage_dir in sorted(stages_dir.iterdir()):
        if stage_dir.is_dir():
            stage_dirs.append((stage_dir.name, stage_dir))
    return stage_dirs


def stage_task_key(stage_name: str | None, task_id: str) -> str:
    return f"{stage_name}:{task_id}" if stage_name else task_id


def appworld_bin(appworld_root: Path) -> str:
    candidate = appworld_root / ".venv" / "bin" / "appworld"
    if candidate.exists():
        return str(candidate)
    return "appworld"


def maybe_evaluate(
    *,
    run_dir: Path,
    appworld_root: Path,
    experiment_name: str,
    dataset: str,
    force: bool,
) -> dict[str, Any]:
    evaluation_path = run_dir / "evaluations" / f"{dataset}.json"
    if evaluation_path.exists() and not force:
        return {"ran": False, "reason": "already_exists", "path": str(evaluation_path)}

    env = os.environ.copy()
    env["APPWORLD_EXPERIMENT_OUTPUTS"] = str(run_dir.parent)
    command = [
        appworld_bin(appworld_root),
        "evaluate",
        experiment_name,
        dataset,
        "--root",
        str(appworld_root),
    ]
    try:
        result = subprocess.run(
            command,
            cwd=str(appworld_root),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    except FileNotFoundError as exc:
        return {"ran": False, "error": str(exc), "command": command}

    return {
        "ran": True,
        "returncode": result.returncode,
        "command": command,
        "output_tail": result.stdout[-4000:],
        "path": str(evaluation_path),
    }


def summarize_evaluation(run_dir: Path, dataset: str) -> dict[str, Any]:
    evaluation_path = run_dir / "evaluations" / f"{dataset}.json"
    if not evaluation_path.exists():
        return {"available": False, "path": str(evaluation_path)}

    data = read_json(evaluation_path)
    individual = data.get("individual", {})
    success_counter = Counter()
    difficulty = defaultdict(lambda: {"passed": 0, "total": 0})
    failures = []
    scenario_results = defaultdict(list)

    for task_id, item in individual.items():
        success = bool(item.get("success"))
        success_counter[str(success)] += 1
        diff = str(item.get("difficulty", "unknown"))
        difficulty[diff]["total"] += 1
        difficulty[diff]["passed"] += int(success)
        scenario_results[task_id.rsplit("_", 1)[0]].append(success)
        if not success:
            failures.append(
                {
                    "task_id": task_id,
                    "difficulty": item.get("difficulty"),
                    "num_tests": item.get("num_tests"),
                    "num_passes": len(item.get("passes", [])),
                    "failures": item.get("failures", []),
                }
            )

    scenarios_total = len(scenario_results)
    scenarios_passed = sum(1 for values in scenario_results.values() if all(values))
    return {
        "available": True,
        "path": str(evaluation_path),
        "aggregate": data.get("aggregate", {}),
        "task_count": len(individual),
        "task_success_count": success_counter.get("True", 0),
        "task_failure_count": success_counter.get("False", 0),
        "scenario_count": scenarios_total,
        "scenario_success_count": scenarios_passed,
        "scenario_failure_count": scenarios_total - scenarios_passed,
        "difficulty": dict(sorted(difficulty.items())),
        "failure_count": len(failures),
        "failures": failures,
    }


def summarize_full_run_evaluations(run_dir: Path) -> dict[str, Any]:
    stage_specs = {
        "eval-normal": "test_normal",
        "eval-challenge": "test_challenge",
    }
    stages: dict[str, Any] = {}
    task_count = 0
    failure_count = 0
    available = False
    for stage_name, dataset in stage_specs.items():
        stage_dir = run_dir / "stages" / stage_name
        summary = summarize_evaluation(stage_dir, dataset)
        stages[stage_name] = summary
        available = available or bool(summary.get("available"))
        task_count += int(summary.get("task_count") or 0)
        failure_count += int(summary.get("failure_count") or 0)
    normal_aggregate = ((stages.get("eval-normal") or {}).get("aggregate") or {})
    challenge_aggregate = ((stages.get("eval-challenge") or {}).get("aggregate") or {})
    return {
        "available": available,
        "aggregate": normal_aggregate,
        "challenge_aggregate": challenge_aggregate,
        "task_count": task_count,
        "failure_count": failure_count,
        "stages": stages,
    }


def compact_lm_call(task_id: str, row: dict[str, Any]) -> dict[str, Any]:
    output = row.get("output") if isinstance(row.get("output"), dict) else {}
    usage = output.get("usage") if isinstance(output.get("usage"), dict) else {}
    prompt_details = usage.get("prompt_tokens_details") if isinstance(usage.get("prompt_tokens_details"), dict) else {}
    arguments = row.get("input") if isinstance(row.get("input"), dict) else {}
    return {
        "task_id": task_id,
        "id": row.get("id"),
        "role": row.get("role"),
        "model": row.get("model") or arguments.get("model"),
        "call_time": row.get("call_time") or output.get("call_time"),
        "wall_time_seconds": row.get("wall_time_seconds") or output.get("wall_time_seconds"),
        "prompt_num_tokens": row.get("prompt_num_tokens")
        or output.get("prompt_num_tokens")
        or usage.get("prompt_tokens")
        or usage.get("input_tokens"),
        "response_num_tokens": row.get("response_num_tokens")
        or output.get("response_num_tokens")
        or usage.get("completion_tokens")
        or usage.get("output_tokens"),
        "reasoning_num_tokens": row.get("reasoning_num_tokens")
        or output.get("reasoning_num_tokens"),
        "total_num_tokens": row.get("total_num_tokens")
        or output.get("total_num_tokens")
        or usage.get("total_tokens"),
        "cached_input_tokens": (
            row.get("cached_input_tokens")
            if row.get("cached_input_tokens") is not None
            else output.get("cached_input_tokens")
            if output.get("cached_input_tokens") is not None
            else prompt_details.get("cached_tokens")
        ),
        "cached_output_tokens": (
            row.get("cached_output_tokens")
            if row.get("cached_output_tokens") is not None
            else output.get("cached_output_tokens")
            if output.get("cached_output_tokens") is not None
            else prompt_details.get("cache_write_tokens")
        ),
        "cost_usd": row.get("cost_usd") or output.get("cost_usd") or output.get("cost"),
        "cost_source": row.get("cost_source") or output.get("cost_source"),
        "prompt_length": row.get("prompt_length"),
        "response_length": row.get("response_length"),
    }


def summarize_lm_calls(run_dir: Path, summary_dir: Path) -> dict[str, Any]:
    compact_path = summary_dir / "llm_calls.compact.jsonl"
    stage_dirs = stage_run_dirs(run_dir)
    compact_rows = []
    role_counts = Counter()
    model_counts = Counter()
    totals = Counter()
    cache_presence = Counter()
    task_call_counts = Counter()
    parse_errors = 0

    raw_entries: list[tuple[str | None, Path, str]] = []
    for stage_name, stage_dir in stage_dirs:
        detailed_paths = sorted((stage_dir / "detailed_llm_logs").glob("*.json"))
        if detailed_paths:
            raw_entries.extend((stage_name, path, "detailed") for path in detailed_paths)
        else:
            raw_entries.extend(
                (stage_name, path, "task")
                for path in sorted((stage_dir / "tasks").glob("*/logs/lm_calls.jsonl"))
            )

    if not raw_entries and compact_path.exists():
        for row in iter_jsonl(compact_path):
            if not row.get("_parse_error"):
                compact_rows.append(row)

    for stage_name, path, source_kind in raw_entries:
        if source_kind == "detailed":
            task_id = stage_task_key(stage_name, str(path.stem))
            try:
                data = read_json(path)
            except Exception:
                data = None
            rows = [data] if isinstance(data, dict) else []
        else:
            task_id = stage_task_key(stage_name, path.parts[-3])
            rows = iter_jsonl(path)
        for row in rows:
            if row.get("_parse_error"):
                parse_errors += 1
                continue
            compact = compact_lm_call(task_id, row)
            compact_rows.append(compact)
            task_call_counts[task_id] += 1
            if compact.get("role"):
                role_counts[str(compact["role"])] += 1
            if compact.get("model"):
                model_counts[str(compact["model"])] += 1
            for key in (
                "prompt_num_tokens",
                "response_num_tokens",
                "reasoning_num_tokens",
                "total_num_tokens",
                "cached_input_tokens",
                "cached_output_tokens",
                "cost_usd",
                "call_time",
                "wall_time_seconds",
            ):
                value = compact.get(key)
                if value is None:
                    continue
                if key in {"cached_input_tokens", "cached_output_tokens"}:
                    cache_presence[key] += 1
                try:
                    totals[key] += float(value)
                except (TypeError, ValueError):
                    pass

    role_counts = Counter()
    model_counts = Counter()
    totals = Counter()
    task_call_counts = Counter()
    for compact in compact_rows:
        task_id = str(compact.get("task_id", "unknown"))
        task_call_counts[task_id] += 1
        if compact.get("role"):
            role_counts[str(compact["role"])] += 1
        if compact.get("model"):
            model_counts[str(compact["model"])] += 1
        for key in (
            "prompt_num_tokens",
            "response_num_tokens",
            "reasoning_num_tokens",
            "total_num_tokens",
            "cached_input_tokens",
            "cached_output_tokens",
            "cost_usd",
            "call_time",
            "wall_time_seconds",
        ):
            value = compact.get(key)
            if value is None:
                continue
            if key in {"cached_input_tokens", "cached_output_tokens"}:
                cache_presence[key] += 1
            try:
                totals[key] += float(value)
            except (TypeError, ValueError):
                pass

    write_jsonl(compact_path, compact_rows)
    costs = [float(row["cost_usd"]) for row in compact_rows if row.get("cost_usd") is not None]
    totals_dict = dict(totals)
    for key in ("cached_input_tokens", "cached_output_tokens"):
        totals_dict[key] = totals[key] if cache_presence[key] else None
    return {
        "call_count": len(compact_rows),
        "parse_errors": parse_errors,
        "compact_path": str(compact_path),
        "role_counts": dict(role_counts),
        "model_counts": dict(model_counts),
        "task_call_counts": dict(task_call_counts),
        "totals": totals_dict,
        "zero_cost_call_count": sum(1 for cost in costs if cost == 0),
        "nonzero_cost_call_count": sum(1 for cost in costs if cost != 0),
    }


def summarize_api_calls(run_dir: Path, summary_dir: Path) -> dict[str, Any]:
    compact_path = summary_dir / "api_calls.summary.jsonl"
    task_counts = {}
    endpoint_counts = Counter()
    method_counts = Counter()
    parse_errors = 0
    rows = []

    raw_entries = []
    for stage_name, stage_dir in stage_run_dirs(run_dir):
        raw_entries.extend(
            (stage_name, path) for path in sorted((stage_dir / "tasks").glob("*/logs/api_calls.jsonl"))
        )

    if not raw_entries and compact_path.exists():
        for row in iter_jsonl(compact_path):
            if not row.get("_parse_error"):
                rows.append(row)
                task_id = str(row.get("task_id", "unknown"))
                count = int(row.get("api_call_count") or 0)
                task_counts[task_id] = count
                for endpoint, value in (row.get("endpoint_counts") or {}).items():
                    endpoint_counts[str(endpoint)] += int(value)

    for stage_name, path in raw_entries:
        task_id = stage_task_key(stage_name, path.parts[-3])
        count = 0
        per_task_endpoint_counts = Counter()
        for row in iter_jsonl(path):
            if row.get("_parse_error"):
                parse_errors += 1
                continue
            count += 1
            endpoint = str(row.get("url", "unknown"))
            method = str(row.get("method", "unknown"))
            endpoint_counts[endpoint] += 1
            method_counts[method] += 1
            per_task_endpoint_counts[endpoint] += 1
        task_counts[task_id] = count
        rows.append(
            {
                "task_id": task_id,
                "api_call_count": count,
                "endpoint_counts": dict(per_task_endpoint_counts),
            }
        )

    write_jsonl(compact_path, rows)
    return {
        "api_call_count": sum(task_counts.values()),
        "parse_errors": parse_errors,
        "compact_path": str(compact_path),
        "method_counts": dict(method_counts),
        "endpoint_counts": dict(endpoint_counts.most_common()),
        "task_call_counts": task_counts,
    }


def iter_metric_records(path: Path) -> Iterable[dict[str, Any]]:
    for row in iter_jsonl(path):
        if isinstance(row, list):
            for item in row:
                if isinstance(item, dict):
                    yield item
        elif isinstance(row, dict):
            yield row


def summarize_telemetry(run_dir: Path) -> dict[str, Any]:
    metric_summary: dict[str, dict[str, Any]] = {}
    metric_file_count = 0
    trace_file_count = 0
    span_count = 0
    span_name_counts = Counter()
    agent_counts = Counter()
    llm_totals = Counter()
    llm_cache_presence = Counter()
    wall_time_by_agent = Counter()

    for _, stage_dir in stage_run_dirs(run_dir):
        telemetry_dir = stage_dir / "telemetry"
        for path in sorted(telemetry_dir.glob("*.metrics.jsonl")):
            metric_file_count += 1
            for record in iter_metric_records(path):
                name = record.get("metric_name")
                if not name:
                    continue
                values = []
                for point in record.get("data_points", []):
                    if isinstance(point, dict) and point.get("value") is not None:
                        try:
                            values.append(float(point["value"]))
                        except (TypeError, ValueError):
                            pass
                if not values:
                    continue
                item = metric_summary.setdefault(
                    name,
                    {"count": 0, "sum": 0.0, "min": None, "max": None, "unit": record.get("unit")},
                )
                item["count"] += len(values)
                item["sum"] += sum(values)
                item["min"] = min(values) if item["min"] is None else min(item["min"], min(values))
                item["max"] = max(values) if item["max"] is None else max(item["max"], max(values))

    for item in metric_summary.values():
        item["avg"] = item["sum"] / item["count"] if item["count"] else None

    for _, stage_dir in stage_run_dirs(run_dir):
        telemetry_dir = stage_dir / "telemetry"
        for path in sorted(telemetry_dir.glob("*.otel.jsonl")):
            trace_file_count += 1
            for row in iter_jsonl(path):
                if row.get("_parse_error"):
                    continue
                span_count += 1
                span_name_counts[str(row.get("name", "unknown"))] += 1
                agent = row.get("agent_name") or (row.get("attributes") or {}).get("agent.name")
                if agent:
                    agent_counts[str(agent)] += 1
                attrs = row.get("attributes") or {}
                if row.get("name") == "ace.call_llm":
                    for key, target in (
                        ("gen_ai.usage.input_tokens", "prompt_num_tokens"),
                        ("gen_ai.usage.output_tokens", "response_num_tokens"),
                        ("gen_ai.usage.reasoning_tokens", "reasoning_num_tokens"),
                        ("gen_ai.usage.total_tokens", "total_num_tokens"),
                        ("llm.usage.cached_input_tokens", "cached_input_tokens"),
                        ("llm.usage.cached_output_tokens", "cached_output_tokens"),
                        ("llm.cost_usd", "cost_usd"),
                        ("llm.cost.usd", "cost_usd_legacy"),
                        ("llm.call_time_seconds", "call_time_seconds"),
                        ("llm.wall_time_seconds", "wall_time_seconds"),
                        ("wall_time_seconds", "span_wall_time_seconds"),
                    ):
                        value = attrs.get(key)
                        if value is None:
                            continue
                        if target in {"cached_input_tokens", "cached_output_tokens"}:
                            llm_cache_presence[target] += 1
                        try:
                            llm_totals[target] += float(value)
                        except (TypeError, ValueError):
                            pass
                wall_time = attrs.get("wall_time_seconds") or attrs.get("duration.wall_time_seconds")
                if agent and wall_time is not None:
                    try:
                        wall_time_by_agent[str(agent)] += float(wall_time)
                    except (TypeError, ValueError):
                        pass

    llm_totals_dict = dict(llm_totals)
    for key in ("cached_input_tokens", "cached_output_tokens"):
        llm_totals_dict[key] = llm_totals[key] if llm_cache_presence[key] else None

    return {
        "metric_file_count": metric_file_count,
        "trace_file_count": trace_file_count,
        "span_count": span_count,
        "span_name_counts": dict(span_name_counts),
        "agent_counts": dict(agent_counts),
        "metrics": metric_summary,
        "llm_totals": llm_totals_dict,
        "wall_time_seconds_by_agent": dict(wall_time_by_agent),
    }


def prune_raw_task_details(run_dir: Path) -> dict[str, Any]:
    removed = []
    bytes_removed = 0
    tasks_dir = run_dir / "tasks"
    if not tasks_dir.exists():
        return {"removed_count": 0, "bytes_removed": 0, "removed": []}

    for task_dir in sorted(tasks_dir.iterdir()):
        if not task_dir.is_dir():
            continue
        for name in ("dbs", "checkpoints"):
            target = task_dir / name
            if target.exists():
                bytes_removed += directory_size(target)
                shutil.rmtree(target)
                removed.append(str(target))
        for relative in (
            "logs/environment_io.md",
            "logs/loggger.log",
            "logs/lm_calls.jsonl",
            "logs/api_calls.jsonl",
        ):
            target = task_dir / relative
            if target.exists():
                bytes_removed += file_size(target)
                target.unlink()
                removed.append(str(target))

    detailed_logs_dir = run_dir / "detailed_llm_logs"
    if detailed_logs_dir.exists():
        bytes_removed += directory_size(detailed_logs_dir)
        shutil.rmtree(detailed_logs_dir)
        removed.append(str(detailed_logs_dir))

    return {
        "removed_count": len(removed),
        "bytes_removed": bytes_removed,
        "removed": removed,
    }


def build_run_summary(run_dir: Path, dataset: str) -> dict[str, Any]:
    stage_count = len(stage_run_dirs(run_dir))
    task_directory_count = 0
    tasks_size_bytes = 0
    telemetry_size_bytes = 0
    evaluation_size_bytes = directory_size(run_dir / "evaluations")
    for _, stage_dir in stage_run_dirs(run_dir):
        task_directory_count += len([p for p in (stage_dir / "tasks").glob("*") if p.is_dir()])
        tasks_size_bytes += directory_size(stage_dir / "tasks")
        telemetry_size_bytes += directory_size(stage_dir / "telemetry")
        evaluation_size_bytes += directory_size(stage_dir / "evaluations")
    summary = {
        "run_dir": str(run_dir),
        "dataset": dataset,
        "mode": "full" if stage_count else None,
        "total_size_bytes": directory_size(run_dir),
        "tasks_size_bytes": tasks_size_bytes or directory_size(run_dir / "tasks"),
        "telemetry_size_bytes": telemetry_size_bytes or directory_size(run_dir / "telemetry"),
        "evaluation_size_bytes": evaluation_size_bytes,
        "task_directory_count": task_directory_count,
        "stage_count": stage_count,
    }
    run_state = load_json(run_dir / "run_state.json") or {}
    for key in (
        "status",
        "checkpointing_enabled",
        "resume_enabled",
        "has_checkpoints",
        "resume_count",
        "current_stage",
        "last_completed_stage",
        "active_runtime_seconds",
        "started_at",
        "last_resumed_at",
        "last_checkpoint_at",
        "completed_at",
        "failure_reason",
    ):
        summary[key] = run_state.get(key)
    return summary


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Export compact summaries from an AppWorld run.")
    parser.add_argument("--run-dir", required=True, type=Path, help="Path to the AppWorld experiment run directory.")
    parser.add_argument("--dataset", default="dev", help="Dataset name used for AppWorld evaluation.")
    parser.add_argument("--experiment-name", help="AppWorld experiment name. Defaults to run directory name.")
    parser.add_argument("--appworld-root", type=Path, default=repo_root / "projects" / "ace-appworld")
    parser.add_argument("--summary-dir-name", default="summary")
    parser.add_argument("--evaluate", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--force-evaluate", action="store_true")
    parser.add_argument("--prune", action=argparse.BooleanOptionalAction, default=False)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    if not run_dir.exists():
        print(f"AppWorld run directory does not exist; skipping summary export: {run_dir}")
        return 0
    if not (run_dir / "tasks").exists() and not (run_dir / "stages").exists():
        print(f"AppWorld run directory has no tasks/ directory; skipping summary export: {run_dir}")
        return 0

    experiment_name = args.experiment_name or run_dir.name
    summary_dir = run_dir / args.summary_dir_name
    summary_dir.mkdir(parents=True, exist_ok=True)

    evaluation_run = {"ran": False, "reason": "disabled"}
    if args.evaluate:
        evaluation_run = maybe_evaluate(
            run_dir=run_dir,
            appworld_root=args.appworld_root.resolve(),
            experiment_name=experiment_name,
            dataset=args.dataset,
            force=args.force_evaluate,
        )
        if evaluation_run.get("ran") and evaluation_run.get("returncode") not in (0, None):
            print("AppWorld evaluation failed; continuing with available artifacts.", file=sys.stderr)

    if (run_dir / "stages").exists():
        evaluation_summary = summarize_full_run_evaluations(run_dir)
        run_summary_dataset = "full"
    else:
        evaluation_summary = summarize_evaluation(run_dir, args.dataset)
        run_summary_dataset = args.dataset
    llm_summary = summarize_lm_calls(run_dir, summary_dir)
    api_summary = summarize_api_calls(run_dir, summary_dir)
    telemetry_summary = summarize_telemetry(run_dir)
    run_summary = build_run_summary(run_dir, run_summary_dataset)

    write_json(summary_dir / "evaluation_summary.json", evaluation_summary)
    write_json(summary_dir / "llm_summary.json", llm_summary)
    write_json(summary_dir / "api_summary.json", api_summary)
    write_json(summary_dir / "telemetry_summary.json", telemetry_summary)

    prune_summary = {"removed_count": 0, "bytes_removed": 0, "removed": []}
    if args.prune:
        prune_summary = prune_raw_task_details(run_dir)

    run_summary["evaluation_run"] = evaluation_run
    run_summary["prune"] = prune_summary
    run_summary["post_export_size_bytes"] = directory_size(run_dir)
    run_summary["post_export_tasks_size_bytes"] = directory_size(run_dir / "tasks")
    run_summary["post_export_telemetry_size_bytes"] = directory_size(run_dir / "telemetry")
    run_summary["post_export_evaluation_size_bytes"] = directory_size(run_dir / "evaluations")
    write_json(summary_dir / "run_summary.json", run_summary)

    print(f"AppWorld summary written to: {summary_dir}")
    if args.prune:
        print(
            "Pruned raw task details: "
            f"{prune_summary['removed_count']} paths, {prune_summary['bytes_removed']} bytes"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
