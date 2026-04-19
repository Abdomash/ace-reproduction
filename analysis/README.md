# Analysis

This directory contains analysis code and generated derived outputs.

- `scripts/ace/`: ACE analysis scripts.
- `scripts/maestro/`: wrappers for compatible MAESTRO analysis utilities.
- `outputs/`: generated reports, summaries, plots, tables, and manifests.

Analysis scripts resolve campaign names against `<repo>/results`. For example:

```bash
python analysis/scripts/ace/summarize_runs.py results/ace-finer/subset/openrouter-gpt-oss-20b
python analysis/scripts/ace/aggregate_experiments.py ace-finer/subset/openrouter-gpt-oss-20b
python analysis/scripts/ace/call_graph_similarity.py ace-finer/subset/openrouter-gpt-oss-120b
python analysis/scripts/maestro/plot_example_metrics.py ace-finer/subset/openrouter-gpt-oss-20b
```

Each generated output directory must include:

- `README.md`
- `manifest.json`
- `inputs.jsonl`

Manifests identify raw input files by repository-relative path, SHA-256, byte size, and role. Analysis scripts should reference raw result files in place instead of copying them.
