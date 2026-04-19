# Analysis

This directory contains analysis code and generated derived outputs.

- `scripts/ace/`: ACE analysis scripts.
- `scripts/maestro/`: wrappers for compatible MAESTRO analysis utilities.
- `outputs/`: generated reports, summaries, plots, tables, and manifests.

Analysis scripts resolve campaign names against `<repo>/results`. For example:

```bash
python analysis/scripts/ace/summarize_runs.py results/openrouter_gptoss20b_smoke
python analysis/scripts/ace/aggregate_experiments.py openrouter_gptoss20b_smoke
python analysis/scripts/ace/call_graph_similarity.py openrouter_gptoss120b_smoke
python analysis/scripts/maestro/plot_example_metrics.py openrouter_gptoss20b_smoke
```

Each generated output directory must include:

- `README.md`
- `manifest.json`
- `inputs.jsonl`

Manifests identify raw input files by repository-relative path, SHA-256, byte size, and role. Analysis scripts should reference raw result files in place instead of copying them.
