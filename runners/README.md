# Runners

This directory contains operational entrypoints for experiments.

- `python -m runner ...`: canonical launcher for the new representative ACE subset campaign. The implementation lives inside the existing `runners/` package, and `runner.py` is just a thin compatibility entrypoint.
- `ace/run_experiments.sh`: unified local ACE runner for FiNER and Formula, plus AppWorld presets. `appworld_full_eval` now uses a single-run staged orchestrator; `appworld_subset` and `appworld_adaptation` continue to launch through `projects/ace-appworld`.
- `ace/setup_appworld.sh`: AppWorld setup helper for the vendored source tree.
- `ace/subset/`: OpenRouter subset launchers with model-slug based wrappers.
- `ace/slurm/`: SLURM jobs for cluster runs.
- `ace-appworld/configs/`: AppWorld experiment configs added for this reproduction.

## Representative Campaign

The checked-in representative pre-reproduction campaign lives under [runners/campaigns/ace_repr_v1](/home/abdo/ace-reproduction/runners/campaigns/ace_repr_v1/campaign.json).

- Purpose: run larger-than-current but still smaller-than-full FiNER/AppWorld subsets that preserve benchmark structure before spending on later paper-faithful full runs.
- Samples:
  - `finer_repr_a`
  - `finer_repr_b`
  - `appworld_test_normal_repr`
  - `appworld_test_challenge_repr`
- Configs:
  - `all_cheap`
  - `all_expensive`
  - `expensive_generator`
  - `expensive_reflector`
  - `expensive_curator`
- Default tiers:
  - `cheap = openrouter / openai/gpt-oss-120b`
  - `expensive = openrouter / deepseek/deepseek-v3.2`
- Historical analysis exception:
  - `openai/gpt-oss-120b:nitro` is classified as `expensive`, not `cheap`
  - DeepSeek and MiniMax are also classified as `expensive`

## Environment

Provider keys are read from the environment. Subset scripts load the repository `.env` file before invoking the unified runner.

Keep real secrets in the repository root `.env`; it is ignored by Git. The example `.env.example` files inside `projects/` belong to their upstream projects or MAESTRO examples and are documented in `context/ENVIRONMENT.md`.

Common variables:

- `ACE_ROOT`: defaults to `<repo>/projects/ace`.
- `APPWORLD_ROOT`: defaults to `<repo>/projects/ace-appworld`.
- `APPWORLD_BIN`: optional path to the `appworld` command from a prepared Python 3.11 AppWorld environment.
- `RESULTS_ROOT`: defaults to `<repo>/results`.
- `RUN_TYPE`: defaults to `subset` or `full` from the preset.
- `CONFIG_SLUG`: explicit result config identity.
- `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `TOGETHER_API_KEY`, `SAMBANOVA_API_KEY`: provider credentials.

## Examples

```bash
python -m runner samples
python -m runner configs
python -m runner launch --sample finer_repr_a --config all_cheap --dry-run
python -m runner launch --sample appworld_test_normal_repr --config expensive_reflector --dry-run
python -m runner launch --sample finer_repr_a --sample appworld_test_challenge_repr --config all_cheap --config all_expensive
python -m runner resume --benchmark finer --sample finer_repr_a --config all_cheap --latest

runners/ace/run_experiments.sh finer_subset --dry-run
runners/ace/run_experiments.sh finer_full --checkpoint-enabled --stop-after-stage train
runners/ace/run_experiments.sh finer_full --resume-from results/ace-finer/full/openrouter-gpt-oss-120b/offline_seed-42_YYYYMMDD_HHMMSS
runners/ace/run_experiments.sh appworld_subset --dry-run
runners/ace/run_experiments.sh appworld_full_eval --checkpoint-enabled --stop-after-stage adapt
runners/ace/run_experiments.sh appworld_full_eval --resume-from results/ace-appworld/full/openrouter-gpt-oss-120b/full_seed-42_YYYYMMDD_HHMMSS
runners/ace/subset/run-finar-subset.sh minimax/minimax-m2.7
runners/ace/subset/run-finar-subset.sh openai/gpt-oss-20b --config-name ace_all_gptoss20b_subset
runners/ace/subset/run-appworld-subset.sh openai/gpt-oss-120b --appworld-max-steps 10
```

## Resumable Interfaces

`python -m runner` exposes launch/list/resume controls for the representative matrix, while `run_experiments.sh` continues to cover older preset-style flows.

The representative runner writes campaign/sample/config/tier metadata into new runs:

- `campaign_id`
- `sample_id`
- `sample_kind`
- `config_id`
- `tier_models`
- `resolved_models`
- `sample_manifest_path`

`run_experiments.sh` continues to expose staged stop/resume controls for existing FiNER runs and for the single-run AppWorld full workflow:

- `--resume-from <run_dir>`
- `--checkpoint-enabled`
- `--stop-after-stage <stage>`
- `--stop-after-step <n>` for FiNER
- `--stop-after-task <n>` and `--checkpoint-every-task <n>` for `appworld_full_eval`

FiNER stage names:

- `baseline-eval`
- `train`
- `final-eval`

AppWorld full-run stage names:

- `adapt`
- `eval-normal`
- `eval-challenge`

`appworld_full_eval` now creates one run directory and executes `adapt -> eval-normal -> eval-challenge` inside it. Raw stage artifacts live under `stages/`, while top-level `summary/` and `evaluations/` remain the compatibility surface consumed by analysis.

AppWorld v1 full-run resume is intentionally serial. If you explicitly pass `--test-workers > 1` to `appworld_full_eval`, the orchestrator fails fast instead of running nondeterministic multi-process resume logic.

## Lifecycle Artifacts

New resumable runs write:

- `run_state.json` with lifecycle state such as `status`, `resume_count`, `current_stage`, `last_completed_stage`, and `active_runtime_seconds`
- `sessions.jsonl` with one append-only row per invocation

FiNER runs also project lifecycle fields into `result_path.json`, `run_group.json`, and `final_results.json`. AppWorld full runs export the same fields into `summary/run_summary.json`.

AppWorld subset/adaptation presets still use `appworld run` from the vendored `ace-appworld` package. Outputs are written directly into the configured `results/ace-appworld/...` directory. `appworld_full_eval` now routes through `runners/ace/run_appworld_full.py`.

If AppWorld dependencies are missing or the local virtualenv was moved, rebuild the documented AppWorld environment:

```bash
runners/ace/setup_appworld.sh
```
