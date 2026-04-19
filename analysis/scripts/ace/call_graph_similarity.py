#!/usr/bin/env python3
"""Compute pairwise call-graph similarity from ACE telemetry JSONL traces."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from _provenance import (
    finalize_output,
    existing_file_records,
    output_dir_for,
    repo_relative,
    result_path,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def find_runs(path_or_name: str) -> list[Path]:
    root = result_path(path_or_name)
    if (root / "run_config.json").exists():
        return [root]
    return sorted(
        p for p in root.rglob("run_config.json")
        if "analysis" not in p.parts
        for p in [p.parent]
    )


def span_label(span: dict[str, Any]) -> str:
    attrs = span.get("attributes") or {}
    agent = span.get("agent_name") or attrs.get("agent.name") or "unknown"
    operation = attrs.get("gen_ai.operation.name") or span.get("name") or "unknown"
    return f"{agent}:{operation}"


def ordered_labels(run_dir: Path) -> list[str]:
    spans: list[tuple[int, str]] = []
    for path in sorted((run_dir / "telemetry").glob("*.otel.jsonl")):
        for span in iter_jsonl(path):
            spans.append((int(span.get("start_time") or 0), span_label(span)))
    spans.sort(key=lambda item: item[0])
    return [label for _, label in spans]


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    if not union:
        return 1.0
    return len(left & right) / len(union)


def lcs_length(left: list[str], right: list[str]) -> int:
    if not left or not right:
        return 0
    previous = [0] * (len(right) + 1)
    for left_item in left:
        current = [0]
        for idx, right_item in enumerate(right, start=1):
            if left_item == right_item:
                current.append(previous[idx - 1] + 1)
            else:
                current.append(max(previous[idx], current[-1]))
        previous = current
    return previous[-1]


def normalized_lcs(left: list[str], right: list[str]) -> float:
    denom = max(len(left), len(right))
    if denom == 0:
        return 1.0
    return lcs_length(left, right) / denom


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", help="Campaign directory path or name under ./results")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: analysis/outputs/<analysis_id>)",
    )
    args = parser.parse_args()

    runs = find_runs(args.campaign)
    if not runs:
        raise FileNotFoundError("No run_config.json files found")

    analysis_id, created_at, output_dir = output_dir_for(
        "call_graph",
        Path(args.campaign).name,
        args.output_dir,
    )
    tables_dir = output_dir / "tables"
    reports_dir = output_dir / "reports"
    tables_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    labels_by_run = {run: ordered_labels(run) for run in runs}
    rows = []
    for idx, left in enumerate(runs):
        for right in runs[idx + 1:]:
            left_labels = labels_by_run[left]
            right_labels = labels_by_run[right]
            rows.append(
                {
                    "left_run_id": left.name,
                    "right_run_id": right.name,
                    "left_span_count": len(left_labels),
                    "right_span_count": len(right_labels),
                    "label_jaccard": jaccard(set(left_labels), set(right_labels)),
                    "normalized_lcs": normalized_lcs(left_labels, right_labels),
                }
            )

    combined = tables_dir / "call_graph_similarity.csv"
    with combined.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "left_run_id",
            "right_run_id",
            "left_span_count",
            "right_span_count",
            "label_jaccard",
            "normalized_lcs",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    jaccard_path = tables_dir / "call_graph_jaccard.csv"
    lcs_path = tables_dir / "call_graph_lcs.csv"
    run_names = [run.name for run in runs]
    matrices = {
        jaccard_path: lambda a, b: jaccard(set(labels_by_run[a]), set(labels_by_run[b])),
        lcs_path: lambda a, b: normalized_lcs(labels_by_run[a], labels_by_run[b]),
    }
    for path, metric in matrices.items():
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["run_id", *run_names])
            for left in runs:
                writer.writerow([left.name, *[metric(left, right) for right in runs]])

    summary_path = reports_dir / "summary.md"
    summary_path.write_text(
        "# Call Graph Similarity\n\n"
        f"- Campaign: `{args.campaign}`\n"
        f"- Runs: {len(runs)}\n"
        f"- Pairwise rows: {len(rows)}\n",
        encoding="utf-8",
    )
    input_records = existing_file_records(
        item
        for run_dir in runs
        for item in [
            (run_dir / "run_config.json", "run_config"),
            *[(path, "telemetry_trace") for path in sorted((run_dir / "telemetry").glob("*.otel.jsonl"))],
        ]
    )
    finalize_output(
        output_dir,
        analysis_id=analysis_id,
        analysis_kind="call_graph",
        label=Path(args.campaign).name,
        created_at=created_at,
        command="python " + " ".join(sys.argv),
        parameters={"campaign": args.campaign},
        input_records=input_records,
        outputs=[
            combined.relative_to(output_dir).as_posix(),
            jaccard_path.relative_to(output_dir).as_posix(),
            lcs_path.relative_to(output_dir).as_posix(),
            summary_path.relative_to(output_dir).as_posix(),
        ],
    )

    print(f"Wrote {len(rows)} pairwise rows to {combined}")
    print(f"Wrote matrices to {jaccard_path} and {lcs_path}")


if __name__ == "__main__":
    main()
