# Environment Files

This repo uses one active experiment environment file at the repository root:

```text
.env
```

It is ignored by Git and should contain local secrets only. The ACE smoke scripts in `runners/ace/smoke/` load this file before calling `runners/ace/run_experiments.sh`.

## Root `.env`

Use the root `.env` for reproduction runs launched from this repository.

Common keys:

```bash
OPENROUTER_API_KEY=...
OPENAI_API_KEY=...
TOGETHER_API_KEY=...
SAMBANOVA_API_KEY=...
```

Only fill in the provider keys you need. Current smoke scripts require `OPENROUTER_API_KEY` because they run OpenRouter models.

Optional runner overrides:

```bash
ACE_ROOT=/path/to/ace
APPWORLD_ROOT=/path/to/ace-appworld
SAVE_PATH=/path/to/results
TEST_WORKERS=20
MAX_TOKENS=4096
TELEMETRY=1
TELEMETRY_INTERVAL=5
MAMBA_ENV=ace-repr-runner
```

Normally these overrides are not needed; defaults point at `projects/ace`, `projects/ace-appworld`, and `results`.

## One-Time Cluster Setup

For new SLURM hosts, the representative runner now has a one-time bootstrap helper:

```bash
runners/ace/setup_cluster_env.sh
```

Default behavior:

- creates or reuses a conda-compatible env named `ace-repr-runner`
- installs editable dependencies for:
  - `projects/maestro[telemetry]`
  - `projects/ace`
  - `projects/ace-appworld`
  - `projects/ace-appworld/experiments[simplified]`
- runs `git lfs install` and `git lfs pull`
- runs `appworld install --repo`
- downloads AppWorld data
- verifies AppWorld tests and tasks

Useful overrides:

```bash
ENV_NAME=my-ace-env runners/ace/setup_cluster_env.sh
APPWORLD_VERIFY=0 runners/ace/setup_cluster_env.sh
APPWORLD_DOWNLOAD_DATA=0 runners/ace/setup_cluster_env.sh
```

The representative SLURM scripts can then activate the environment with either:

```bash
MAMBA_ENV=ace-repr-runner
CONDA_ENV_NAME=ace-repr-runner
```

They also auto-load provider keys from the repository root `.env` when present.

## Project Example Files

- `projects/ace/.env.example`: upstream ACE provider-key template. For this restructured repo, copy needed values into the root `.env` instead of creating a separate ACE `.env`.
- `projects/maestro/examples/adk/brand-search-optimization/env.example`: MAESTRO example-only Google/Vertex/BigQuery settings. Not needed for ACE reproduction runs.
- `projects/maestro/examples/adk/content-creation/local_deployment/.env.example`: MAESTRO content-creation local deployment ports and provider settings. Not needed for ACE reproduction runs.
- `projects/maestro/examples/adk/content-creation/src/agents/shared/.env.example`: MAESTRO content-creation shared Google API key template. Not needed for ACE reproduction runs.
- `projects/maestro/examples/adk/image-scoring/.env.example`: MAESTRO image-scoring Google/Vertex and storage settings. Not needed for ACE reproduction runs.
- `projects/maestro/examples/adk/marketing-agency/.env.example`: MAESTRO marketing-agency Google/Vertex deployment settings. Not needed for ACE reproduction runs.

## AppWorld Variables

`runners/ace/setup_appworld.sh` exports `APPWORLD_PROJECT_PATH` during setup. For manual AppWorld commands, set:

```bash
export APPWORLD_PROJECT_PATH=/path/to/ace-reproduction/projects/ace-appworld
```

The AppWorld configs under `runners/ace-appworld/configs/` may also require the same provider keys as the root `.env`, depending on which model/provider config you run.
