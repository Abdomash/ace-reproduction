# MAESTRO Wrappers

These scripts run compatible MAESTRO analysis utilities against this repo's ACE result layout.

## Compatible Now

`plot_example_metrics.py` wraps MAESTRO's JSONL plotting entrypoint:

```bash
python analysis/scripts/maestro/plot_example_metrics.py ace-finer/subset/openrouter-gpt-oss-20b
```

It stages symlinks to telemetry files from `results/<benchmark>/<run_type>/<config_slug>/*/telemetry/` into the flat `traces/` and `metrics/` directories expected by MAESTRO, then writes derived plots/logs under `analysis/outputs/<analysis_id>/`.

## Not Directly Compatible

Most MAESTRO paper plotting scripts under `projects/maestro/plot/` expect consolidated MAESTRO parquet files with fields such as `example_name`, `tags`, model labels, and run IDs. ACE run folders do not currently provide that schema directly. Those scripts can be used after an explicit ACE-to-MAESTRO parquet conversion step is added.
