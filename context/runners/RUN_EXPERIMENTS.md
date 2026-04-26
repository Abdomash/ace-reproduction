# Unified Experiment Runner

This document explains how to run quick subsets or broader runs using:

- `runners/ace/run_experiments.sh`

It supports FiNER subsets, Formula subsets, AppWorld subsets, staged AppWorld full runs, and combined full-style runs.
The runner is paper-faithful by default: standard chat-completion calls,
`max_tokens=4096`, provider JSON mode off, and no OpenRouter reasoning controls.

## 1) Prerequisites

- You are in the repository root.
- Python dependencies are installed (for example via `uv sync`)
- API key for your selected provider is exported:
  - `OPENROUTER_API_KEY` for `--provider openrouter`
  - `OPENAI_API_KEY` for `--provider openai`
  - `TOGETHER_API_KEY` for `--provider together`
  - `SAMBANOVA_API_KEY` for `--provider sambanova`

For AppWorld, make sure the vendored `ace-appworld` package and its experiment
extras are installed in a Python 3.11 environment:

```bash
runners/ace/setup_appworld.sh
```

The runner uses `projects/ace-appworld/.venv/bin/appworld` by default when it
exists. Set `APPWORLD_BIN=/path/to/appworld` if you use another prepared
environment.

## 2) Presets

Available presets:

- `finer_subset`: uses ACE sample slicing (60 train, 40 val, 80 test) and runs FiNER
- `finer_full`: runs FiNER using default full sample config
- `formula_subset`: uses ACE sample slicing for Formula and runs it
- `appworld_subset`: runs AppWorld `eval_only` on `dev`
- `appworld_full_eval`: creates one AppWorld full run directory and executes `adapt -> eval-normal -> eval-challenge`
- `all_full`: runs `finer_full` then `appworld_full_eval`

## 3) Quick examples

### A) FiNER subset (section-sized style)

```bash
runners/ace/run_experiments.sh finer_subset \
  --provider openrouter \
  --generator openai/gpt-oss-120b:nitro \
  --reflector openai/gpt-oss-120b:nitro \
  --curator openai/gpt-oss-120b:nitro \
  --config-name ace_all_openrouter_gptoss120b_subset \
  --seed 42 \
  --telemetry 1 \
  --telemetry-interval 5
```

Provider-returned hidden reasoning is not consumed by ACE agents. If a provider
returns no visible content or malformed provider JSON, the failed call/sample is
logged and counted as failed where the workflow can continue.

### B) AppWorld subset

```bash
runners/ace/run_experiments.sh appworld_subset \
  --provider openrouter \
  --generator openai/gpt-oss-120b:nitro \
  --reflector openai/gpt-oss-120b:nitro \
  --curator openai/gpt-oss-120b:nitro \
  --appworld-max-steps 20 \
  --config-name appworld_subset_gptoss20b \
  --seed 42
```

### C) Combined full-style run

```bash
runners/ace/run_experiments.sh all_full \
  --provider openrouter \
  --generator minimax/minimax-m2.7 \
  --reflector minimax/minimax-m2.7 \
  --curator minimax/minimax-m2.7 \
  --config-name ace_all_openrouter_minimax_m27 \
  --seed 42
```

### D) Staged stop/resume examples

```bash
runners/ace/run_experiments.sh finer_full \
  --provider openrouter \
  --generator openai/gpt-oss-120b:nitro \
  --reflector openai/gpt-oss-120b:nitro \
  --curator openai/gpt-oss-120b:nitro \
  --config-slug openrouter-gpt-oss-120b \
  --checkpoint-enabled \
  --stop-after-stage baseline-eval

runners/ace/run_experiments.sh finer_full \
  --resume-from results/ace-finer/full/openrouter-gpt-oss-120b/offline_seed-42_YYYYMMDD_HHMMSS

runners/ace/run_experiments.sh appworld_full_eval \
  --provider openrouter \
  --generator openai/gpt-oss-120b:nitro \
  --reflector openai/gpt-oss-120b:nitro \
  --curator openai/gpt-oss-120b:nitro \
  --config-slug openrouter-gpt-oss-120b \
  --checkpoint-enabled \
  --stop-after-stage adapt

runners/ace/run_experiments.sh appworld_full_eval \
  --resume-from results/ace-appworld/full/openrouter-gpt-oss-120b/full_seed-42_YYYYMMDD_HHMMSS
```

Stage names:

- FiNER: `baseline-eval`, `train`, `final-eval`
- AppWorld full runs: `adapt`, `eval-normal`, `eval-challenge`

AppWorld full-run v1 resume is serial. If you explicitly pass `--test-workers > 1`
to `appworld_full_eval`, the orchestrator fails fast.

## 4) What gets executed

- The script calls task-specific run modules:
  - `python -m eval.finance.run ...`
- `appworld_subset` and `appworld_adaptation` run through the vendored `ace-appworld` package:
  - `appworld run ... --root projects/ace-appworld --override ...`
- `appworld_full_eval` runs through the staged wrapper:
  - `python runners/ace/run_appworld_full.py ...`
- For subset presets, it passes ACE slicing flags with:
  - `--sample_config_path projects/ace/eval/finance/data/sample_config.json`
  - `--train_limit`, `--val_limit`, and `--test_limit`

## 5) Output locations

By default, outputs go to:

- `results/`
- AppWorld subset/adaptation presets write canonical AppWorld outputs directly under the selected
  `results/ace-appworld/...` path.
- AppWorld full runs write a single run directory under `results/ace-appworld/...` with
  stage-local artifacts under `stages/` and compatibility summaries under `summary/`
  and `evaluations/`.

FiNER runs create a canonical run folder such as `offline_seed-42_YYYYMMDD_HHMMSS` containing:

- `run_config.json`
- `result_path.json`
- `run_state.json`
- `sessions.jsonl`
- `final_results.json`
- `detailed_llm_logs/`
- `detailed_llm_logs/problematic_requests/` for empty or malformed provider responses
- `telemetry/` (if telemetry enabled)
- plus mode-specific artifacts like intermediate playbooks and test result JSON files.

AppWorld full runs add:

- `run_state.json`
- `sessions.jsonl`
- `stages/adapt/`, `stages/eval-normal/`, `stages/eval-challenge/`
- `summary/run_summary.json`

Override output root with:

```bash
--save-path /your/path
```

## 6) Dry-run mode

To print commands without executing:

```bash
runners/ace/run_experiments.sh finer_subset --dry-run
```
