#!/usr/bin/env python3
"""Move current ACE result runs from old campaign folders into the subset layout."""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ACE_ROOT = REPO_ROOT / "projects" / "ace"
if str(ACE_ROOT) not in sys.path:
    sys.path.insert(0, str(ACE_ROOT))

from result_layout import update_run_group, write_result_path_json  # noqa: E402


@dataclass(frozen=True)
class Mapping:
    old: str
    benchmark: str
    run_type: str
    config_slug: str
    mode: str
    seed: int
    timestamp: str

    @property
    def run_leaf(self) -> str:
        return f"{self.mode}_seed-{self.seed}_{self.timestamp}"

    @property
    def new(self) -> str:
        return (
            f"results/{self.benchmark}/{self.run_type}/"
            f"{self.config_slug}/{self.run_leaf}"
        )


MAPPINGS = [
    Mapping(
        "results/openrouter_gptoss20b_smoke/ace_finer_offline_ace_all_gptoss20b_subset_smoke_42_20260418_175143",
        "ace-finer",
        "subset",
        "openrouter-gpt-oss-20b",
        "offline",
        42,
        "20260418_175143",
    ),
    Mapping(
        "results/openrouter_gptoss20b_smoke/ace_finer_offline_ace_all_gptoss20b_subset_smoke_42_20260418_223218",
        "ace-finer",
        "subset",
        "openrouter-gpt-oss-20b",
        "offline",
        42,
        "20260418_223218",
    ),
    Mapping(
        "results/openrouter_gptoss120b_smoke/ace_finer_offline_ace_all_gptoss120b_subset_smoke_42_20260418_143058",
        "ace-finer",
        "subset",
        "openrouter-gpt-oss-120b",
        "offline",
        42,
        "20260418_143058",
    ),
    Mapping(
        "results/openrouter_gptoss120b_smoke/ace_finer_offline_ace_all_gptoss120b_subset_smoke_42_20260418_171221",
        "ace-finer",
        "subset",
        "openrouter-gpt-oss-120b",
        "offline",
        42,
        "20260418_171221",
    ),
    Mapping(
        "results/openrouter_gptoss120b_smoke/ace_finer_offline_ace_all_gptoss120b_subset_smoke_42_20260418_221428",
        "ace-finer",
        "subset",
        "openrouter-gpt-oss-120b",
        "offline",
        42,
        "20260418_221428",
    ),
    Mapping(
        "results/openrouter_gptoss120b_smoke/ace_finer_offline_ace_all_gptoss120b_subset_smoke_42_20260419_024022",
        "ace-finer",
        "subset",
        "openrouter-gpt-oss-120b",
        "offline",
        42,
        "20260419_024022",
    ),
    Mapping(
        "results/openrouter_minimax-m2.7_smoke/ace_finer_offline_ace_all_minimax-m2.7_subset_smoke_42_20260418_230446",
        "ace-finer",
        "subset",
        "openrouter-minimax-m2-7",
        "offline",
        42,
        "20260418_230446",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Move directories permanently. Default is dry-run only.",
    )
    return parser.parse_args()


def validate_mapping(mapping: Mapping) -> tuple[Path, Path]:
    source = REPO_ROOT / mapping.old
    destination = REPO_ROOT / mapping.new
    if not source.exists():
        raise FileNotFoundError(f"Source run does not exist: {mapping.old}")
    if not source.is_dir():
        raise NotADirectoryError(f"Source is not a directory: {mapping.old}")
    if destination.exists():
        raise FileExistsError(f"Destination already exists: {mapping.new}")
    return source, destination


def write_metadata(mapping: Mapping, run_dir: Path) -> None:
    config = {
        "benchmark": mapping.benchmark,
        "run_type": mapping.run_type,
        "config_slug": mapping.config_slug,
        "seed": mapping.seed,
        "task_name": "finer",
    }
    config_dir = run_dir.parent
    result_metadata = write_result_path_json(
        config=config,
        save_dir=config_dir,
        run_dir=run_dir,
        run_leaf=mapping.run_leaf,
        mode=mapping.mode,
        seed=mapping.seed,
        timestamp=mapping.timestamp,
    )
    update_run_group(config_dir, result_metadata)


def remove_empty_old_dirs(sources: list[Path]) -> None:
    old_parents = sorted({source.parent for source in sources}, key=lambda path: len(path.parts), reverse=True)
    for parent in old_parents:
        try:
            parent.rmdir()
            print(f"removed empty {parent.relative_to(REPO_ROOT).as_posix()}")
        except OSError:
            pass


def main() -> int:
    args = parse_args()
    planned: list[tuple[Mapping, Path, Path]] = []
    for mapping in MAPPINGS:
        source, destination = validate_mapping(mapping)
        planned.append((mapping, source, destination))

    print("Result layout migration")
    print(f"Mode: {'apply' if args.apply else 'dry-run'}")
    for mapping, _, _ in planned:
        print(f"{mapping.old} -> {mapping.new}")

    if not args.apply:
        print("Dry-run only; no files were modified.")
        return 0

    for mapping, source, destination in planned:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        write_metadata(mapping, destination)

    remove_empty_old_dirs([source for _, source, _ in planned])
    print("Migration complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
