# Results

This directory contains raw experiment outputs from runs.

Campaigns should be grouped by run label, for example:

```text
results/
  openrouter_gptoss20b_smoke/
    ace_finer_offline_<config>_<seed>_<timestamp>/
      run_config.json
      final_results.json
      detailed_llm_logs/
      telemetry/
```

Do not write derived reports, plots, tables, or summaries here. Use `analysis/outputs/` for derived analysis artifacts and provenance manifests.
