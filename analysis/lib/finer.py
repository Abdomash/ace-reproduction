from __future__ import annotations

import re

from .common import load_json
from .pricing import summarize_costs
from .telemetry import summarize_telemetry


def _split_tags(value: str) -> list[str]:
    return [part.strip().lower() for part in str(value).split(",")]


def _score_tags(prediction: str, target: str) -> tuple[int, int]:
    predicted = _split_tags(prediction)
    labels = _split_tags(target)
    if len(predicted) > len(labels):
        predicted = predicted[: len(labels)]
    elif len(predicted) < len(labels):
        predicted += [""] * (len(labels) - len(predicted))
    return sum(p == y for p, y in zip(predicted, labels)), len(labels)


def _infer_tags_per_sample(test_file: dict | None, default: int = 4) -> int:
    if not test_file:
        return default
    errors = (test_file.get("error_log") or {}).get("errors") or []
    for error in errors:
        target = error.get("ground_truth")
        if target:
            return len(_split_tags(target))
    return default


def summarize_test_file(path, tags_per_sample: int | None = None) -> dict | None:
    data = load_json(path)
    if not data:
        return None
    test_results = data.get("test_results", data)
    error_log = data.get("error_log") or {}
    errors = error_log.get("errors") or []
    total_samples = int(test_results.get("total", 0) or 0)
    exact_correct = int(test_results.get("correct", 0) or 0)
    tags_per_sample = tags_per_sample or _infer_tags_per_sample(data)
    distribution = {i: 0 for i in range(tags_per_sample + 1)}
    error_tag_correct = 0
    error_tag_total = 0
    sample_correct_tags_by_index = {
        index: tags_per_sample for index in range(total_samples)
    }
    for error in errors:
        correct, total = _score_tags(error.get("prediction", ""), error.get("ground_truth", ""))
        error_tag_correct += correct
        error_tag_total += total
        distribution.setdefault(correct, 0)
        distribution[correct] += 1
        if "index" in error:
            sample_correct_tags_by_index[int(error["index"])] = correct
    tag_total = total_samples * tags_per_sample if total_samples else error_tag_total
    tag_correct = exact_correct * tags_per_sample + error_tag_correct
    no_answer = int(test_results.get("no_answer", 0) or 0)
    distribution.setdefault(tags_per_sample, 0)
    distribution[tags_per_sample] += max(0, exact_correct)
    return {
        "accuracy": test_results.get("accuracy"),
        "exact_correct": exact_correct,
        "total": total_samples,
        "no_answer": no_answer,
        "no_answer_rate": (no_answer / total_samples) if total_samples else None,
        "computed_tag_accuracy": (tag_correct / tag_total) if tag_total else None,
        "correct_tags": tag_correct,
        "total_tags": tag_total,
        "tag_correct_distribution": distribution,
        "exact_correct_indices": _exact_correct_indices(data),
        "sample_correct_tags_by_index": sample_correct_tags_by_index,
    }


def _exact_correct_indices(test_file: dict) -> list[int]:
    test_results = test_file.get("test_results", test_file)
    total = int(test_results.get("total", 0) or 0)
    errors = (test_file.get("error_log") or {}).get("errors") or []
    error_indices = {int(error["index"]) for error in errors if "index" in error}
    return sorted(set(range(total)) - error_indices)


def summarize_pre_post(path) -> dict | None:
    rows = load_json(path)
    if not rows:
        return None
    pre_exact = 0
    post_exact = 0
    pre_tags = 0
    post_tags = 0
    total_tags = 0
    for row in rows:
        target = row.get("target", "")
        pre = (row.get("pre_train_result") or {}).get("final_answer", "")
        post = (row.get("post_train_result") or {}).get("final_answer", "")
        pre_exact += bool((row.get("pre_train_result") or {}).get("is_correct"))
        post_exact += bool((row.get("post_train_result") or {}).get("is_correct"))
        pre_correct, pre_total = _score_tags(pre, target)
        post_correct, post_total = _score_tags(post, target)
        pre_tags += pre_correct
        post_tags += post_correct
        total_tags += max(pre_total, post_total)
    total_samples = len(rows)
    return {
        "total_samples": total_samples,
        "pre_exact": pre_exact,
        "post_exact": post_exact,
        "pre_correct_tags": pre_tags,
        "post_correct_tags": post_tags,
        "total_tags": total_tags,
        "pre_tag_accuracy": pre_tags / total_tags if total_tags else None,
        "post_tag_accuracy": post_tags / total_tags if total_tags else None,
    }


def summarize_train_results(path) -> dict | None:
    data = load_json(path)
    if not data:
        return None
    best = None
    checkpoints = []
    for row in data.get("results") or []:
        val = row.get("val_result") or {}
        train = row.get("train_result") or {}
        stats = row.get("playbook_stats") or {}
        checkpoint = {
            "epoch": row.get("epoch"),
            "step": row.get("step"),
            "val_accuracy": val.get("accuracy"),
            "val_exact_correct": val.get("correct"),
            "val_total": val.get("total"),
            "val_no_answer": val.get("no_answer"),
            "train_pre_accuracy": train.get("pre_train_accuracy"),
            "train_post_accuracy": train.get("post_train_accuracy"),
            "playbook_tokens": row.get("playbook_num_tokens"),
            "playbook_chars": row.get("playbook_length"),
            "playbook_bullets": stats.get("total_bullets"),
            "problematic_bullets": stats.get("problematic"),
            "unused_bullets": stats.get("unused"),
        }
        checkpoints.append(checkpoint)
        if checkpoint["val_accuracy"] is not None and (
            best is None or checkpoint["val_accuracy"] > best["val_accuracy"]
        ):
            best = checkpoint
    return {
        "best_accuracy": data.get("best_accuracy"),
        "best_checkpoint": best,
        "checkpoint_count": len(checkpoints),
        "checkpoints": checkpoints,
    }


def summarize_playbook(path) -> dict | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    bullet_matches = re.findall(r"\[([a-z]+)-\d+\]\s+helpful=(\d+)\s+harmful=(\d+)", text)
    return {
        "chars": len(text),
        "lines": text.count("\n") + 1,
        "bullets": len(bullet_matches),
        "helpful_sum": sum(int(item[1]) for item in bullet_matches),
        "harmful_sum": sum(int(item[2]) for item in bullet_matches),
        "harmful_bullets": sum(1 for item in bullet_matches if int(item[2]) > 0),
    }


def summarize_llm_logs(log_dir) -> dict:
    roles: dict[str, dict] = {}
    for path in sorted(log_dir.glob("*.json")) if log_dir.exists() else []:
        data = load_json(path)
        if not isinstance(data, dict):
            continue
        role = str(data.get("role") or "unknown")
        row = roles.setdefault(
            role,
            {
                "calls": 0,
                "prompt_tokens": 0,
                "response_tokens": 0,
                "reasoning_tokens": 0,
                "total_tokens": 0,
                "cached_input_tokens": None,
                "cached_output_tokens": None,
                "total_time": 0.0,
                "cost_usd": 0.0,
                "calls_with_cost": 0,
            },
        )
        row["calls"] += 1
        row["prompt_tokens"] += int(data.get("prompt_num_tokens") or 0)
        row["response_tokens"] += int(data.get("response_num_tokens") or 0)
        row["reasoning_tokens"] += int(data.get("reasoning_num_tokens") or 0)
        row["total_tokens"] += int(data.get("total_num_tokens") or 0)
        for field in ("cached_input_tokens", "cached_output_tokens"):
            value = data.get(field)
            if value is None:
                continue
            row[field] = int(value) + int(row[field] or 0)
        row["total_time"] += float(data.get("total_time") or data.get("call_time") or 0.0)
        if data.get("cost_usd") is not None:
            row["cost_usd"] += float(data.get("cost_usd") or 0.0)
            row["calls_with_cost"] += 1
    total = {
        "calls": sum(role["calls"] for role in roles.values()),
        "prompt_tokens": sum(role["prompt_tokens"] for role in roles.values()),
        "response_tokens": sum(role["response_tokens"] for role in roles.values()),
        "reasoning_tokens": sum(role["reasoning_tokens"] for role in roles.values()),
        "total_tokens": sum(role["total_tokens"] for role in roles.values()),
        "cached_input_tokens": (
            sum(int(role["cached_input_tokens"] or 0) for role in roles.values())
            if any(role["cached_input_tokens"] is not None for role in roles.values())
            else None
        ),
        "cached_output_tokens": (
            sum(int(role["cached_output_tokens"] or 0) for role in roles.values())
            if any(role["cached_output_tokens"] is not None for role in roles.values())
            else None
        ),
        "total_time": sum(role["total_time"] for role in roles.values()),
        "cost_usd": sum(role["cost_usd"] for role in roles.values()),
        "calls_with_cost": sum(role["calls_with_cost"] for role in roles.values()),
    }
    return {"roles": roles, "total": total}


def summarize_run(run) -> dict:
    run_config = load_json(run.path / "run_config.json") or {}
    run_state = load_json(run.path / "run_state.json") or {}
    config = run_config.get("config") or {}
    initial_raw = load_json(run.path / "initial_test_results.json")
    final_raw = load_json(run.path / "final_test_results.json")
    tags_per_sample = _infer_tags_per_sample(final_raw or initial_raw)
    initial = summarize_test_file(run.path / "initial_test_results.json", tags_per_sample) or {}
    final = summarize_test_file(run.path / "final_test_results.json", tags_per_sample) or {}
    training = summarize_train_results(run.path / "train_results.json") or {}
    training_pre_post = summarize_pre_post(run.path / "pre_train_post_train_results.json") or {}
    trace_files = sorted((run.path / "telemetry").glob("*.otel.jsonl"))
    metrics_files = sorted((run.path / "telemetry").glob("*.metrics.jsonl"))
    costs = summarize_costs(run.path, trace_files=trace_files)
    telemetry = summarize_telemetry(trace_files, metrics_files)
    best_playbook = summarize_playbook(run.path / "best_playbook.txt")
    final_playbook = summarize_playbook(run.path / "final_playbook.txt")
    initial_ok = set(initial.get("exact_correct_indices") or [])
    final_ok = set(final.get("exact_correct_indices") or [])
    initial_sample_tags = initial.get("sample_correct_tags_by_index") or {}
    final_sample_tags = final.get("sample_correct_tags_by_index") or {}
    llm_usage = summarize_llm_logs(run.path / "detailed_llm_logs")
    regressed_tags = 0
    improved_tags = 0
    regressed_samples = 0
    improved_samples = 0
    shared_indices = sorted(set(initial_sample_tags) | set(final_sample_tags))
    for index in shared_indices:
        initial_count = int(initial_sample_tags.get(index, 0) or 0)
        final_count = int(final_sample_tags.get(index, 0) or 0)
        if final_count < initial_count:
            regressed_tags += initial_count - final_count
            regressed_samples += 1
        elif final_count > initial_count:
            improved_tags += final_count - initial_count
            improved_samples += 1
    summary = {
        "initial_accuracy": initial.get("accuracy"),
        "final_accuracy": final.get("accuracy"),
        "best_validation_accuracy": training.get("best_accuracy")
        or (training.get("best_checkpoint") or {}).get("val_accuracy"),
        "initial_exact_correct": initial.get("exact_correct"),
        "final_exact_correct": final.get("exact_correct"),
        "initial_total": initial.get("total"),
        "final_total": final.get("total"),
        "initial_no_answer": initial.get("no_answer"),
        "final_no_answer": final.get("no_answer"),
        "initial_no_answer_rate": initial.get("no_answer_rate"),
        "final_no_answer_rate": final.get("no_answer_rate"),
        "initial_tag_accuracy": initial.get("computed_tag_accuracy"),
        "final_tag_accuracy": final.get("computed_tag_accuracy"),
        "tag_accuracy_delta": (
            final.get("computed_tag_accuracy") - initial.get("computed_tag_accuracy")
            if final.get("computed_tag_accuracy") is not None
            and initial.get("computed_tag_accuracy") is not None
            else None
        ),
        "exact_correct_delta": (
            final.get("exact_correct") - initial.get("exact_correct")
            if final.get("exact_correct") is not None and initial.get("exact_correct") is not None
            else None
        ),
        "correct_tags_delta": (
            final.get("correct_tags") - initial.get("correct_tags")
            if final.get("correct_tags") is not None and initial.get("correct_tags") is not None
            else None
        ),
        "status": run_state.get("status") or "completed",
        "checkpointing_enabled": run_state.get("checkpointing_enabled", False),
        "has_checkpoints": run_state.get("has_checkpoints", False),
        "resume_count": run_state.get("resume_count", 0),
        "active_runtime_seconds": run_state.get("active_runtime_seconds"),
        "current_stage": run_state.get("current_stage"),
        "last_completed_stage": run_state.get("last_completed_stage"),
    }
    return {
        "summary": summary,
        "costs": costs,
        "telemetry": telemetry,
        "tests": {
            "initial": initial,
            "final": final,
        },
        "training": training,
        "training_pre_post": training_pre_post,
        "models": {
            "generator": run_config.get("generator_model") or config.get("generator_model"),
            "reflector": run_config.get("reflector_model") or config.get("reflector_model"),
            "curator": run_config.get("curator_model") or config.get("curator_model"),
        },
        "models_display": " | ".join(
            f"{role}={model}"
            for role, model in [
                ("generator", run_config.get("generator_model") or config.get("generator_model")),
                ("reflector", run_config.get("reflector_model") or config.get("reflector_model")),
                ("curator", run_config.get("curator_model") or config.get("curator_model")),
            ]
            if model
        ),
        "playbooks": {
            "best": best_playbook,
            "final": final_playbook,
            "best_equals_final": best_playbook == final_playbook if best_playbook and final_playbook else None,
        },
        "config": {
            "mode": run.mode,
            "seed": run.seed,
            "eval_steps": config.get("eval_steps"),
            "num_epochs": config.get("num_epochs"),
            "json_mode": config.get("json_mode"),
            "api_provider": config.get("api_provider"),
            "config_name": config.get("config_name"),
        },
        "run_state": run_state,
        "llm_usage": llm_usage,
        "exact_changes": {
            "became_correct": sorted(final_ok - initial_ok),
            "became_wrong": sorted(initial_ok - final_ok),
        },
        "tag_changes": {
            "regressed_tags": regressed_tags,
            "improved_tags": improved_tags,
            "regressed_samples": regressed_samples,
            "improved_samples": improved_samples,
        },
        "artifacts": {
            "bullet_usage_log_lines": _count_lines(run.path / "bullet_usage_log.jsonl"),
            "curator_operations_lines": _count_lines(run.path / "curator_operations_diff.jsonl"),
            "curator_failures_lines": _count_lines(
                run.path / "detailed_llm_logs" / "curator_failures.txt"
            ),
            "trace_lines": sum(_count_lines(path) or 0 for path in trace_files),
            "metrics_lines": sum(_count_lines(path) or 0 for path in metrics_files),
        },
    }


def _count_lines(path) -> int | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)
