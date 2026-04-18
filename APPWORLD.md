# ACE on AppWorld Setup

This file documents the setup needed after cloning this repository to run the
vendored ACE AppWorld benchmark code with MAESTRO observability.

The important point: do not clone `ace-agent/ace-appworld` separately and do
not install `appworld` from PyPI for these experiments. This repository already
contains a patched local copy at `ace-appworld/`.

## Repository Layout

- `ace-appworld/`: vendored copy of `ace-agent/ace-appworld`, based on upstream
  commit `748a9dc8908464c7243696988534a9933932216b`, with local MAESTRO
  instrumentation patches applied.
- `maestro/`: local MAESTRO source tree. The AppWorld telemetry shim imports
  helpers from `maestro/src` when `ace-appworld/` is kept next to `maestro/`.
- `ace/`: the separate ACE reproduction code used for the other benchmarks.
  The AppWorld benchmark described here runs through `ace-appworld`, not through
  `ace/eval/appworld`.

## System Prerequisites

Use Linux or macOS with:

- Python 3.11. The verified local environment used Python `3.11.15`.
- Git LFS.
- A normal build toolchain for Python packages with native wheels or extensions.

On Ubuntu-like systems:

```bash
sudo apt-get update
sudo apt-get install -y git-lfs python3.11 python3.11-venv build-essential
git lfs install
```

If you use conda instead of `venv`, create a Python 3.11 environment and then
run the same `pip` commands below from inside that environment.

## After Cloning This Repository

From the repository root:

```bash
cd /path/to/ace-reproduction
git lfs install
git lfs pull
```

The LFS step matters because AppWorld source bundles are stored under:

- `ace-appworld/src/appworld/.source/*.bundle`
- `ace-appworld/generate/.source/*.bundle`

If those files contain only Git LFS pointer text, `appworld install --repo` will
not be able to unpack the app/test sources correctly.

## Create the AppWorld Environment

Create and activate a Python 3.11 environment inside the vendored AppWorld copy:

```bash
cd /path/to/ace-reproduction/ace-appworld
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

Install both AppWorld and its experiment package from the local source tree:

```bash
pip install -e .
pip install -e "experiments[simplified]"
```

The `experiments[simplified]` extra installs the ACE experiment dependencies,
including the OpenTelemetry packages required by the MAESTRO instrumentation.

The locally verified key package versions were:

- `appworld==0.1.4.dev0`
- `appworld-experiments==0.1.0.dev0`
- `litellm==1.83.9`
- `openai==2.24.0`
- `httpx==0.28.1`
- `opentelemetry-api==1.41.0`
- `opentelemetry-sdk==1.41.0`
- `jsonnet==0.21.0`

`pip check` currently reports dependency conflicts because the experiment stack
pulls newer `openai` and `httpx` versions than the base AppWorld package asks
for. The verified test suite still passes with the versions above.

## Unpack AppWorld Sources and Data

Run the AppWorld repo install step and download benchmark data:

```bash
export APPWORLD_PROJECT_PATH="$(pwd)"
appworld install --repo
appworld download data
```

`appworld install --repo` unpacks source bundles into ignored local directories
such as `src/appworld/apps/`, `tests/package/apps/`, `generate/data/`, and
`generate/tasks/task_generators/`. These generated/unpacked directories should
not be committed.

## Required Environment Variables

Set `APPWORLD_PROJECT_PATH` every time before running experiment configs:

```bash
cd /path/to/ace-reproduction/ace-appworld
source .venv/bin/activate
export APPWORLD_PROJECT_PATH="$(pwd)"
```

The checked-in experiment configs default to DeepSeek-V3.1 through SambaNova, so
the default full runs require:

```bash
export SAMBANOVA_API_KEY="..."
```

If you edit `experiments/configs/*.jsonnet` to use another LiteLLM provider,
export the matching key instead, for example:

```bash
export OPENAI_API_KEY="..."
export TOGETHER_API_KEY="..."
```

## MAESTRO Telemetry Controls

Telemetry is enabled by default. It writes JSONL traces and metrics under:

```text
ace-appworld/experiments/outputs/<experiment_name>/telemetry/
```

Useful controls:

```bash
# Disable AppWorld MAESTRO telemetry for a run.
export APPWORLD_MAESTRO_TELEMETRY=0

# Enable it explicitly.
export APPWORLD_MAESTRO_TELEMETRY=1

# Secondary global default used if APPWORLD_MAESTRO_TELEMETRY is unset.
export MAESTRO_TELEMETRY_ENABLED=1

# Metrics sampling interval. Default is 15 seconds.
export APPWORLD_MAESTRO_METRICS_INTERVAL_SECONDS=15

# Optional resource attribute in telemetry output.
export DEPLOYMENT_ENVIRONMENT=local
```

Telemetry imports MAESTRO helpers from the local sibling tree:

```text
/path/to/ace-reproduction/maestro/src
```

Keep `ace-appworld/` and `maestro/` in the same repository layout. If you move
`ace-appworld/` elsewhere, either move `maestro/` next to it or set
`PYTHONPATH` to include the MAESTRO source directory before running experiments.

## Verify the Installation

Run both official verification commands:

```bash
cd /path/to/ace-reproduction/ace-appworld
source .venv/bin/activate
export APPWORLD_PROJECT_PATH="$(pwd)"

appworld verify tasks --root .
appworld verify tests --root .
```

The local verified results were:

- `appworld verify tasks`: `147/147` tasks passed.
- `appworld verify tests`: `1553 passed` for app tests and `139 passed` for
  package tests.

You can also run a no-LLM smoke test that exercises the AppWorld runner and
telemetry setup without spending API calls:

```bash
APPWORLD_MAESTRO_TELEMETRY=1 \
APPWORLD_MAESTRO_METRICS_INTERVAL_SECONDS=1 \
appworld run ACE_online_no_GT \
  --task-id 50e1ac9_1 \
  --override '{"config":{"dataset":"dev","agent":{"max_steps":0,"logger_config":{"verbose":false,"color":false}}}}' \
  --root .
```

Expected telemetry artifacts:

```text
experiments/outputs/ACE_online_no_GT/telemetry/
  metadata_ACE_online_no_GT_50e1ac9_1.json
  run_ACE_online_no_GT_50e1ac9_1.otel.jsonl
  ace-appworld_ACE_online_no_GT_50e1ac9_1.metrics.jsonl
```

## Running Experiments

General form:

```bash
appworld run <CONFIG_NAME> --root .
```

Available ACE configs:

```bash
appworld run ACE_online_no_GT --root .
appworld run ACE_offline_no_GT_adaptation --root .
appworld run ACE_offline_no_GT_evaluation --root .
appworld run ACE_offline_with_GT_adaptation --root .
appworld run ACE_offline_with_GT_evaluation --root .
```

For a single task:

```bash
appworld run ACE_online_no_GT --task-id 50e1ac9_1 --root .
```

For a small subset:

```bash
appworld run ACE_online_no_GT \
  --override '{"config":{"dataset":"dev","sample_size":3}}' \
  --root .
```

For multiprocessing, run one process per index:

```bash
appworld run ACE_online_no_GT --num-processes 4 --process-index 0 --root .
appworld run ACE_online_no_GT --num-processes 4 --process-index 1 --root .
appworld run ACE_online_no_GT --num-processes 4 --process-index 2 --root .
appworld run ACE_online_no_GT --num-processes 4 --process-index 3 --root .
```

Each process writes a separate telemetry run id with the process index included.

## Offline Playbook Notes

The offline no-GT configs use this trained playbook path:

```text
experiments/playbooks/appworld_offline_trained_no_gt_playbook_deepseek_3_1.txt
```

That file is produced by `ACE_offline_no_GT_adaptation`. If you want to run
offline no-GT evaluation using the shipped trained playbook instead, override
the path to:

```text
experiments/playbooks/appworld_offline_trained_no_gt_playbook.txt
```

Example:

```bash
appworld run ACE_offline_no_GT_evaluation \
  --override '{"config":{"agent":{"trained_playbook_file_path":"'"$APPWORLD_PROJECT_PATH"'/experiments/playbooks/appworld_offline_trained_no_gt_playbook.txt"}}}' \
  --root .
```

## Evaluating Results

After a run writes outputs, aggregate metrics with:

```bash
appworld evaluate ACE_online_no_GT test_normal --root .
appworld evaluate ACE_online_no_GT test_challenge --root .
```

Replace `ACE_online_no_GT` with the experiment config you ran. AppWorld reports
Task Goal Completion and Scenario Goal Completion.

## What Should Not Be Committed

These paths are local runtime/install artifacts and should remain ignored:

- `ace-appworld/.venv/`
- `ace-appworld/data/`
- `ace-appworld/experiments/outputs/`
- `ace-appworld/experiments/appworld_experiments.egg-info/`
- `ace-appworld/src/appworld/apps/`
- `ace-appworld/tests/package/apps/`
- `ace-appworld/generate/data/`
- `ace-appworld/generate/tasks/task_generators/`
- any `__pycache__/` or `.pytest_cache/` directories

## Troubleshooting

If `appworld install --repo` fails with bundle or archive errors, run:

```bash
git lfs pull
git lfs checkout
```

If configs fail with a Jsonnet `APPWORLD_PROJECT_PATH` error, re-export:

```bash
export APPWORLD_PROJECT_PATH="$(pwd)"
```

If telemetry files are missing, check:

```bash
echo "$APPWORLD_MAESTRO_TELEMETRY"
python - <<'PY'
from appworld_experiments.code.ace.telemetry import telemetry_enabled_by_default
print(telemetry_enabled_by_default())
PY
```

If telemetry initialization reports a MAESTRO import error, verify that this
path exists:

```bash
ls /path/to/ace-reproduction/maestro/src/maestro/telemetry_helpers
```

If a real experiment appears to hang, remember that the default configs allow up
to 40 ReAct steps per task and up to 50 LLM retries per call. Start with
`--task-id` or `sample_size` before launching a full split.
