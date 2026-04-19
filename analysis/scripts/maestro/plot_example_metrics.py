#!/usr/bin/env python3
"""Run MAESTRO's JSONL telemetry plotting helper on ACE result campaigns.

This wrapper stages symlinks to ACE telemetry files into the flat trace/metrics
directories expected by ``projects/maestro/plot/plot_example_metrics.py``.
Raw result files stay under ``results/``.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ACE_ANALYSIS_SCRIPTS = REPO_ROOT / "analysis" / "scripts" / "ace"
if str(ACE_ANALYSIS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(ACE_ANALYSIS_SCRIPTS))

from _provenance import (  # noqa: E402
    finalize_output,
    existing_file_records,
    output_dir_for,
    repo_relative,
    result_label,
    result_path,
)


def find_telemetry_files(campaign_dir: Path) -> tuple[list[Path], list[Path]]:
    if (campaign_dir / "run_config.json").exists():
        roots = [campaign_dir]
    elif (campaign_dir / "telemetry").exists():
        roots = [campaign_dir]
    else:
        roots = sorted(path.parent for path in campaign_dir.rglob("run_config.json"))
        appworld_roots = sorted(
            {
                path.parent.parent
                for path in campaign_dir.rglob("telemetry/*.otel.jsonl")
                if path.parent.name == "telemetry"
            }
        )
        roots.extend(root for root in appworld_roots if root not in roots)

    trace_files: list[Path] = []
    metrics_files: list[Path] = []
    for run_dir in roots:
        telemetry_dir = run_dir / "telemetry"
        trace_files.extend(sorted(telemetry_dir.glob("*.otel.jsonl")))
        metrics_files.extend(sorted(telemetry_dir.glob("*.metrics.jsonl")))
    return trace_files, metrics_files


def stage_symlink(source: Path, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / source.name
    if destination.exists() or destination.is_symlink():
        destination.unlink()
    destination.symlink_to(source.resolve())
    return destination


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", help="Campaign directory path or name under results/")
    parser.add_argument(
        "--mode",
        choices=("latest", "per_run", "all"),
        default="per_run",
        help="MAESTRO plot_example_metrics mode.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Analysis output directory (default: analysis/outputs/<analysis_id>)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    campaign_dir = result_path(args.campaign)
    trace_files, metrics_files = find_telemetry_files(campaign_dir)
    if not trace_files:
        raise FileNotFoundError(f"No telemetry trace files found under {campaign_dir}")

    label = result_label(args.campaign, campaign_dir)
    analysis_id, created_at, output_dir = output_dir_for(
        "maestro_example_metrics",
        label,
        args.output_dir,
    )
    staging_dir = output_dir / "logs" / "maestro_inputs"
    traces_dir = staging_dir / "traces"
    metrics_dir = staging_dir / "metrics"
    plots_dir = output_dir / "plots" / "maestro_example_metrics"
    reports_dir = output_dir / "reports"
    logs_dir = output_dir / "logs"
    plots_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    for path in trace_files:
        stage_symlink(path, traces_dir)
    for path in metrics_files:
        stage_symlink(path, metrics_dir)

    env = os.environ.copy()
    env["PYTHONPATH"] = (
        f"{REPO_ROOT / 'projects' / 'maestro'}"
        + (f":{env['PYTHONPATH']}" if env.get("PYTHONPATH") else "")
    )
    command = [
        sys.executable,
        "-m",
        "plot.plot_example_metrics",
        "--mode",
        args.mode,
        "--traces-dir",
        str(traces_dir),
        "--metrics-dir",
        str(metrics_dir),
        "--output-dir",
        str(plots_dir),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT / "projects" / "maestro",
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    stdout_path = logs_dir / "maestro_plot_example_metrics.stdout.log"
    stderr_path = logs_dir / "maestro_plot_example_metrics.stderr.log"
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        print(completed.stdout, end="")
        print(completed.stderr, end="", file=sys.stderr)
        return completed.returncode

    compatibility_path = reports_dir / "compatibility.md"
    compatibility_path.write_text(
        "# MAESTRO Compatibility\n\n"
        "This wrapper uses MAESTRO's JSONL `plot.plot_example_metrics` entrypoint. "
        "It is compatible with ACE telemetry JSONL files after staging symlinks into "
        "flat `traces/` and `metrics/` directories. The MAESTRO parquet paper-figure "
        "scripts require a consolidated MAESTRO dataset/parquet schema and are not "
        "run directly against ACE result folders by this wrapper.\n",
        encoding="utf-8",
    )

    input_records = existing_file_records(
        [(path, "telemetry_trace") for path in trace_files]
        + [(path, "telemetry_metrics") for path in metrics_files]
    )
    output_entries = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if "maestro_inputs" in path.parts:
            continue
        output_entries.append(path.relative_to(output_dir).as_posix())

    finalize_output(
        output_dir,
        analysis_id=analysis_id,
        analysis_kind="maestro_example_metrics",
        label=label,
        created_at=created_at,
        command="python " + " ".join(sys.argv),
        parameters={
            "campaign": args.campaign,
            "mode": args.mode,
            "maestro_entrypoint": "plot.plot_example_metrics",
        },
        input_records=input_records,
        outputs=output_entries,
    )

    print(f"Ran MAESTRO plot_example_metrics for {repo_relative(campaign_dir)}")
    print(f"Output directory: {output_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
