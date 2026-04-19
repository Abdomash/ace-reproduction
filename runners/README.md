# Runners

This directory contains operational entrypoints for experiments.

- `ace/run_experiments.sh`: unified local ACE runner for FiNER and Formula, plus AppWorld presets that launch through `projects/ace-appworld`.
- `ace/setup_appworld.sh`: AppWorld setup helper for the vendored source tree.
- `ace/subset/`: OpenRouter subset launchers with model-slug based wrappers.
- `ace/slurm/`: SLURM jobs for cluster runs.
- `ace-appworld/configs/`: AppWorld experiment configs added for this reproduction.

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
runners/ace/run_experiments.sh finer_subset --dry-run
runners/ace/run_experiments.sh appworld_subset --dry-run
runners/ace/subset/run-finar-subset.sh minimax/minimax-m2.7
runners/ace/subset/run-finar-subset.sh openai/gpt-oss-20b:nitro --config-name ace_all_gptoss20b_subset
runners/ace/subset/run-appworld-subset.sh openai/gpt-oss-120b:nitro --appworld-max-steps 10
```

AppWorld presets use `appworld run` from the vendored `ace-appworld` package. Outputs are written directly into the configured `results/ace-appworld/...` directory.

If AppWorld dependencies are missing or the local virtualenv was moved, rebuild the documented AppWorld environment:

```bash
runners/ace/setup_appworld.sh
```
