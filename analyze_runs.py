#!/usr/bin/env python3
"""Summarize ACE result directories.

Usage:
  ./analyze_runs.py <run_id_or_path> [<run_id_or_path> ...]

The script accepts either exact run directory paths or run IDs. For run IDs it
searches under ./results by default.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


def load_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        return {"_load_error": str(exc)}


def count_lines(path: Path) -> int | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f)


def split_tags(value: str) -> list[str]:
    return [part.strip().lower() for part in str(value).split(",")]


def score_tags(prediction: str, target: str) -> tuple[int, int]:
    predicted = split_tags(prediction)
    labels = split_tags(target)

    if len(predicted) > len(labels):
        predicted = predicted[: len(labels)]
    elif len(predicted) < len(labels):
        predicted += [""] * (len(labels) - len(predicted))

    return sum(p == y for p, y in zip(predicted, labels)), len(labels)


def infer_tags_per_sample(test_file: dict[str, Any] | None, default: int = 4) -> int:
    if not test_file:
        return default
    errors = (test_file.get("error_log") or {}).get("errors") or []
    for error in errors:
        target = error.get("ground_truth")
        if target:
            return len(split_tags(target))
    return default


def summarize_test_file(path: Path, tags_per_sample: int | None = None) -> dict[str, Any] | None:
    data = load_json(path)
    if not data:
        return None
    if isinstance(data, dict) and data.get("_load_error"):
        return data

    test_results = data.get("test_results", data)
    error_log = data.get("error_log") or {}
    errors = error_log.get("errors") or []

    total_samples = int(test_results.get("total", 0) or 0)
    exact_correct = int(test_results.get("correct", 0) or 0)
    tags_per_sample = tags_per_sample or infer_tags_per_sample(data)

    dist = {i: 0 for i in range(tags_per_sample + 1)}
    error_tag_correct = 0
    error_tag_total = 0
    for error in errors:
        correct, total = score_tags(
            error.get("prediction", ""), error.get("ground_truth", "")
        )
        error_tag_correct += correct
        error_tag_total += total
        dist.setdefault(correct, 0)
        dist[correct] += 1

    dist.setdefault(tags_per_sample, 0)
    dist[tags_per_sample] += max(0, exact_correct)

    tag_total = total_samples * tags_per_sample if total_samples else error_tag_total
    tag_correct = exact_correct * tags_per_sample + error_tag_correct
    computed_accuracy = tag_correct / tag_total if tag_total else None

    return {
        "path": str(path),
        "reported_accuracy": test_results.get("accuracy"),
        "computed_tag_accuracy": computed_accuracy,
        "correct_tags": tag_correct,
        "total_tags": tag_total,
        "exact_correct": exact_correct,
        "total_samples": total_samples,
        "no_answer": int(test_results.get("no_answer", 0) or 0),
        "error_count": len(errors),
        "tags_per_sample": tags_per_sample,
        "tag_correct_distribution": dist,
        "exact_correct_indices": exact_correct_indices(data),
    }


def exact_correct_indices(test_file: dict[str, Any]) -> list[int]:
    test_results = test_file.get("test_results", test_file)
    total = int(test_results.get("total", 0) or 0)
    errors = (test_file.get("error_log") or {}).get("errors") or []
    error_indices = {int(e["index"]) for e in errors if "index" in e}
    return sorted(set(range(total)) - error_indices)


def summarize_pre_post(path: Path) -> dict[str, Any] | None:
    rows = load_json(path)
    if not rows:
        return None
    if isinstance(rows, dict) and rows.get("_load_error"):
        return rows

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

        pre_correct, pre_total = score_tags(pre, target)
        post_correct, post_total = score_tags(post, target)
        pre_tags += pre_correct
        post_tags += post_correct
        total_tags += max(pre_total, post_total)

    total_samples = len(rows)
    return {
        "total_samples": total_samples,
        "pre_exact": pre_exact,
        "post_exact": post_exact,
        "pre_exact_accuracy": pre_exact / total_samples if total_samples else None,
        "post_exact_accuracy": post_exact / total_samples if total_samples else None,
        "pre_correct_tags": pre_tags,
        "post_correct_tags": post_tags,
        "total_tags": total_tags,
        "pre_tag_accuracy": pre_tags / total_tags if total_tags else None,
        "post_tag_accuracy": post_tags / total_tags if total_tags else None,
    }


def summarize_train_results(path: Path) -> dict[str, Any] | None:
    data = load_json(path)
    if not data:
        return None
    if isinstance(data, dict) and data.get("_load_error"):
        return data

    checkpoints = []
    best = None
    for row in data.get("results") or []:
        val = row.get("val_result") or {}
        train = row.get("train_result") or {}
        stats = row.get("playbook_stats") or {}
        checkpoint = {
            "epoch": row.get("epoch"),
            "step": row.get("step"),
            "train_pre_accuracy": train.get("pre_train_accuracy"),
            "train_post_accuracy": train.get("post_train_accuracy"),
            "val_accuracy": val.get("accuracy"),
            "val_exact_correct": val.get("correct"),
            "val_total": val.get("total"),
            "val_no_answer": val.get("no_answer"),
            "playbook_tokens": row.get("playbook_num_tokens"),
            "playbook_chars": row.get("playbook_length"),
            "playbook_bullets": stats.get("total_bullets"),
            "problematic_bullets": stats.get("problematic"),
            "unused_bullets": stats.get("unused"),
        }
        checkpoints.append(checkpoint)
        if checkpoint["val_accuracy"] is not None:
            if best is None or checkpoint["val_accuracy"] > best["val_accuracy"]:
                best = checkpoint

    return {
        "best_accuracy": data.get("best_accuracy"),
        "checkpoint_count": len(checkpoints),
        "best_checkpoint": best,
        "checkpoints": checkpoints,
    }


def summarize_val_results(path: Path) -> dict[str, Any] | None:
    rows = load_json(path)
    if not rows:
        return None
    if isinstance(rows, dict) and rows.get("_load_error"):
        return rows
    return {
        "checkpoint_count": len(rows),
        "checkpoints": [
            {
                "epoch": row.get("epoch"),
                "step": row.get("step"),
                "accuracy": (row.get("val_results") or {}).get("accuracy"),
                "exact_correct": (row.get("val_results") or {}).get("correct"),
                "total": (row.get("val_results") or {}).get("total"),
                "no_answer": (row.get("val_results") or {}).get("no_answer"),
                "errors": len(((row.get("error_log") or {}).get("errors") or [])),
            }
            for row in rows
        ],
    }


def summarize_playbook(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    bullet_matches = re.findall(r"\[([a-z]+)-\d+\]\s+helpful=(\d+)\s+harmful=(\d+)", text)
    by_prefix: dict[str, int] = {}
    for prefix, _, _ in bullet_matches:
        by_prefix[prefix] = by_prefix.get(prefix, 0) + 1
    return {
        "chars": len(text),
        "lines": text.count("\n") + 1,
        "bullets": len(bullet_matches),
        "helpful_sum": sum(int(item[1]) for item in bullet_matches),
        "harmful_sum": sum(int(item[2]) for item in bullet_matches),
        "harmful_bullets": sum(1 for item in bullet_matches if int(item[2]) > 0),
        "by_prefix": by_prefix,
    }


def find_run(identifier: str, results_root: Path) -> Path:
    candidate = Path(identifier)
    if candidate.exists() and candidate.is_dir():
        return candidate.resolve()

    matches = [p for p in results_root.rglob(identifier) if p.is_dir() and p.name == identifier]
    if not matches:
        raise FileNotFoundError(f"Could not find run ID or path: {identifier}")
    if len(matches) > 1:
        formatted = "\n  ".join(str(p) for p in matches)
        raise RuntimeError(f"Multiple matches for {identifier}:\n  {formatted}")
    return matches[0].resolve()


def analyze_run(run_dir: Path) -> dict[str, Any]:
    run_config = load_json(run_dir / "run_config.json") or {}
    config = run_config.get("config") or {}

    initial_file = load_json(run_dir / "initial_test_results.json")
    final_file = load_json(run_dir / "final_test_results.json")
    tags_per_sample = infer_tags_per_sample(final_file or initial_file)

    initial = summarize_test_file(run_dir / "initial_test_results.json", tags_per_sample)
    final = summarize_test_file(run_dir / "final_test_results.json", tags_per_sample)

    exact_changes = None
    if initial and final:
        initial_ok = set(initial.get("exact_correct_indices") or [])
        final_ok = set(final.get("exact_correct_indices") or [])
        exact_changes = {
            "became_correct": sorted(final_ok - initial_ok),
            "became_wrong": sorted(initial_ok - final_ok),
            "stayed_correct": sorted(initial_ok & final_ok),
        }

    best_playbook_path = run_dir / "best_playbook.txt"
    final_playbook_path = run_dir / "final_playbook.txt"
    best_playbook_text = (
        best_playbook_path.read_text(encoding="utf-8", errors="replace")
        if best_playbook_path.exists()
        else None
    )
    final_playbook_text = (
        final_playbook_path.read_text(encoding="utf-8", errors="replace")
        if final_playbook_path.exists()
        else None
    )

    telemetry_dir = run_dir / "telemetry"
    trace_files = sorted(telemetry_dir.glob("*.otel.jsonl")) if telemetry_dir.exists() else []
    metrics_files = sorted(telemetry_dir.glob("*.metrics.jsonl")) if telemetry_dir.exists() else []

    return {
        "run_id": run_dir.name,
        "path": str(run_dir),
        "task_name": run_config.get("task_name"),
        "mode": run_config.get("mode"),
        "models": {
            "generator": run_config.get("generator_model"),
            "reflector": run_config.get("reflector_model"),
            "curator": run_config.get("curator_model"),
        },
        "config": {
            "eval_steps": config.get("eval_steps"),
            "num_epochs": config.get("num_epochs"),
            "train_workers": None,
            "test_workers": config.get("test_workers"),
            "json_mode": config.get("json_mode"),
            "api_provider": config.get("api_provider"),
            "seed": config.get("seed"),
            "config_name": config.get("config_name"),
        },
        "initial_test": initial,
        "final_test": final,
        "exact_changes": exact_changes,
        "training_pre_post": summarize_pre_post(run_dir / "pre_train_post_train_results.json"),
        "train_results": summarize_train_results(run_dir / "train_results.json"),
        "val_results": summarize_val_results(run_dir / "val_results.json"),
        "playbooks": {
            "best": summarize_playbook(best_playbook_path),
            "final": summarize_playbook(final_playbook_path),
            "best_equals_final": (
                best_playbook_text == final_playbook_text
                if best_playbook_text is not None and final_playbook_text is not None
                else None
            ),
        },
        "artifacts": {
            "bullet_usage_log_lines": count_lines(run_dir / "bullet_usage_log.jsonl"),
            "curator_operations_lines": count_lines(run_dir / "curator_operations_diff.jsonl"),
            "curator_failures_lines": count_lines(run_dir / "detailed_llm_logs" / "curator_failures.txt"),
            "trace_lines": sum(count_lines(p) or 0 for p in trace_files),
            "metrics_lines": sum(count_lines(p) or 0 for p in metrics_files),
        },
    }


def pct(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value) * 100:.2f}%"
    except Exception:
        return str(value)


def pct_delta(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value) * 100:+.2f}pp"
    except Exception:
        return str(value)


def count_fmt(numer: Any, denom: Any) -> str:
    if numer is None or denom is None:
        return "n/a"
    return f"{numer}/{denom}"


def build_notes(report: dict[str, Any]) -> list[str]:
    notes = []
    train_results = report.get("train_results") or {}
    playbooks = report.get("playbooks") or {}
    best_playbook = playbooks.get("best") or {}
    final_playbook = playbooks.get("final") or {}
    initial = report.get("initial_test") or {}
    final = report.get("final_test") or {}

    if train_results and train_results.get("checkpoint_count") == 0:
        notes.append(
            "No validation checkpoints ran; best_playbook likely stayed at the initial playbook."
        )
    if best_playbook and best_playbook.get("bullets") == 0:
        notes.append("Best playbook has zero learned bullets.")
    if (
        best_playbook
        and final_playbook
        and best_playbook.get("bullets") != final_playbook.get("bullets")
    ):
        notes.append(
            "Best and final playbooks differ; final test usually uses the best validated playbook."
        )
    if initial and final:
        exact_delta = (final.get("exact_correct") or 0) - (initial.get("exact_correct") or 0)
        tag_delta = (final.get("correct_tags") or 0) - (initial.get("correct_tags") or 0)
        if tag_delta > 0 and exact_delta <= 0:
            notes.append(
                "Tag-level accuracy improved, but exact-sample accuracy did not improve."
            )
    return notes


def print_run_report(report: dict[str, Any], verbose: bool = False) -> None:
    print(f"# {report['run_id']}")
    print(f"Path: {report['path']}")
    print(
        "Task: {task} | Mode: {mode} | Provider: {provider} | Eval steps: {eval_steps}".format(
            task=report.get("task_name"),
            mode=report.get("mode"),
            provider=(report.get("config") or {}).get("api_provider"),
            eval_steps=(report.get("config") or {}).get("eval_steps"),
        )
    )
    models = report.get("models") or {}
    print(
        f"Models: generator={models.get('generator')} reflector={models.get('reflector')} curator={models.get('curator')}"
    )

    initial = report.get("initial_test") or {}
    final = report.get("final_test") or {}
    if initial or final:
        print("\nTest summary:")
        print("  split    tag_acc   correct_tags   exact_samples   no_answer")
        for name, data in [("initial", initial), ("final", final)]:
            if not data:
                continue
            print(
                "  {name:<7} {tag_acc:<9} {tags:<14} {exact:<15} {no_answer}".format(
                    name=name,
                    tag_acc=pct(data.get("computed_tag_accuracy")),
                    tags=count_fmt(data.get("correct_tags"), data.get("total_tags")),
                    exact=count_fmt(data.get("exact_correct"), data.get("total_samples")),
                    no_answer=data.get("no_answer"),
                )
            )

        if initial and final:
            tag_delta = (
                final.get("computed_tag_accuracy") - initial.get("computed_tag_accuracy")
                if final.get("computed_tag_accuracy") is not None
                and initial.get("computed_tag_accuracy") is not None
                else None
            )
            correct_tag_delta = (
                final.get("correct_tags") - initial.get("correct_tags")
                if final.get("correct_tags") is not None and initial.get("correct_tags") is not None
                else None
            )
            exact_delta = (
                final.get("exact_correct") - initial.get("exact_correct")
                if final.get("exact_correct") is not None and initial.get("exact_correct") is not None
                else None
            )
            print(
                f"  delta   tag_acc={pct_delta(tag_delta)} correct_tags={correct_tag_delta:+} exact_samples={exact_delta:+}"
            )

            print("\nTag-correct distribution per sample:")
            print(f"  initial: {initial.get('tag_correct_distribution')}")
            print(f"  final:   {final.get('tag_correct_distribution')}")

    train = report.get("training_pre_post")
    if train:
        print("\nTraining pre/post:")
        print(
            "  tag_acc: {pre} -> {post} ({pre_count} -> {post_count})".format(
                pre=pct(train.get("pre_tag_accuracy")),
                post=pct(train.get("post_tag_accuracy")),
                pre_count=count_fmt(train.get("pre_correct_tags"), train.get("total_tags")),
                post_count=count_fmt(train.get("post_correct_tags"), train.get("total_tags")),
            )
        )
        print(
            "  exact:   {pre} -> {post}".format(
                pre=count_fmt(train.get("pre_exact"), train.get("total_samples")),
                post=count_fmt(train.get("post_exact"), train.get("total_samples")),
            )
        )

    train_results = report.get("train_results")
    if train_results:
        print("\nValidation checkpoints:")
        print(f"  best_accuracy: {pct(train_results.get('best_accuracy'))}")
        print("  step   val_acc   exact    train_pre -> train_post   bullets   tokens")
        for checkpoint in train_results.get("checkpoints") or []:
            print(
                "  {step:<6} {val:<9} {exact:<8} {pre} -> {post:<9} {bullets:<8} {tokens}".format(
                    step=checkpoint.get("step"),
                    val=pct(checkpoint.get("val_accuracy")),
                    exact=count_fmt(
                        checkpoint.get("val_exact_correct"), checkpoint.get("val_total")
                    ),
                    pre=pct(checkpoint.get("train_pre_accuracy")),
                    post=pct(checkpoint.get("train_post_accuracy")),
                    bullets=checkpoint.get("playbook_bullets"),
                    tokens=checkpoint.get("playbook_tokens"),
                )
            )
        best_checkpoint = train_results.get("best_checkpoint")
        if best_checkpoint:
            print(
                f"  selected best checkpoint: step {best_checkpoint.get('step')} at {pct(best_checkpoint.get('val_accuracy'))}"
            )

    playbooks = report.get("playbooks") or {}
    if playbooks:
        print("\nPlaybooks:")
        for name in ["best", "final"]:
            data = playbooks.get(name)
            if not data:
                continue
            print(
                "  {name:<5} bullets={bullets:<4} chars={chars:<6} helpful_sum={helpful:<4} harmful_sum={harmful:<4} harmful_bullets={harmful_bullets}".format(
                    name=name,
                    bullets=data.get("bullets"),
                    chars=data.get("chars"),
                    helpful=data.get("helpful_sum"),
                    harmful=data.get("harmful_sum"),
                    harmful_bullets=data.get("harmful_bullets"),
                )
            )
        print(f"  best_equals_final: {playbooks.get('best_equals_final')}")

    exact_changes = report.get("exact_changes")
    if exact_changes:
        print("\nExact-match movement:")
        print(f"  became_correct: {exact_changes.get('became_correct')}")
        print(f"  became_wrong:   {exact_changes.get('became_wrong')}")

    artifacts = report.get("artifacts") or {}
    print("\nArtifacts:")
    print(
        "  bullet_usage={bullet_usage_log_lines} curator_ops={curator_operations_lines} curator_failures={curator_failures_lines} trace_lines={trace_lines} metrics_lines={metrics_lines}".format(
            **artifacts
        )
    )

    notes = build_notes(report)
    if notes:
        print("\nNotes:")
        for note in notes:
            print(f"  - {note}")

    if verbose and report.get("val_results"):
        print("\nVal result file:")
        print(json.dumps(report["val_results"], indent=2, sort_keys=True))

    print()


def print_comparison(reports: list[dict[str, Any]]) -> None:
    if len(reports) < 2:
        return
    print("# Comparison")
    print("run_id")
    print("  initial_tag  final_tag   delta_tag_acc  delta_tags  exact_i  exact_f  best_val")
    for report in reports:
        initial = report.get("initial_test") or {}
        final = report.get("final_test") or {}
        train_results = report.get("train_results") or {}
        correct_delta = None
        tag_acc_delta = None
        if initial.get("correct_tags") is not None and final.get("correct_tags") is not None:
            correct_delta = final.get("correct_tags") - initial.get("correct_tags")
        if (
            initial.get("computed_tag_accuracy") is not None
            and final.get("computed_tag_accuracy") is not None
        ):
            tag_acc_delta = (
                final.get("computed_tag_accuracy") - initial.get("computed_tag_accuracy")
            )
        print(report["run_id"])
        print(
            "  {init:<12} {final:<11} {delta_acc:<14} {delta:<11} {exact_i:<8} {exact_f:<8} {best}".format(
                init=pct(initial.get("computed_tag_accuracy")),
                final=pct(final.get("computed_tag_accuracy")),
                delta_acc=pct_delta(tag_acc_delta),
                delta=(f"{correct_delta:+}" if correct_delta is not None else "n/a"),
                exact_i=count_fmt(initial.get("exact_correct"), initial.get("total_samples")),
                exact_f=count_fmt(final.get("exact_correct"), final.get("total_samples")),
                best=pct(train_results.get("best_accuracy")),
            )
        )
    print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze ACE result runs.")
    parser.add_argument("runs", nargs="+", help="Run IDs or run directory paths")
    parser.add_argument(
        "--results-root",
        default=str(ROOT / "results"),
        help="Directory to search when a run ID is provided",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    parser.add_argument("--verbose", action="store_true", help="Include extra raw summaries")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results_root = Path(args.results_root).resolve()
    reports = []

    for identifier in args.runs:
        run_dir = find_run(identifier, results_root)
        reports.append(analyze_run(run_dir))

    if args.json:
        print(json.dumps(reports, indent=2, sort_keys=True))
    else:
        for report in reports:
            print_run_report(report, verbose=args.verbose)
        print_comparison(reports)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
