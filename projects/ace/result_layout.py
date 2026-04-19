"""Shared helpers for ACE result path identity metadata."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = REPO_ROOT / "results"
RUN_LEAF_RE = re.compile(r"^(?P<mode>[A-Za-z0-9_]+)_seed-(?P<seed>[^_]+)_(?P<timestamp>\d{8}_\d{6})$")


def slugify_path_segment(value: str) -> str:
    """Return a lowercase path-safe slug using hyphen separators."""
    slug = re.sub(r"[^A-Za-z0-9]+", "-", str(value).strip().lower()).strip("-")
    return slug or "default"


def benchmark_for_task(task_name: str) -> str:
    task = str(task_name or "default").lower()
    explicit = {
        "finer": "ace-finer",
        "formula": "ace-formula",
        "appworld": "ace-appworld",
        "mind2web": "ace-mind2web",
        "mind2web2": "ace-mind2web2",
    }
    return explicit.get(task, f"ace-{slugify_path_segment(task)}")


def build_run_leaf(mode: str, seed: Any, timestamp: str) -> str:
    return f"{mode}_seed-{seed}_{timestamp}"


def parse_run_leaf(run_leaf: str) -> dict[str, str] | None:
    match = RUN_LEAF_RE.match(str(run_leaf))
    if not match:
        return None
    return match.groupdict()


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def infer_identity_from_save_dir(save_dir: str | Path) -> dict[str, str]:
    path = Path(save_dir).resolve()
    try:
        parts = path.relative_to(RESULTS_ROOT.resolve()).parts
    except ValueError:
        return {}
    if len(parts) >= 3:
        return {
            "benchmark": parts[0],
            "run_type": parts[1],
            "config_slug": parts[2],
        }
    return {}


def resolve_path_identity(config: dict[str, Any] | None, save_dir: str | Path) -> dict[str, str]:
    config = config or {}
    inferred = infer_identity_from_save_dir(save_dir)
    task_name = config.get("task_name", "default")
    config_name = config.get("config_name", "default")
    return {
        "benchmark": str(
            config.get("benchmark") or inferred.get("benchmark") or benchmark_for_task(task_name)
        ),
        "run_type": str(config.get("run_type") or inferred.get("run_type") or "manual"),
        "config_slug": str(
            config.get("config_slug")
            or inferred.get("config_slug")
            or slugify_path_segment(config_name)
        ),
    }


def result_path_metadata(
    *,
    config: dict[str, Any] | None,
    save_dir: str | Path,
    run_dir: str | Path,
    run_leaf: str,
    mode: str,
    seed: Any,
    timestamp: str,
) -> dict[str, Any]:
    identity = resolve_path_identity(config, save_dir)
    return {
        "schema_version": 1,
        **identity,
        "mode": mode,
        "seed": seed,
        "timestamp": timestamp,
        "run_leaf": run_leaf,
        "run_dir": repo_relative(Path(run_dir)),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def write_result_path_json(
    *,
    config: dict[str, Any] | None,
    save_dir: str | Path,
    run_dir: str | Path,
    run_leaf: str,
    mode: str,
    seed: Any,
    timestamp: str,
) -> dict[str, Any]:
    metadata = result_path_metadata(
        config=config,
        save_dir=save_dir,
        run_dir=run_dir,
        run_leaf=run_leaf,
        mode=mode,
        seed=seed,
        timestamp=timestamp,
    )
    write_json(Path(run_dir) / "result_path.json", metadata)
    return metadata


def update_run_group(config_dir: str | Path, result_metadata: dict[str, Any]) -> dict[str, Any]:
    config_dir = Path(config_dir)
    group_path = config_dir / "run_group.json"
    identity = {
        "schema_version": 1,
        "benchmark": result_metadata["benchmark"],
        "run_type": result_metadata["run_type"],
        "config_slug": result_metadata["config_slug"],
    }
    entry = {
        "run_leaf": result_metadata["run_leaf"],
        "mode": result_metadata["mode"],
        "seed": result_metadata["seed"],
        "timestamp": result_metadata["timestamp"],
        "run_dir": result_metadata["run_dir"],
    }

    existing: dict[str, Any] = {}
    if group_path.exists():
        try:
            existing = json.loads(group_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

    runs_by_leaf = {
        str(run.get("run_leaf")): run
        for run in existing.get("runs", [])
        if isinstance(run, dict) and run.get("run_leaf")
    }
    runs_by_leaf[entry["run_leaf"]] = entry
    group = {
        **identity,
        "runs": sorted(
            runs_by_leaf.values(),
            key=lambda run: (str(run.get("timestamp") or ""), str(run.get("run_leaf") or "")),
        ),
    }
    write_json(group_path, group)
    return group
