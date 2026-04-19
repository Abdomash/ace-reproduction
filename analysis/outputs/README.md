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

For ACE result groups, labels use the sanitized path under `results/`, for example
`ace-finer__subset__openrouter-gpt-oss-20b`.

`manifest.json` records the command, parameters, git commit, outputs, and all consumed raw result files. `inputs.jsonl` contains one row per input file with `path`, `sha256`, `bytes`, and `role`.
