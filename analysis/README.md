# Analysis

`analysis` is a small terminal-first CLI over raw artifacts in [`results/`](/home/abdo/ace-reproduction/results).

The intended workflows are:

- `python -m analysis list ...`
- `python -m analysis ...selectors...`

There is no separate `summary` command anymore. The default command is the report itself.

Selector naming model:

- `run`: one concrete run directory, for example `offline_seed-42_20260421_025609`
- `config`: one config/model directory containing one or more runs
- `campaign`: any directory subtree under `results/` that contains runs

Examples:

```bash
python -m analysis list --benchmark finer
python -m analysis --run offline_seed-42_20260421_025609
python -m analysis --config openrouter-gpt-oss-120b --benchmark finer
python -m analysis results/ace-finer/subset/openrouter-gpt-oss-120b
```

`list` prints compact discovery columns: `benchmark`, `size`, `mode`, `config`, `run_id`, and `timestamp`.

Behavior:

- The default report requires an explicit selector. It will not print the whole repo by default.
- Single-run mode prints a compact narrative report.
- Multi-run mode prints a comparison report only; it does not append full per-run reports afterward.
- Mixed-benchmark comparisons are rejected. Narrow them with `--benchmark`.
