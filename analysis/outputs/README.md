# Analysis Outputs

Generated analysis artifacts are written under deterministic, timestamped directories:

```text
analysis/outputs/
  <analysis_kind>__<campaign_or_comparison_label>__<YYYYMMDD_HHMMSS>/
    README.md
    manifest.json
    inputs.jsonl
    tables/
    plots/
    reports/
    logs/
```

`manifest.json` records the command, parameters, git commit, outputs, and all consumed raw result files. `inputs.jsonl` contains one row per input file with `path`, `sha256`, `bytes`, and `role`.
