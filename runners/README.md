# Runners

This directory contains operational entrypoints for experiments.

- `python -m runner ...`: canonical launcher for the smoke and representative ACE campaigns. The implementation lives inside the existing `runners/` package, and `runner.py` is just a thin compatibility entrypoint.
- `ace/run_experiments.sh`: unified local ACE runner for FiNER and Formula, plus AppWorld presets. `appworld_full_eval` now uses a single-run staged orchestrator; `appworld_subset` and `appworld_adaptation` continue to launch through `projects/ace-appworld`.
- `ace/setup_cluster_env.sh`: one-time conda/mamba bootstrap for SLURM hosts running the representative campaign.
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
  - `expensive = openrouter / deepseek/deepseek-v4-flash`
- Historical analysis exception:
  - `openai/gpt-oss-120b:nitro` is classified as `expensive`, not `cheap`
  - DeepSeek and MiniMax are also classified as `expensive`

## Smoke Campaign

The checked-in preflight smoke campaign lives under [runners/campaigns/ace_smoke_v1](/home/abdo/ace-reproduction/runners/campaigns/ace_smoke_v1/campaign.json). It is separate from `ace_repr_v1` and is intended to confirm the runner, provider wiring, output layout, and telemetry before launching real matrix cells.

- Samples:
  - `finer_smoke`: FiNER `train=5,val=5,test=5`, with `eval_steps=1`
  - `appworld_smoke`: one AppWorld train/adapt task and one `test_normal` eval task, with `appworld_max_steps=1`
- Configs and default tiers match the representative campaign so the same config names work.

Examples:

```bash
python -m runner samples --campaign ace_smoke_v1
python -m runner configs --campaign ace_smoke_v1
python -m runner launch --campaign ace_smoke_v1 --sample finer_smoke --config all_cheap --dry-run
python -m runner launch --campaign ace_smoke_v1 --sample appworld_smoke --config all_cheap --dry-run
python -m runner launch --campaign ace_smoke_v1 --sample finer_smoke --sample appworld_smoke --config all_cheap --keep-going
```

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
python -m runner samples --campaign ace_smoke_v1
python -m runner launch --campaign ace_smoke_v1 --sample finer_smoke --config all_cheap --dry-run
python -m runner launch --sample finer_repr_a --config all_cheap --dry-run
python -m runner launch --sample appworld_test_normal_repr --config expensive_reflector --dry-run
python -m runner launch --sample finer_repr_a --sample appworld_test_challenge_repr --config all_cheap --config all_expensive
python -m runner resume --benchmark finer --sample finer_repr_a --config all_cheap --latest

sbatch runners/ace/slurm/ace_repr_finer_launch.sbatch
SAMPLES=finer_repr_a,finer_repr_b CONFIGS=all_cheap,expensive_reflector sbatch runners/ace/slurm/ace_repr_finer_launch.sbatch
sbatch runners/ace/slurm/ace_repr_appworld_launch.sbatch
SAMPLES=appworld_test_normal_repr,appworld_test_challenge_repr CONFIGS=all_expensive sbatch runners/ace/slurm/ace_repr_appworld_launch.sbatch
BENCHMARK=appworld SAMPLE=appworld_test_normal_repr CONFIG=expensive_generator sbatch runners/ace/slurm/ace_repr_resume.sbatch

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

## SLURM

The representative campaign now has three cluster entrypoints under [runners/ace/slurm](/home/abdo/ace-reproduction/runners/ace/slurm):

- `ace_repr_finer_launch.sbatch`: launch one or more FiNER representative cells through `python -m runner launch`
- `ace_repr_appworld_launch.sbatch`: launch one or more AppWorld representative cells through `python -m runner launch`
- `ace_repr_resume.sbatch`: resume the latest matching representative run through `python -m runner resume`

These scripts follow the guidance in [context/runners/SLURM.md](/home/abdo/ace-reproduction/context/runners/SLURM.md):

- resource requests are defaults, and can be overridden with normal `sbatch` flags such as `--gres` and `--time`
- runtime configuration is passed with environment variables like `SAMPLES`, `CONFIGS`, `CHEAP_MODEL`, `EXPENSIVE_MODEL`, and `MAMBA_ENV`
- any extra CLI flags can still be appended after the script path and are forwarded to `python -m runner`
- checkpointing is enabled by default in these cluster entrypoints and can be disabled with `CHECKPOINT_ENABLED=0`
- the scripts automatically load provider keys from the repository root `.env` if it exists

One-time host preparation:

```bash
runners/ace/setup_cluster_env.sh
MAMBA_ENV=ace-repr-runner sbatch runners/ace/slurm/ace_repr_finer_launch.sbatch
```

If you use plain conda instead of mamba:

```bash
CONDA_ENV_NAME=ace-repr-runner sbatch runners/ace/slurm/ace_repr_finer_launch.sbatch
```

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
