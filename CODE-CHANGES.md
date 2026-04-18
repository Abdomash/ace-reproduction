# Code Changes Needed

This file tracks the coding work needed to complete the project under the
updated assumption that GPT-oss-120b replaces GPT-oss-20b and is accessed
through OpenRouter.

The AppWorld integration itself is assumed to follow `APPWORLD.md`, using the
vendored `ace-appworld/` runner.

## Assumptions

- Cheap-model baseline is now GPT-oss-120b, served through OpenRouter's
  OpenAI-compatible API.
- GPT-oss-20b should be treated as obsolete for the final experiments.
- Stronger MiniMax-role experiments should use the OpenRouter model slug
  `minimax/minimax-m2.7`, not the older MiniMax-M2.5 label.
- OpenRouter is the only API provider used for final experiments. Both
  GPT-oss-120b and MiniMax-M2.7 are called through OpenRouter.
- Keep independent role provider configuration in the code because it is low
  effort and useful later. For the final project configs, set Generator,
  Reflector, and Curator providers to `openrouter`; role differences come from
  model slugs.
- AppWorld experiments should run through `ace-appworld/`, not the separate
  `ace/eval/appworld/` adapter.

## 1. Add OpenRouter Provider Support

Status: needed.

Replace MiniMax Provider with OpenRouter provider. OpenRouter is OpenAI-compatible, so this should be straightforward and mostly renaming stuff.

Relevant files:

- `ace/utils.py`
- `ace/eval/finance/run.py`
- `ace/.env.example`

Required behavior:

- Accept `--api_provider openrouter`.
- Read `OPENROUTER_API_KEY`.
- Default base URL to `https://openrouter.ai/api/v1`.
- Allow override via `OPENROUTER_BASE_URL`.
- Use OpenAI-compatible `openai.OpenAI(api_key=..., base_url=...)`.
- Record provider and base URL label in `run_config.json`, but never record API
  keys.

Suggested model name:

```text
openai/gpt-oss-120b
```

Confirm the exact OpenRouter model slug before final runs and store it in the
run config.

## 2. Add Per-Role Provider and Model Configuration

Status: needed.

The current FiNER ACE constructor initializes all three clients from one
provider. Add per-role provider support even though the final experiments will
set all roles to OpenRouter. This keeps the runner flexible and makes the
provider/model pairing explicit in result metadata.

Relevant files:

- `ace/ace/ace.py`
- `ace/utils.py`
- `ace/eval/finance/run.py`

Required CLI flags:

```text
--generator_provider
--reflector_provider
--curator_provider
--generator_model
--reflector_model
--curator_model
```

Backwards compatibility:

- Keep `--api_provider` as a global default.
- If a role-specific provider is not set, fall back to `--api_provider`.
- For final runs, `--api_provider`, `--generator_provider`,
  `--reflector_provider`, and `--curator_provider` should all resolve to
  `openrouter`.

Required config fields:

```json
{
  "api_provider": "openrouter",
  "generator_provider": "openrouter",
  "reflector_provider": "openrouter",
  "curator_provider": "openrouter",
  "generator_model": "openai/gpt-oss-120b",
  "reflector_model": "openai/gpt-oss-120b",
  "curator_model": "openai/gpt-oss-120b"
}
```

For mixed-model runs, this should support configurations such as:

```json
{
  "api_provider": "openrouter",
  "generator_provider": "openrouter",
  "generator_model": "openai/gpt-oss-120b",
  "reflector_provider": "openrouter",
  "reflector_model": "minimax/minimax-m2.7",
  "curator_provider": "openrouter",
  "curator_model": "openai/gpt-oss-120b"
}
```

Do not use a direct MiniMax API path for the final project. MiniMax should be
called as an OpenRouter model by setting `reflector_provider=openrouter` and
`reflector_model=minimax/minimax-m2.7`.

## 3. Update Run Scripts and Slurm Templates

Status: needed.

Replace GPT-oss-20b defaults with GPT-oss-120b on OpenRouter.

Relevant files:

- `ace/slurm/ace_finer_smoke.sbatch`
- `ace/slurm/ace_finer_pilot.sbatch`
- `ace/slurm/ace_finer_full.sbatch`
- any local shell snippets used for report runs

Required changes:

- Default provider should be `openrouter`.
- Default model should be the confirmed GPT-oss-120b OpenRouter slug.
- MiniMax runs should use `minimax/minimax-m2.7` with the same OpenRouter
  provider.
- Rename config labels from `gptoss20b` to `gptoss120b`.
- Ensure `OPENROUTER_API_KEY` is documented as required.

Example defaults:

```bash
: "${API_PROVIDER:=openrouter}"
: "${GENERATOR_PROVIDER:=${API_PROVIDER}}"
: "${REFLECTOR_PROVIDER:=${API_PROVIDER}}"
: "${CURATOR_PROVIDER:=${API_PROVIDER}}"
: "${GENERATOR_MODEL:=openai/gpt-oss-120b}"
: "${REFLECTOR_MODEL:=openai/gpt-oss-120b}"
: "${CURATOR_MODEL:=openai/gpt-oss-120b}"
```

Example mixed-model override:

```bash
API_PROVIDER=openrouter \
GENERATOR_PROVIDER=openrouter \
GENERATOR_MODEL=openai/gpt-oss-120b \
REFLECTOR_PROVIDER=openrouter \
REFLECTOR_MODEL=minimax/minimax-m2.7 \
CURATOR_PROVIDER=openrouter \
CURATOR_MODEL=openai/gpt-oss-120b \
CONFIG_NAME=ace_mixed_minimax_m27_reflector_gptoss120b_gen_curator
```

## 4. Add Dataset Slice Controls

Status: needed.

The experiment plan relies on fixed slice sizes such as 60/40/80 and larger
controlled runs. The runner should support deterministic slicing directly.

Relevant file:

- `ace/eval/finance/run.py`

Required CLI flags:

```text
--train_limit
--val_limit
--test_limit
--train_offset
--val_offset
--test_offset
--sample_seed
--shuffle_samples
```

Required behavior:

- If `--shuffle_samples` is unset, use deterministic contiguous slices from the
  selected offsets.
- If `--shuffle_samples` is set, shuffle with `--sample_seed` before slicing.
- Save selected indices, limits, offsets, and seed into `run_config.json`.

This makes the 60/40/80 pilot and later larger runs reproducible.

## 5. Add Cost Accounting for OpenRouter

Status: needed.

The project needs cost-accuracy plots. OpenRouter costs are provider/model
specific and should be captured explicitly. Aim to capture them automatically 
via https://openrouter.ai/docs/guides/administration/usage-accounting.

Relevant files:

- `ace/llm.py`
- `ace/analysis/local_partial_smoke_and_viz.py`
- new or existing analysis script for final aggregation

Required behavior:

- Add model pricing metadata in config

```json
{
  "pricing": {
    "openai/gpt-oss-120b": {
      ...
    }
  }
}
```

- Add current OpenRouter pricing used at experiment time.
- Compute per-call estimated cost from the responses metadata.
- Store `cost_usd` in each LLM call log.
- Aggregate cost by role and total run.

Do not hard-code prices without documenting the date/source in the final report
or run metadata.

## 6. Update Experiment Labels and Result Naming

Status: needed.

Avoid mixing old GPT-oss-20b and new GPT-oss-120b results.

Relevant files:

- `ace/ace/ace.py`
- `ace/eval/finance/run.py`
- Slurm scripts

Required behavior:

- Include role provider and role model names in `run_config.json`.
- Include `gptoss120b` in `config_name` defaults.
- Do not reuse old output directories labeled `gptoss20b`.

Recommended config names:

```text
react_no_playbook_gptoss120b
ace_all_gptoss120b
ace_all_minimax_m27
ace_mixed_minimax_m27_reflector_gptoss120b_gen_curator
```

## 7. Add Analysis Aggregator for Final Tables

Status: needed.

The current visualization helper is useful for one run, but the final report
needs multi-run tables.

Relevant files:

- `ace/analysis/local_partial_smoke_and_viz.py`
- new script, suggested: `ace/analysis/aggregate_experiments.py`

Required outputs:

- one CSV or JSON summary row per run
- accuracy fields
- no-answer count/rate
- role-level token totals
- role-level latency totals
- estimated role-level cost
- trace span count
- metrics summary
- playbook length/token growth

Suggested output:

```text
results/<campaign>/analysis/experiment_summary.csv
```

## 8. Add Call-Graph Similarity Analysis

Status: needed.

This directly supports the system-level behavior research question.

Relevant files:

- new script, suggested: `ace/analysis/call_graph_similarity.py`

Required behavior:

- Load MAESTRO OTEL JSONL traces from multiple run directories.
- Convert each trace into ordered labels:

```text
<agent.name>:<gen_ai.operation.name>
```

- Compute pairwise Jaccard similarity over label sets.
- Compute pairwise normalized LCS similarity over ordered labels.
- Output tables and optional heatmaps.

For AppWorld, include environment/tool spans when present.

## 9. Document Environment Setup

Status: needed.

Update docs so future runs use GPT-oss-120b through OpenRouter consistently.

Relevant files:

- `README.md` if present for the ACE reproduction flow
- `NOTES.md`
- `SLURM.md`
- `EXPERIMENTS.md`
- `ace/.env.example`

Required documentation:

```bash
export OPENROUTER_API_KEY="..."
export OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"
export OPENROUTER_HTTP_REFERER="https://github.com/<repo-or-project>"
export OPENROUTER_APP_TITLE="ACE MAESTRO Reproduction"
```

Also document the exact OpenRouter model slug chosen for GPT-oss-120b and
document `minimax/minimax-m2.7` as the stronger MiniMax model slug. Both are
called through OpenRouter.

## Minimum Code Completion Criteria

Before final experiments, the code should satisfy:

- FiNER can run with `--api_provider openrouter`. <!-- Running it with minimax works, but just to better understand that it also support any model in openrouter -->
- GPT-oss-120b on OpenRouter is the default cheap-model config.
- Generator, Reflector, and Curator can use independent provider/model settings.
- Final experiment configs set every role provider to `openrouter`.
- Run configs clearly record provider and model per role.
- Dataset slices are reproducible from saved limits/offsets/seeds.
- Cost accounting works for OpenRouter token usage.
- Multi-run aggregation can produce the final report tables.
- Call-graph similarity can be computed from telemetry traces.
