from __future__ import annotations

import json
import re
import subprocess
import hashlib
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[3]
RESULTS_ROOT = REPO_ROOT / "results"
ANALYSIS_OUTPUTS_ROOT = REPO_ROOT / "analysis" / "outputs"


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip().lower()).strip("_")
    return slug or "analysis"


def reject_old_layout(path_or_name: str | Path) -> None:
    parts = Path(path_or_name).parts or (str(path_or_name),)
    if any("smoke" in part.lower() for part in parts):
        raise ValueError(
            "Old smoke result layouts are not supported. Use "
            "results/<benchmark>/<run_type>/<config_slug>."
        )


def result_label(path_or_name: str | Path, resolved_path: Path | None = None) -> str:
    path = (resolved_path or Path(path_or_name)).resolve()
    try:
        rel = path.relative_to(RESULTS_ROOT.resolve())
        parts = rel.parts
    except ValueError:
        parts = Path(path_or_name).parts
        if parts and parts[0] == "results":
            parts = parts[1:]
    cleaned = [slugify(part).replace("_", "-") for part in parts if part not in {"", "."}]
    return "__".join(cleaned) or slugify(str(path_or_name)).replace("_", "-")


def make_analysis_id(
    analysis_kind: str,
    label: str,
    created_at: datetime | None = None,
) -> str:
    timestamp = (created_at or datetime.now().astimezone()).strftime("%Y%m%d_%H%M%S")
    return f"{slugify(analysis_kind)}__{slugify(label)}__{timestamp}"


def git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def result_path(path_or_name: str | Path) -> Path:
    reject_old_layout(path_or_name)
    path = Path(path_or_name)
    if path.exists():
        return path.resolve()
    candidate = (RESULTS_ROOT / path).resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"Result path not found: {path_or_name}")
    return candidate


def output_dir_for(
    analysis_kind: str,
    label: str,
    output_dir: Path | None = None,
) -> tuple[str, datetime, Path]:
    created_at = datetime.now().astimezone()
    analysis_id = make_analysis_id(analysis_kind, label, created_at)
    destination = output_dir or (ANALYSIS_OUTPUTS_ROOT / analysis_id)
    return analysis_id, created_at, destination.resolve()


def file_record(path: Path, role: str) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "path": repo_relative(path),
        "sha256": digest.hexdigest(),
        "bytes": path.stat().st_size,
        "role": role,
    }


def existing_file_records(paths_and_roles: Iterable[tuple[Path, str]]) -> list[dict[str, Any]]:
    records = []
    seen: set[tuple[str, str]] = set()
    for path, role in paths_and_roles:
        if not path.exists() or not path.is_file():
            continue
        key = (str(path.resolve()), role)
        if key in seen:
            continue
        seen.add(key)
        records.append(file_record(path, role))
    return records


def group_inputs_by_run(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        path = Path(record["path"])
        run_dir = path.parent
        if path.parent.name in {"telemetry", "detailed_llm_logs", "analysis"}:
            run_dir = path.parent.parent
        grouped[run_dir.as_posix()].append(
            {key: value for key, value in record.items() if key != "role"}
        )
    return [
        {"run_dir": run_dir, "files": files}
        for run_dir, files in sorted(grouped.items(), key=lambda item: item[0])
    ]


def write_inputs_jsonl(output_dir: Path, records: Iterable[dict[str, Any]]) -> None:
    with (output_dir / "inputs.jsonl").open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def write_readme(output_dir: Path, analysis_id: str, analysis_kind: str, label: str) -> None:
    text = (
        f"# {analysis_id}\n\n"
        f"- Analysis kind: `{analysis_kind}`\n"
        f"- Label: `{label}`\n"
        "- Raw inputs are referenced by relative path and SHA-256 in `manifest.json` "
        "and `inputs.jsonl`.\n"
    )
    (output_dir / "README.md").write_text(text, encoding="utf-8")


def write_manifest(
    output_dir: Path,
    *,
    analysis_id: str,
    analysis_kind: str,
    created_at: datetime,
    command: str,
    parameters: dict[str, Any],
    input_records: list[dict[str, Any]],
    outputs: list[str],
) -> None:
    manifest = {
        "analysis_id": analysis_id,
        "analysis_kind": analysis_kind,
        "created_at": created_at.isoformat(),
        "git_commit": git_commit(),
        "command": command,
        "parameters": parameters,
        "inputs": group_inputs_by_run(input_records),
        "outputs": outputs,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def finalize_output(
    output_dir: Path,
    *,
    analysis_id: str,
    analysis_kind: str,
    label: str,
    created_at: datetime,
    command: str,
    parameters: dict[str, Any],
    input_records: list[dict[str, Any]],
    outputs: list[str],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_readme(output_dir, analysis_id, analysis_kind, label)
    write_inputs_jsonl(output_dir, input_records)
    write_manifest(
        output_dir,
        analysis_id=analysis_id,
        analysis_kind=analysis_kind,
        created_at=created_at,
        command=command,
        parameters=parameters,
        input_records=input_records,
        outputs=outputs,
    )
