from __future__ import annotations

from datetime import datetime
import json
import re
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = REPO_ROOT / "results"


def load_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj


def normalize_benchmark(value: str | None) -> str | None:
    mapping = {
        "ace-finer": "finer",
        "finer": "finer",
        "ace-appworld": "appworld",
        "appworld": "appworld",
    }
    return mapping.get(value or "", value)


def extract_timestamp(*values: object) -> str | None:
    for value in values:
        if not value:
            continue
        match = re.search(r"(\d{8}_\d{6})", str(value))
        if match:
            return match.group(1)
    return None


def repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def format_timestamp(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d_%H%M%S").strftime("%b %d, %Y at %H:%M:%S")
    except ValueError:
        return value
