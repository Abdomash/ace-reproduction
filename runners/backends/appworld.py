from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .common import APPWORLD_ROOT, RESULTS_ROOT, maybe_append, maybe_append_bool, python_bin, run_command


def config_dir(config_slug: str, run_type: str = "subset", benchmark: str = "ace-appworld") -> Path:
    return RESULTS_ROOT / benchmark / run_type / config_slug


def appworld_python_bin(appworld_root: Path) -> str:
    candidate = appworld_root / ".venv" / "bin" / "python"
    if candidate.exists():
        return str(candidate)
    return python_bin()


def build_full_eval_command(
    *,
    save_path: Path,
    config_name: str,
    seed: int,
    generator_provider: str,
    generator_model: str,
    reflector_provider: str,
    reflector_model: str,
    curator_provider: str,
    curator_model: str,
    appworld_root: Path = APPWORLD_ROOT,
    max_steps: int = 30,
    max_tokens: int = 4096,
    telemetry: int = 1,
    telemetry_interval: float | None = None,
    initial_playbook_path: Path | None = None,
    resume_from: Path | None = None,
    checkpoint_enabled: bool = False,
    stop_after_stage: str | None = None,
    stop_after_task: int | None = None,
    checkpoint_every_task: int = 1,
    test_workers: int = 1,
    enabled_stages: list[str] | None = None,
    task_manifest_paths: dict[str, Path] | None = None,
    run_metadata: dict[str, Any] | None = None,
) -> list[str]:
    argv = [
        appworld_python_bin(appworld_root),
        str(Path(__file__).resolve().parents[2] / "runners" / "ace" / "run_appworld_full.py"),
        "--appworld-root",
        str(appworld_root),
        "--save-path",
        str(save_path),
        "--config-name",
        config_name,
        "--seed",
        str(seed),
        "--generator-provider",
        generator_provider,
        "--generator-model",
        generator_model,
        "--reflector-provider",
        reflector_provider,
        "--reflector-model",
        reflector_model,
        "--curator-provider",
        curator_provider,
        "--curator-model",
        curator_model,
        "--max-steps",
        str(max_steps),
        "--max-tokens",
        str(max_tokens),
        "--telemetry",
        str(telemetry),
        "--test-workers",
        str(test_workers),
        "--initial-playbook-path",
        str(initial_playbook_path or appworld_root / "experiments" / "playbooks" / "appworld_initial_playbook.txt"),
    ]
    maybe_append(argv, "--telemetry-interval", telemetry_interval)
    maybe_append(argv, "--resume-from", resume_from)
    maybe_append(argv, "--stop-after-stage", stop_after_stage)
    maybe_append(argv, "--stop-after-task", stop_after_task)
    maybe_append(argv, "--checkpoint-every-task", checkpoint_every_task)
    maybe_append(argv, "--enabled-stages", ",".join(enabled_stages or []))
    maybe_append_bool(argv, "--checkpoint-enabled", checkpoint_enabled)
    if run_metadata:
        maybe_append(argv, "--run-metadata-json", json.dumps(run_metadata, sort_keys=True))
    for stage_name, manifest_path in sorted((task_manifest_paths or {}).items()):
        maybe_append(argv, f"--{stage_name}-task-manifest", manifest_path)
    return argv


def launch(argv: list[str], *, dry_run: bool = False) -> int:
    env = os.environ.copy()
    env.setdefault("APPWORLD_PROJECT_PATH", str(APPWORLD_ROOT))
    return run_command(argv, cwd=Path(__file__).resolve().parents[2], dry_run=dry_run)
