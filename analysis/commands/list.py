from __future__ import annotations

from ..lib.common import format_timestamp
from .shared import build_command_result, get_runs, run_rows


def run(args):
    runs = get_runs(args, require_selection=False, allow_mixed_benchmarks=True)
    rows = [
        {
            "benchmark": run.benchmark,
            "size": run.run_type,
            "mode": run.mode,
            "config": run.config_slug,
            "run_id": run.run_leaf,
            "timestamp": format_timestamp(run.timestamp) or run.timestamp,
            "status": run.status,
            "checkpointing": run.checkpointing_enabled,
            "resume_count": run.resume_count,
            "current_stage": run.current_stage,
        }
        for run in runs
    ]
    return build_command_result(
        title="Runs",
        rows=rows,
        data={"count": len(rows), "runs": run_rows(runs)},
    )
