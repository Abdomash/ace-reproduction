# ACE Reproduction

This repository reproduces and extends ACE experiments with local runner scripts, AppWorld integration, MAESTRO-style telemetry, and post-run analysis.

## Layout

- `projects/`: vendored or modified upstream project trees.
- `runners/`: local smoke runners, experiment launchers, and SLURM jobs.
- `context/`: user-created notes, plans, and research context for humans and agents.
- `analysis/`: analysis scripts and generated derived outputs.
- `results/`: raw experiment run artifacts only.

Raw run outputs belong under `results/`. Derived reports, summaries, plots, tables, and provenance manifests belong under `analysis/outputs/`.

## Common Entrypoints

```bash
runners/ace/run_experiments.sh finer_subset --dry-run
python analysis/scripts/ace/summarize_runs.py results/openrouter_gptoss20b_smoke
python analysis/scripts/ace/aggregate_experiments.py openrouter_gptoss20b_smoke
```

Environment file usage is documented in `context/ENVIRONMENT.md`. Keep real API keys in the ignored root `.env`.
