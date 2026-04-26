from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from analysis.lib.discovery import discover_runs


@dataclass(frozen=True)
class RunnerRun:
    benchmark: str
    run_type: str | None
    config_slug: str | None
    run_leaf: str
    path: Path
    seed: int | None
    timestamp: str | None
    status: str | None
    sample_id: str | None
    config_id: str | None
    campaign_id: str | None
    config_name: str | None
    run_metadata: dict[str, Any]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def metadata_for_run(path: Path, benchmark: str) -> dict[str, Any]:
    run_config = _load_json(path / "run_config.json")
    if benchmark == "finer":
        config = run_config.get("config") or {}
        return {
            "campaign_id": config.get("campaign_id"),
            "sample_id": config.get("sample_id"),
            "config_id": config.get("config_id"),
            "config_name": config.get("config_name"),
            "sample_kind": config.get("sample_kind"),
            "tier_models": config.get("tier_models"),
            "resolved_models": config.get("resolved_models"),
            "sample_manifest_path": config.get("sample_manifest_path"),
        }
    summary = _load_json(path / "summary" / "run_summary.json")
    return {
        "campaign_id": summary.get("campaign_id") or run_config.get("campaign_id"),
        "sample_id": summary.get("sample_id") or run_config.get("sample_id"),
        "config_id": summary.get("config_id") or run_config.get("config_id"),
        "config_name": summary.get("config_name") or run_config.get("config_name"),
        "sample_kind": summary.get("sample_kind") or run_config.get("sample_kind"),
        "tier_models": summary.get("tier_models") or run_config.get("tier_models"),
        "resolved_models": summary.get("resolved_models") or run_config.get("resolved_models"),
        "sample_manifest_path": summary.get("sample_manifest_path") or run_config.get("sample_manifest_path"),
    }


def discover_runner_runs() -> list[RunnerRun]:
    runs: list[RunnerRun] = []
    for run in discover_runs():
        metadata = metadata_for_run(run.path, run.benchmark)
        runs.append(
            RunnerRun(
                benchmark=run.benchmark,
                run_type=run.run_type,
                config_slug=run.config_slug,
                run_leaf=run.run_leaf,
                path=run.path,
                seed=run.seed,
                timestamp=run.timestamp,
                status=run.status,
                sample_id=metadata.get("sample_id") or run.sample_id,
                config_id=metadata.get("config_id") or run.config_id or run.tier_config_id,
                campaign_id=metadata.get("campaign_id") or run.campaign_id,
                config_name=metadata.get("config_name"),
                run_metadata=metadata,
            )
        )
    return runs
