#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
ACE_ROOT = REPO_ROOT / "projects" / "ace"

if str(ACE_ROOT) not in sys.path:
    sys.path.insert(0, str(ACE_ROOT))

from lifecycle import (  # noqa: E402
    STATUS_CHECKPOINTED,
    STATUS_COMPLETED,
    STATUS_FAILED,
    checkpoints_dir,
    finish_session,
    load_json,
    load_run_state,
    new_run_state,
    now_utc_iso,
    persist_run_state,
    start_session,
    write_json_atomic,
)
from result_layout import build_run_leaf  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run staged resumable AppWorld full workflow.")
    parser.add_argument("--appworld-root", type=Path, required=True)
    parser.add_argument("--save-path", type=Path, required=True)
    parser.add_argument("--config-name", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--generator-provider", required=True)
    parser.add_argument("--generator-model", required=True)
    parser.add_argument("--reflector-provider", required=True)
    parser.add_argument("--reflector-model", required=True)
    parser.add_argument("--curator-provider", required=True)
    parser.add_argument("--curator-model", required=True)
    parser.add_argument("--max-steps", type=int, default=30)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--telemetry", type=int, default=1)
    parser.add_argument("--telemetry-interval", type=float, default=None)
    parser.add_argument("--initial-playbook-path", required=True)
    parser.add_argument("--resume-from", type=Path, default=None)
    parser.add_argument("--checkpoint-enabled", action="store_true")
    parser.add_argument("--stop-after-stage", choices=["adapt", "eval-normal", "eval-challenge"], default=None)
    parser.add_argument("--stop-after-task", type=int, default=None)
    parser.add_argument("--checkpoint-every-task", type=int, default=1)
    parser.add_argument("--test-workers", type=int, default=1)
    return parser.parse_args()


def model_config(provider: str, model: str, max_tokens: int) -> dict[str, Any]:
    config: dict[str, Any] = {
        "name": model,
        "provider": provider,
        "temperature": 0,
        "seed": 100,
        "stop": ["<|endoftext|>", "<|eot_id|>", "<|start_header_id|>"],
        "logprobs": False,
        "top_logprobs": None,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "n": 1,
        "response_format": {"type": "text"},
        "retry_after_n_seconds": 10,
        "use_cache": True,
        "max_retries": 50,
        "max_tokens": int(max_tokens),
    }
    if provider.lower() == "openrouter":
        pricing_by_model = {
            "openai/gpt-oss-120b:nitro": {
                "input_cost_per_token": 0.039 / 1_000_000,
                "output_cost_per_token": 0.19 / 1_000_000,
                "litellm_provider": "openai",
                "mode": "chat",
                "max_input_tokens": 131072,
                "max_output_tokens": 32768,
            },
            "openai/gpt-oss-20b:nitro": {
                "input_cost_per_token": 0.03 / 1_000_000,
                "output_cost_per_token": 0.14 / 1_000_000,
                "litellm_provider": "openai",
                "mode": "chat",
                "max_input_tokens": 131072,
                "max_output_tokens": 32768,
            },
            "minimax/minimax-m2.7": {
                "input_cost_per_token": 0.30 / 1_000_000,
                "output_cost_per_token": 1.20 / 1_000_000,
                "litellm_provider": "openai",
                "mode": "chat",
                "max_input_tokens": 196608,
            },
        }
        token_cost_data = pricing_by_model.get(model.lower())
        if token_cost_data:
            config["token_cost_data"] = token_cost_data
    return config


def stage_specs(args: argparse.Namespace, run_dir: Path) -> list[dict[str, Any]]:
    adapted_playbook = run_dir / "stages" / "adapt" / "adapted_playbook.txt"
    return [
        {
            "name": "adapt",
            "dataset": "train",
            "agent_class": "adaptation",
            "agent_type": "ace_adaptation_react",
            "initial_playbook_file_path": str(args.initial_playbook_path),
            "trained_playbook_file_path": str(adapted_playbook),
        },
        {
            "name": "eval-normal",
            "dataset": "test_normal",
            "agent_class": "evaluation",
            "agent_type": "ace_evaluation_react",
            "trained_playbook_file_path": str(adapted_playbook),
        },
        {
            "name": "eval-challenge",
            "dataset": "test_challenge",
            "agent_class": "evaluation",
            "agent_type": "ace_evaluation_react",
            "trained_playbook_file_path": str(adapted_playbook),
        },
    ]


def build_run_dir(args: argparse.Namespace) -> tuple[Path, str]:
    if args.resume_from:
        run_dir = args.resume_from.resolve()
        return run_dir, run_dir.name
    run_id = build_run_leaf("full", args.seed, time.strftime("%Y%m%d_%H%M%S"))
    return (args.save_path / run_id).resolve(), run_id


def stage_dir(run_dir: Path, stage_name: str) -> Path:
    return run_dir / "stages" / stage_name


def manifest_path(run_dir: Path, stage_name: str) -> Path:
    return stage_dir(run_dir, stage_name) / "task_manifest.json"


def load_manifest(run_dir: Path, stage_name: str) -> dict[str, Any]:
    return load_json(manifest_path(run_dir, stage_name)) or {
        "stage": stage_name,
        "tasks": {},
        "updated_at": None,
    }


def persist_manifest(run_dir: Path, stage_name: str, manifest: dict[str, Any]) -> None:
    manifest["updated_at"] = now_utc_iso()
    write_json_atomic(manifest_path(run_dir, stage_name), manifest)


def stage_experiment_name(stage_name: str) -> str:
    return f"stages/{stage_name}"


def export_top_level_summary(appworld_root: Path, run_dir: Path) -> None:
    command = [
        sys.executable,
        str(REPO_ROOT / "runners" / "ace" / "export_appworld_summary.py"),
        "--run-dir",
        str(run_dir),
        "--appworld-root",
        str(appworld_root),
        "--no-evaluate",
    ]
    subprocess.run(command, check=True, cwd=str(REPO_ROOT))


def copy_stage_evaluation(run_dir: Path, stage_name: str, dataset: str) -> None:
    source = stage_dir(run_dir, stage_name) / "evaluations" / f"{dataset}.json"
    source_txt = stage_dir(run_dir, stage_name) / "evaluations" / f"{dataset}.txt"
    target_dir = run_dir / "evaluations"
    target_dir.mkdir(parents=True, exist_ok=True)
    if source.exists():
        shutil.copy2(source, target_dir / source.name)
    if source_txt.exists():
        shutil.copy2(source_txt, target_dir / source_txt.name)


def stage_completed(manifest: dict[str, Any], task_ids: list[str]) -> bool:
    return all((manifest.get("tasks") or {}).get(task_id, {}).get("status") == "completed" for task_id in task_ids)


def configure_appworld_env(args: argparse.Namespace, run_dir: Path) -> None:
    os.environ["APPWORLD_PROJECT_PATH"] = str(args.appworld_root)
    os.environ["APPWORLD_EXPERIMENT_OUTPUTS"] = str(run_dir)
    os.environ["APPWORLD_MAESTRO_TELEMETRY"] = str(args.telemetry)
    if args.telemetry_interval is not None:
        os.environ["APPWORLD_MAESTRO_METRICS_INTERVAL_SECONDS"] = str(args.telemetry_interval)


def write_run_config(args: argparse.Namespace, run_dir: Path, run_id: str) -> None:
    payload = {
        "run_id": run_id,
        "mode": "full",
        "task_name": "appworld",
        "config_name": args.config_name,
        "seed": args.seed,
        "checkpoint_enabled": args.checkpoint_enabled,
        "resume_from": str(args.resume_from) if args.resume_from else None,
        "stop_after_stage": args.stop_after_stage,
        "stop_after_task": args.stop_after_task,
        "checkpoint_every_task": args.checkpoint_every_task,
        "appworld_root": str(args.appworld_root),
        "save_path": str(run_dir),
        "models": {
            "generator": {"provider": args.generator_provider, "model": args.generator_model},
            "reflector": {"provider": args.reflector_provider, "model": args.reflector_model},
            "curator": {"provider": args.curator_provider, "model": args.curator_model},
        },
    }
    write_json_atomic(run_dir / "run_config.json", payload)


def update_run_state(run_dir: Path, run_state: dict[str, Any], **updates: Any) -> dict[str, Any]:
    run_state.update(updates)
    persist_run_state(run_dir, run_state)
    return run_state


def build_agent(stage: dict[str, Any], args: argparse.Namespace):
    import appworld_experiments.code.ace.adaptation_react  # noqa: F401
    import appworld_experiments.code.ace.evaluation_react  # noqa: F401
    from appworld_experiments.code.ace.adaptation_agent import StarAgent
    from appworld_experiments.code.ace.evaluation_agent import Agent

    prompts_dir = args.appworld_root / "experiments" / "prompts"
    agent_payload: dict[str, Any] = {
        "type": stage["agent_type"],
        "appworld_config": {"random_seed": int(args.seed)},
        "max_steps": int(args.max_steps),
        "max_cost_overall": 1000,
        "max_cost_per_task": 10,
        "log_lm_calls": True,
        "ignore_multiple_calls": True,
        "logger_config": {"color": True, "verbose": True},
    }
    if stage["agent_class"] == "adaptation":
        agent_payload.update(
            {
                "generator_model_config": model_config(args.generator_provider, args.generator_model, args.max_tokens),
                "reflector_model_config": model_config(args.reflector_provider, args.reflector_model, args.max_tokens),
                "curator_model_config": model_config(args.curator_provider, args.curator_model, args.max_tokens),
                "generator_prompt_file_path": str(prompts_dir / "appworld_react_generator_prompt.txt"),
                "reflector_prompt_file_path": str(prompts_dir / "appworld_react_reflector_no_gt_prompt.txt"),
                "curator_prompt_file_path": str(prompts_dir / "appworld_react_curator_prompt.txt"),
                "initial_playbook_file_path": stage["initial_playbook_file_path"],
                "trained_playbook_file_path": stage["trained_playbook_file_path"],
                "use_gt_code": False,
            }
        )
        return StarAgent.from_dict(agent_payload)
    agent_payload.update(
        {
            "generator_model_config": model_config(args.generator_provider, args.generator_model, args.max_tokens),
            "generator_prompt_file_path": str(prompts_dir / "appworld_react_generator_prompt.txt"),
            "trained_playbook_file_path": stage["trained_playbook_file_path"],
        }
    )
    return Agent.from_dict(agent_payload)


def task_output_summary(stage_dir_path: Path, task_id: str) -> dict[str, Any]:
    task_dir = stage_dir_path / "tasks" / task_id
    cost_file = task_dir / "misc" / "cost.txt"
    cost = None
    if cost_file.exists():
        try:
            cost = float(cost_file.read_text(encoding="utf-8").strip())
        except ValueError:
            cost = None
    return {
        "task_dir": str(task_dir),
        "evaluation_report": str(task_dir / "evaluation" / "report.md"),
        "cost_usd": cost,
    }


def remaining_task_ids(manifest: dict[str, Any], task_ids: list[str]) -> list[str]:
    remaining = []
    for task_id in task_ids:
        if (manifest.get("tasks") or {}).get(task_id, {}).get("status") == "completed":
            continue
        remaining.append(task_id)
    return remaining


def run_stage(
    args: argparse.Namespace,
    run_dir: Path,
    run_state: dict[str, Any],
    stage: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    from appworld.task import load_task_ids
    from appworld.evaluator import evaluate_dataset

    stage_name = stage["name"]
    dataset = stage["dataset"]
    stage_root = stage_dir(run_dir, stage_name)
    stage_root.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(run_dir, stage_name)
    task_ids = load_task_ids(dataset)
    manifest["task_ids"] = task_ids
    manifest["dataset"] = dataset
    persist_manifest(run_dir, stage_name, manifest)
    if stage_completed(manifest, task_ids):
        return False, manifest

    agent = build_agent(stage, args)
    pending_task_ids = remaining_task_ids(manifest, task_ids)
    agent.logger.initialize(experiment_name=stage_experiment_name(stage_name), num_tasks=len(task_ids), num_processes=1, process_index=0)

    completed_count = sum(1 for row in (manifest.get("tasks") or {}).values() if row.get("status") == "completed")
    for task_index, task_id in enumerate(pending_task_ids, start=completed_count):
        started_at = now_utc_iso()
        started_perf = time.perf_counter()
        task_row = dict((manifest.get("tasks") or {}).get(task_id) or {})
        task_row.update(
            {
                "task_id": task_id,
                "stage": stage_name,
                "status": "in_progress",
                "attempt": int(task_row.get("attempt") or 0) + 1,
                "started_at": started_at,
            }
        )
        manifest.setdefault("tasks", {})[task_id] = task_row
        persist_manifest(run_dir, stage_name, manifest)
        update_run_state(run_dir, run_state, has_checkpoints=True, current_stage=stage_name, last_checkpoint_at=started_at)

        try:
            if hasattr(agent, "current_task_index"):
                agent.current_task_index = task_index
            agent.solve_task(task_id, stage_experiment_name(stage_name))
            ended_at = now_utc_iso()
            elapsed = max(0.0, time.perf_counter() - started_perf)
            task_row.update(
                {
                    "status": "completed",
                    "ended_at": ended_at,
                    "active_runtime_seconds": float(task_row.get("active_runtime_seconds") or 0.0) + elapsed,
                    "task_completed": True,
                    **task_output_summary(stage_root, task_id),
                }
            )
            manifest["tasks"][task_id] = task_row
            persist_manifest(run_dir, stage_name, manifest)
            completed_count += 1
            if args.stop_after_task is not None and completed_count >= int(args.stop_after_task):
                return True, manifest
        except Exception as exc:
            ended_at = now_utc_iso()
            elapsed = max(0.0, time.perf_counter() - started_perf)
            task_row.update(
                {
                    "status": "failed",
                    "ended_at": ended_at,
                    "active_runtime_seconds": float(task_row.get("active_runtime_seconds") or 0.0) + elapsed,
                    "task_completed": False,
                    "failure_reason": str(exc),
                }
            )
            manifest["tasks"][task_id] = task_row
            persist_manifest(run_dir, stage_name, manifest)
            raise

    if stage["agent_class"] == "evaluation":
        evaluate_dataset(stage_experiment_name(stage_name), dataset, print_report=False)
        copy_stage_evaluation(run_dir, stage_name, dataset)
    return False, manifest


def main() -> int:
    args = parse_args()
    if args.test_workers != 1:
        raise SystemExit("appworld_full_eval resumable mode only supports --test-workers 1 in v1.")

    run_dir, run_id = build_run_dir(args)
    run_dir.mkdir(parents=True, exist_ok=True)
    configure_appworld_env(args, run_dir)

    sys.path.insert(0, str(args.appworld_root / "src"))
    sys.path.insert(0, str(args.appworld_root / "experiments"))

    run_state = load_run_state(run_dir)
    if not run_state:
        run_state = new_run_state(
            run_id=run_id,
            checkpointing_enabled=bool(args.checkpoint_enabled),
            resume_enabled=True,
            current_stage="adapt",
        )
        persist_run_state(run_dir, run_state)
    write_run_config(args, run_dir, run_id)

    stage_list = stage_specs(args, run_dir)
    current_stage = run_state.get("current_stage") or "adapt"
    session = start_session(
        run_dir,
        run_state,
        stage_entered=current_stage,
        resume_from_checkpoint=bool(args.resume_from or run_state.get("has_checkpoints")),
    )

    try:
        for stage in stage_list:
            stage_name = stage["name"]
            if run_state.get("last_completed_stage") == "eval-challenge":
                break
            if stage_name in {"baseline-eval"}:
                continue
            if run_state.get("last_completed_stage") == "adapt" and stage_name == "adapt":
                continue
            if run_state.get("last_completed_stage") == "eval-normal" and stage_name in {"adapt", "eval-normal"}:
                continue

            update_run_state(run_dir, run_state, current_stage=stage_name, status="in_progress")
            stopped_early, manifest = run_stage(args, run_dir, run_state, stage)
            export_top_level_summary(args.appworld_root, run_dir)
            if stage_completed(manifest, manifest.get("task_ids") or []):
                update_run_state(run_dir, run_state, last_completed_stage=stage_name)
                export_top_level_summary(args.appworld_root, run_dir)
                if args.stop_after_stage == stage_name:
                    update_run_state(run_dir, run_state, status=STATUS_CHECKPOINTED)
                    run_state, _ = finish_session(run_dir, run_state, session, stage_exited=stage_name, status=STATUS_CHECKPOINTED)
                    export_top_level_summary(args.appworld_root, run_dir)
                    return 0
            if stopped_early:
                update_run_state(run_dir, run_state, status=STATUS_CHECKPOINTED, has_checkpoints=True)
                run_state, _ = finish_session(run_dir, run_state, session, stage_exited=stage_name, status=STATUS_CHECKPOINTED)
                export_top_level_summary(args.appworld_root, run_dir)
                return 0

        update_run_state(run_dir, run_state, status=STATUS_COMPLETED, current_stage="eval-challenge")
        run_state, _ = finish_session(
            run_dir,
            run_state,
            session,
            stage_exited=run_state.get("last_completed_stage"),
            status=STATUS_COMPLETED,
        )
        export_top_level_summary(args.appworld_root, run_dir)
        return 0
    except Exception as exc:
        update_run_state(run_dir, run_state, status=STATUS_FAILED, failure_reason=str(exc))
        finish_session(run_dir, run_state, session, stage_exited=run_state.get("current_stage"), status=STATUS_FAILED)
        export_top_level_summary(args.appworld_root, run_dir)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
