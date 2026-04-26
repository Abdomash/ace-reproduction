from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import ACE_ROOT, RESULTS_ROOT, maybe_append, maybe_append_bool, python_bin, run_command


def build_command(
    *,
    task_name: str,
    mode: str,
    save_path: Path,
    benchmark: str,
    run_type: str,
    config_slug: str,
    config_name: str,
    seed: int,
    api_provider: str,
    generator_provider: str | None,
    reflector_provider: str | None,
    curator_provider: str | None,
    generator_model: str,
    reflector_model: str,
    curator_model: str,
    sample_config_path: Path,
    sample_manifest_path: Path | None = None,
    train_limit: int | None = None,
    val_limit: int | None = None,
    test_limit: int | None = None,
    train_offset: int | None = None,
    val_offset: int | None = None,
    test_offset: int | None = None,
    sample_seed: int | None = None,
    shuffle_samples: bool = False,
    eval_steps: int = 100,
    test_workers: int = 20,
    max_tokens: int = 4096,
    telemetry: int = 1,
    telemetry_interval: float | None = None,
    resume_from: Path | None = None,
    checkpoint_enabled: bool = False,
    stop_after_stage: str | None = None,
    stop_after_step: int | None = None,
    run_metadata: dict[str, Any] | None = None,
) -> list[str]:
    argv = [
        python_bin(),
        "-m",
        "eval.finance.run",
        "--task_name",
        task_name,
        "--mode",
        mode,
        "--sample_config_path",
        str(sample_config_path),
        "--api_provider",
        api_provider,
        "--generator_model",
        generator_model,
        "--reflector_model",
        reflector_model,
        "--curator_model",
        curator_model,
        "--seed",
        str(seed),
        "--config_name",
        config_name,
        "--save_path",
        str(save_path),
        "--benchmark",
        benchmark,
        "--run_type",
        run_type,
        "--config_slug",
        config_slug,
        "--eval_steps",
        str(eval_steps),
        "--test_workers",
        str(test_workers),
        "--max_tokens",
        str(max_tokens),
    ]
    maybe_append(argv, "--generator_provider", generator_provider)
    maybe_append(argv, "--reflector_provider", reflector_provider)
    maybe_append(argv, "--curator_provider", curator_provider)
    maybe_append(argv, "--sample_manifest_path", sample_manifest_path)
    maybe_append(argv, "--train_limit", train_limit)
    maybe_append(argv, "--val_limit", val_limit)
    maybe_append(argv, "--test_limit", test_limit)
    maybe_append(argv, "--train_offset", train_offset)
    maybe_append(argv, "--val_offset", val_offset)
    maybe_append(argv, "--test_offset", test_offset)
    maybe_append(argv, "--sample_seed", sample_seed)
    maybe_append(argv, "--resume-from", resume_from)
    maybe_append(argv, "--stop-after-stage", stop_after_stage)
    maybe_append(argv, "--stop-after-step", stop_after_step)
    maybe_append(argv, "--run_metadata_json", (json.dumps(run_metadata, sort_keys=True) if run_metadata else None))
    maybe_append_bool(argv, "--shuffle_samples", shuffle_samples)
    maybe_append_bool(argv, "--telemetry_enabled", telemetry == 1)
    maybe_append(argv, "--telemetry_metrics_interval_seconds", telemetry_interval)
    maybe_append_bool(argv, "--checkpoint-enabled", checkpoint_enabled)
    return argv


def launch(argv: list[str], *, dry_run: bool = False) -> int:
    return run_command(argv, cwd=ACE_ROOT, dry_run=dry_run)


def config_dir(config_slug: str, run_type: str = "subset", benchmark: str = "ace-finer") -> Path:
    return RESULTS_ROOT / benchmark / run_type / config_slug
