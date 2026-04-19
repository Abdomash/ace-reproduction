# Unified Experiment Runner

This document explains how to run quick subsets or broader runs using:

- `scripts/run_experiments.sh`

It supports FiNER subsets, Formula subsets, AppWorld subsets, and combined full-style runs.
The runner is paper-faithful by default: standard chat-completion calls,
`max_tokens=4096`, provider JSON mode off, and no OpenRouter reasoning controls.

## 1) Prerequisites

- You are in the ACE root directory: `ace/`
- Python dependencies are installed (for example via `uv sync`)
- API key for your selected provider is exported:
  - `OPENROUTER_API_KEY` for `--provider openrouter`
  - `OPENAI_API_KEY` for `--provider openai`
  - `TOGETHER_API_KEY` for `--provider together`
  - `SAMBANOVA_API_KEY` for `--provider sambanova`

For AppWorld, make sure `ace-appworld` is installed and prepared (pinned commit recommended):

```bash
APPWORLD_COMMIT=<pinned-sha> ./scripts/setup_appworld.sh
```

## 2) Presets

Available presets:

- `finer_subset`: creates/generated subset config (60 train, 40 val, 80 test) and runs FiNER
- `finer_full`: runs FiNER using default full sample config
- `formula_subset`: creates/generated subset config for Formula and runs it
- `appworld_subset`: runs AppWorld `eval_only` on `dev`
- `appworld_full_eval`: runs AppWorld `eval_only` on `test_normal` and `test_challenge`
- `all_full`: runs `finer_full` then `appworld_full_eval`

## 3) Quick examples

### A) FiNER subset (section-sized style)

```bash
./scripts/run_experiments.sh finer_subset \
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
./scripts/run_experiments.sh appworld_subset \
  --provider openrouter \
  --generator openai/gpt-oss-120b:nitro \
  --reflector openai/gpt-oss-120b:nitro \
  --curator openai/gpt-oss-120b:nitro \
  --appworld-root ../ace-appworld \
  --appworld-max-steps 20 \
  --config-name appworld_subset_gptoss20b \
  --seed 42
```

### C) Combined full-style run

```bash
./scripts/run_experiments.sh all_full \
  --provider openrouter \
  --generator minimax/minimax-m2.7 \
  --reflector minimax/minimax-m2.7 \
  --curator minimax/minimax-m2.7 \
  --config-name ace_all_openrouter_minimax_m27 \
  --seed 42
```

## 4) What gets executed

- The script calls task-specific run modules:
  - `python -m eval.finance.run ...`
  - `python -m eval.appworld.run ...`
- For subset presets, it first creates reduced JSONL files under:
  - `eval/finance/data/generated/`
- Then it uses a generated sample config JSON through:
  - `--sample_config_path ...`

## 5) Output locations

By default, outputs go to:

- `./results`

Each run creates a canonical run folder (`ace_<task>_<mode>_<config>_<seed>_<timestamp>`) containing:

- `run_config.json`
- `final_results.json`
- `detailed_llm_logs/`
- `detailed_llm_logs/problematic_requests/` for empty or malformed provider responses
- `telemetry/` (if telemetry enabled)
- plus mode-specific artifacts like intermediate playbooks and test result JSON files.

Override output root with:

```bash
--save-path /your/path
```

## 6) Dry-run mode

To print commands without executing:

```bash
./scripts/run_experiments.sh finer_subset --dry-run
```
