# ACE Reproduction

This repository reproduces and extends ACE experiments with local runner scripts, AppWorld integration, MAESTRO-style telemetry, staged resumable runs, and post-run analysis.

## Layout

- `projects/`: vendored or modified upstream project trees.
- `runners/`: local subset runners, experiment launchers, and SLURM jobs.
- `context/`: user-created notes, plans, and research context for humans and agents.
- `analysis/`: analysis scripts and generated derived outputs.
- `results/`: raw experiment run artifacts only.

Raw run outputs belong under `results/`. Derived reports, summaries, plots, tables, and provenance manifests belong under `analysis/outputs/`.

## Common Entrypoints

```bash
runners/ace/run_experiments.sh finer_subset --dry-run
runners/ace/run_experiments.sh finer_full --checkpoint-enabled --stop-after-stage baseline-eval
runners/ace/run_experiments.sh appworld_full_eval --checkpoint-enabled --stop-after-stage adapt
python -m analysis results/ace-finer/subset/openrouter-gpt-oss-20b --benchmark finer
python analysis/scripts/ace/aggregate_experiments.py ace-finer/subset/openrouter-gpt-oss-20b
```

New resumable runs write `run_state.json` and `sessions.jsonl` in the run directory. FiNER runs also project lifecycle fields into `result_path.json`, `run_group.json`, and `final_results.json`; AppWorld full runs surface the same fields via `summary/run_summary.json`.

Environment file usage is documented in `context/ENVIRONMENT.md`. Keep real API keys in the ignored root `.env`.
