# ACE Reproduction

This repository reproduces and extends ACE experiments with local runner scripts, AppWorld integration, MAESTRO-style telemetry, and post-run analysis.

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
python -m analysis results/ace-finer/subset/openrouter-gpt-oss-20b --benchmark finer
python analysis/scripts/ace/aggregate_experiments.py ace-finer/subset/openrouter-gpt-oss-20b
```

Environment file usage is documented in `context/ENVIRONMENT.md`. Keep real API keys in the ignored root `.env`.
