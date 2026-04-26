from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = REPO_ROOT / "results"
ACE_ROOT = REPO_ROOT / "projects" / "ace"
APPWORLD_ROOT = REPO_ROOT / "projects" / "ace-appworld"


def shell_join(argv: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in argv)


def run_command(argv: list[str], *, cwd: Path | None = None, dry_run: bool = False) -> int:
    command = shell_join(argv)
    print()
    print(f">>> {command}")
    if dry_run:
        return 0
    result = subprocess.run(argv, cwd=str(cwd) if cwd else None, check=False)
    return int(result.returncode)


def maybe_append(argv: list[str], flag: str, value: Any | None) -> None:
    if value is None or value == "":
        return
    argv.extend([flag, str(value)])


def maybe_append_bool(argv: list[str], flag: str, enabled: bool) -> None:
    if enabled:
        argv.append(flag)


def json_arg(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True)


def ensure_api_key(provider: str) -> None:
    mapping = {
        "openrouter": "OPENROUTER_API_KEY",
        "openai": "OPENAI_API_KEY",
        "together": "TOGETHER_API_KEY",
        "sambanova": "SAMBANOVA_API_KEY",
    }
    key_name = mapping.get(provider)
    if not key_name:
        raise SystemExit(f"Unsupported provider: {provider}")
    if not os.environ.get(key_name):
        raise SystemExit(f"Missing {key_name}")


def python_bin() -> str:
    return sys.executable or "python3"

