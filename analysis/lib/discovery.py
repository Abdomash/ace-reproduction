from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .common import RESULTS_ROOT, extract_timestamp, load_json, normalize_benchmark, repo_relative
from .selectors import SelectorSet


@dataclass(frozen=True)
class RunRecord:
    path: Path
    benchmark: str
    benchmark_raw: str
    run_type: str | None
    config_slug: str | None
    run_leaf: str
    seed: int | None
    timestamp: str | None
    mode: str | None
    run_group_path: Path | None
    status: str | None
    checkpointing_enabled: bool | None
    has_checkpoints: bool | None
    resume_count: int | None
    current_stage: str | None
    last_completed_stage: str | None
    active_runtime_seconds: float | None

    @property
    def repo_relative_path(self) -> str:
        return repo_relative(self.path)

    @property
    def config_path(self) -> Path:
        return self.path.parent

    @property
    def config_selector(self) -> str:
        return repo_relative(self.config_path)

    @property
    def campaign_selector(self) -> str:
        return repo_relative(self.config_path)


def _finer_run_records() -> list[RunRecord]:
    runs: list[RunRecord] = []
    for result_path_file in sorted(RESULTS_ROOT.rglob("result_path.json")):
        run_dir = result_path_file.parent
        identity = load_json(result_path_file) or {}
        run_config = load_json(run_dir / "run_config.json") or {}
        config = run_config.get("config") or {}
        run_state = load_json(run_dir / "run_state.json") or {}
        benchmark_raw = identity.get("benchmark") or config.get("benchmark") or "ace-finer"
        config_dir = run_dir.parent
        runs.append(
            RunRecord(
                path=run_dir.resolve(),
                benchmark=normalize_benchmark(benchmark_raw) or "finer",
                benchmark_raw=benchmark_raw,
                run_type=identity.get("run_type") or config.get("run_type"),
                config_slug=identity.get("config_slug") or config.get("config_slug") or config_dir.name,
                run_leaf=identity.get("run_leaf") or run_dir.name,
                seed=identity.get("seed") or config.get("seed"),
                timestamp=identity.get("timestamp") or extract_timestamp(run_dir.name),
                mode=identity.get("mode") or run_config.get("mode") or config.get("mode"),
                run_group_path=(config_dir / "run_group.json") if (config_dir / "run_group.json").exists() else None,
                status=run_state.get("status") or identity.get("status") or "completed",
                checkpointing_enabled=run_state.get("checkpointing_enabled", identity.get("checkpointing_enabled", False)),
                has_checkpoints=run_state.get("has_checkpoints", identity.get("has_checkpoints", False)),
                resume_count=run_state.get("resume_count", identity.get("resume_count", 0)),
                current_stage=run_state.get("current_stage") or identity.get("current_stage"),
                last_completed_stage=run_state.get("last_completed_stage") or identity.get("last_completed_stage"),
                active_runtime_seconds=run_state.get("active_runtime_seconds", identity.get("active_runtime_seconds")),
            )
        )
    return runs


def _appworld_run_records() -> list[RunRecord]:
    seen: set[Path] = set()
    runs: list[RunRecord] = []
    for summary_file in sorted(RESULTS_ROOT.rglob("summary/run_summary.json")):
        run_dir = summary_file.parent.parent.resolve()
        if run_dir in seen:
            continue
        seen.add(run_dir)
        parts = run_dir.relative_to(RESULTS_ROOT).parts
        benchmark_raw = parts[0] if len(parts) >= 1 else "ace-appworld"
        run_type = parts[1] if len(parts) >= 2 else None
        config_slug = parts[2] if len(parts) >= 3 else None
        run_summary = load_json(summary_file) or {}
        run_state = load_json(run_dir / "run_state.json") or {}
        runs.append(
            RunRecord(
                path=run_dir,
                benchmark=normalize_benchmark(benchmark_raw) or "appworld",
                benchmark_raw=benchmark_raw,
                run_type=run_type,
                config_slug=config_slug,
                run_leaf=run_dir.name,
                seed=None,
                timestamp=extract_timestamp(run_dir.name),
                mode=run_summary.get("mode"),
                run_group_path=(run_dir.parent / "run_group.json") if (run_dir.parent / "run_group.json").exists() else None,
                status=run_state.get("status") or run_summary.get("status") or "completed",
                checkpointing_enabled=run_state.get("checkpointing_enabled", run_summary.get("checkpointing_enabled", False)),
                has_checkpoints=run_state.get("has_checkpoints", run_summary.get("has_checkpoints", False)),
                resume_count=run_state.get("resume_count", run_summary.get("resume_count", 0)),
                current_stage=run_state.get("current_stage") or run_summary.get("current_stage"),
                last_completed_stage=run_state.get("last_completed_stage") or run_summary.get("last_completed_stage"),
                active_runtime_seconds=run_state.get("active_runtime_seconds", run_summary.get("active_runtime_seconds")),
            )
        )
    return runs


def discover_runs() -> list[RunRecord]:
    runs = _finer_run_records() + _appworld_run_records()
    runs.sort(key=lambda run: (run.benchmark, run.run_type or "", run.config_slug or "", run.timestamp or "", run.run_leaf))
    return runs


def _match_existing_path(run: RunRecord, selector: str) -> tuple[bool, str | None]:
    candidate = Path(selector)
    if candidate.exists():
        resolved = candidate.resolve()
        if resolved == run.path:
            return True, "run"
        if resolved == run.config_path:
            return True, "config"
        if resolved in run.path.parents:
            return True, "campaign"
    return False, None


def _path_selector_matches(run: RunRecord, selector: str) -> bool:
    matched, _ = _match_existing_path(run, selector)
    if matched:
        return True
    run_path = run.repo_relative_path
    config_path = run.config_selector
    return (
        selector == run.run_leaf
        or run_path.endswith(selector)
        or run_path == selector
        or config_path.endswith(selector)
        or config_path == selector
    )


def _campaign_selector_matches(run: RunRecord, selector: str) -> bool:
    matched, matched_kind = _match_existing_path(run, selector)
    if matched:
        return matched_kind in {"campaign", "config", "run"}
    run_path = run.repo_relative_path
    config_path = run.config_selector
    benchmark_path = "/".join(part for part in [run.benchmark_raw, run.run_type, run.config_slug] if part)
    return (
        run_path.startswith(selector)
        or config_path.startswith(selector)
        or selector == config_path
        or selector == benchmark_path
        or config_path.endswith(selector)
    )


def _config_selector_matches(run: RunRecord, selector: str) -> bool:
    matched, matched_kind = _match_existing_path(run, selector)
    if matched:
        return matched_kind in {"config", "campaign"}
    return selector == run.config_slug or selector == run.config_selector or run.config_selector.endswith(selector)


def _run_selector_matches(run: RunRecord, selector: str) -> bool:
    matched, matched_kind = _match_existing_path(run, selector)
    if matched:
        return matched_kind == "run"
    run_path = run.repo_relative_path
    return selector == run.run_leaf or selector == run_path or run_path.endswith(selector)


def _infer_target_kind(selector: str, runs: list[RunRecord]) -> str:
    config_matches = [run for run in runs if _config_selector_matches(run, selector)]
    run_matches = [run for run in runs if _run_selector_matches(run, selector)]
    campaign_matches = [run for run in runs if _campaign_selector_matches(run, selector)]

    unique_run_leaves = {run.run_leaf for run in run_matches}
    unique_configs = {run.config_slug for run in config_matches}
    if len(unique_run_leaves) == 1 and len(run_matches) == 1:
        return "run"
    if len(unique_configs) == 1 and config_matches:
        return "config"
    if campaign_matches:
        return "campaign"
    return "run"


def _matches(run: RunRecord, selectors: SelectorSet) -> bool:
    if selectors.benchmark and run.benchmark != selectors.benchmark:
        return False
    if selectors.run_type and run.run_type != selectors.run_type:
        return False
    if selectors.config and not _config_selector_matches(run, selectors.config):
        return False
    if selectors.seed is not None and run.seed != selectors.seed:
        return False
    if selectors.run and not _run_selector_matches(run, selectors.run):
        return False
    if selectors.campaign and not _campaign_selector_matches(run, selectors.campaign):
        return False
    return True


def select_runs(selectors: SelectorSet) -> list[RunRecord]:
    discovered = discover_runs()
    runs = [run for run in discovered if _matches(run, selectors)]
    if selectors.target and not (selectors.run or selectors.config or selectors.campaign):
        kind = selectors.target_kind
        if kind == "auto":
            kind = _infer_target_kind(selectors.target, runs or discovered)
        if kind == "run":
            runs = [run for run in runs if _run_selector_matches(run, selectors.target)]
        elif kind == "config":
            runs = [run for run in runs if _config_selector_matches(run, selectors.target)]
        elif kind == "campaign":
            runs = [run for run in runs if _campaign_selector_matches(run, selectors.target)]
    if selectors.latest and runs:
        runs = [max(runs, key=lambda run: (run.timestamp or "", run.path.stat().st_mtime, run.run_leaf))]
    return runs
