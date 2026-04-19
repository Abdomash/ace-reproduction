# Runners

This directory contains operational entrypoints for experiments.

- `ace/run_experiments.sh`: unified local ACE runner for FiNER, Formula, and AppWorld presets.
- `ace/setup_appworld.sh`: pinned AppWorld setup helper.
- `ace/subset/`: OpenRouter FiNER subset launchers.
- `ace/slurm/`: SLURM jobs for cluster runs.
- `ace-appworld/configs/`: AppWorld experiment configs added for this reproduction.

## Environment

Provider keys are read from the environment. Subset scripts load the repository `.env` file before invoking the unified runner.

Keep real secrets in the repository root `.env`; it is ignored by Git. The example `.env.example` files inside `projects/` belong to their upstream projects or MAESTRO examples and are documented in `context/ENVIRONMENT.md`.

Common variables:

- `ACE_ROOT`: defaults to `<repo>/projects/ace`.
- `APPWORLD_ROOT`: defaults to `<repo>/projects/ace-appworld`.
- `RESULTS_ROOT`: defaults to `<repo>/results`.
- `RUN_TYPE`: defaults to `subset` or `full` from the preset.
- `CONFIG_SLUG`: explicit result config identity.
- `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `TOGETHER_API_KEY`, `SAMBANOVA_API_KEY`: provider credentials.

## Examples

```bash
runners/ace/run_experiments.sh finer_subset --dry-run
runners/ace/run_experiments.sh appworld_subset --dry-run
runners/ace/subset/run-finar-gptoss20b-subset.sh
```
