from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any


RUN_STATE_FILENAME = "run_state.json"
SESSIONS_FILENAME = "sessions.jsonl"
CHECKPOINTS_DIRNAME = "checkpoints"
TRAIN_CHECKPOINT_FILENAME = "train_checkpoint.json"
SCHEMA_VERSION = 1

STATUS_IN_PROGRESS = "in_progress"
STATUS_CHECKPOINTED = "checkpointed"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

LIFECYCLE_FIELD_NAMES = (
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
)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: str | Path) -> Any | None:
    path = Path(path)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def iter_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    path = Path(path)
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def write_json_atomic(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=False)
            handle.write("\n")
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def append_jsonl(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=False) + "\n")


def lifecycle_fields_from_state(state: dict[str, Any] | None) -> dict[str, Any]:
    state = state or {}
    return {key: state.get(key) for key in LIFECYCLE_FIELD_NAMES}


def default_legacy_lifecycle() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS_COMPLETED,
        "checkpointing_enabled": False,
        "resume_enabled": False,
        "has_checkpoints": False,
        "resume_count": 0,
        "current_stage": None,
        "last_completed_stage": None,
        "active_runtime_seconds": None,
        "started_at": None,
        "last_resumed_at": None,
        "last_checkpoint_at": None,
        "completed_at": None,
        "failure_reason": None,
    }


def new_run_state(
    *,
    run_id: str,
    checkpointing_enabled: bool,
    resume_enabled: bool,
    current_stage: str | None,
    started_at: str | None = None,
) -> dict[str, Any]:
    started_at = started_at or now_utc_iso()
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "status": STATUS_IN_PROGRESS,
        "checkpointing_enabled": bool(checkpointing_enabled),
        "resume_enabled": bool(resume_enabled),
        "has_checkpoints": False,
        "resume_count": 0,
        "current_stage": current_stage,
        "last_completed_stage": None,
        "active_runtime_seconds": 0.0,
        "started_at": started_at,
        "last_resumed_at": started_at,
        "last_checkpoint_at": None,
        "completed_at": None,
        "failure_reason": None,
    }


def load_run_state(run_dir: str | Path) -> dict[str, Any] | None:
    return load_json(Path(run_dir) / RUN_STATE_FILENAME)


def load_run_state_with_defaults(run_dir: str | Path) -> dict[str, Any]:
    state = load_run_state(run_dir)
    if not state:
        return default_legacy_lifecycle()
    merged = default_legacy_lifecycle()
    merged.update(state)
    return merged


def persist_run_state(run_dir: str | Path, state: dict[str, Any]) -> Path:
    path = Path(run_dir) / RUN_STATE_FILENAME
    write_json_atomic(path, state)
    return path


def update_run_state(run_dir: str | Path, **updates: Any) -> dict[str, Any]:
    state = load_run_state(run_dir) or default_legacy_lifecycle()
    state.update(updates)
    persist_run_state(run_dir, state)
    return state


def checkpoints_dir(run_dir: str | Path) -> Path:
    path = Path(run_dir) / CHECKPOINTS_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def train_checkpoint_path(run_dir: str | Path) -> Path:
    return checkpoints_dir(run_dir) / TRAIN_CHECKPOINT_FILENAME


def persist_train_checkpoint(run_dir: str | Path, payload: dict[str, Any]) -> Path:
    path = train_checkpoint_path(run_dir)
    write_json_atomic(path, payload)
    state = load_run_state(run_dir) or default_legacy_lifecycle()
    state["has_checkpoints"] = True
    state["last_checkpoint_at"] = now_utc_iso()
    persist_run_state(run_dir, state)
    return path


def load_train_checkpoint(run_dir: str | Path) -> dict[str, Any] | None:
    return load_json(train_checkpoint_path(run_dir))


@dataclass
class SessionRuntime:
    session_id: str
    started_at: str
    stage_entered: str | None
    resume_from_checkpoint: bool
    start_perf_counter: float


def start_session(
    run_dir: str | Path,
    state: dict[str, Any],
    *,
    stage_entered: str | None,
    resume_from_checkpoint: bool,
) -> SessionRuntime:
    started_at = now_utc_iso()
    session_id = f"session_{int(time.time() * 1000)}"
    state["status"] = STATUS_IN_PROGRESS
    state["current_stage"] = stage_entered
    state["completed_at"] = None
    state["failure_reason"] = None
    state["last_resumed_at"] = started_at
    if resume_from_checkpoint:
        state["resume_count"] = int(state.get("resume_count") or 0) + 1
    persist_run_state(run_dir, state)
    return SessionRuntime(
        session_id=session_id,
        started_at=started_at,
        stage_entered=stage_entered,
        resume_from_checkpoint=resume_from_checkpoint,
        start_perf_counter=time.perf_counter(),
    )


def finish_session(
    run_dir: str | Path,
    state: dict[str, Any],
    runtime: SessionRuntime,
    *,
    stage_exited: str | None,
    status: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    elapsed = max(0.0, time.perf_counter() - runtime.start_perf_counter)
    ended_at = now_utc_iso()
    row = {
        "session_id": runtime.session_id,
        "started_at": runtime.started_at,
        "ended_at": ended_at,
        "active_runtime_seconds": elapsed,
        "stage_entered": runtime.stage_entered,
        "stage_exited": stage_exited,
        "resume_from_checkpoint": runtime.resume_from_checkpoint,
    }
    append_jsonl(Path(run_dir) / SESSIONS_FILENAME, row)
    state["active_runtime_seconds"] = float(state.get("active_runtime_seconds") or 0.0) + elapsed
    if stage_exited is not None:
        state["current_stage"] = stage_exited
    if status is not None:
        state["status"] = status
    if status == STATUS_COMPLETED:
        state["completed_at"] = ended_at
    persist_run_state(run_dir, state)
    return state, row
