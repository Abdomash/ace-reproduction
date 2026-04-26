# Results

This directory contains raw experiment outputs from runs.

Campaigns should be grouped by run label, for example:

```text
results/
  ace-finer/
    full/
      openrouter-gpt-oss-120b/
        run_group.json
        offline_seed-42_YYYYMMDD_HHMMSS/
          run_config.json
          result_path.json
          run_state.json
          sessions.jsonl
          final_results.json
          detailed_llm_logs/
          telemetry/
  ace-appworld/
    full/
      openrouter-gpt-oss-120b/
        full_seed-42_YYYYMMDD_HHMMSS/
          run_config.json
          run_state.json
          sessions.jsonl
          stages/
            adapt/
            eval-normal/
            eval-challenge/
          evaluations/
          summary/
            run_summary.json
```

Legacy runs may not contain lifecycle files. Analysis treats those as `completed` with checkpointing disabled unless a `run_state.json` override is present.

Do not write derived reports, plots, tables, or summaries here. Use `analysis/outputs/` for derived analysis artifacts and provenance manifests.
