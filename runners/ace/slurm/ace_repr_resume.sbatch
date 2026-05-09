#!/bin/bash --login
# Representative campaign resume via `python -m runner resume`.
# Override resources at submission time when needed, for example:
#   sbatch --gres=gpu:v100:1 --time=16:00:00 runners/ace/slurm/ace_repr_resume.sbatch
#
# Common env overrides:
#   MAMBA_ENV=<env>
#   CONDA_ENV_NAME=<env>
#   VENV_PATH=<venv>
#   BENCHMARK=finer|appworld
#   SAMPLE=finer_repr_a
#   CONFIG=all_cheap
#   CAMPAIGN=ace_repr_v1
#   LATEST=1
#   SEED_OVERRIDE=43
#   TELEMETRY=1
#   TEST_WORKERS=1
#   MAX_TOKENS=4096
#   APPWORLD_MAX_STEPS=30
#   CHECKPOINT_ENABLED=1
#   STOP_AFTER_STAGE=adapt
#   STOP_AFTER_STEP=200
#   STOP_AFTER_TASK=10

#SBATCH --job-name=ace_repr_resume
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --qos=normal
#SBATCH --time=16:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32GB
#SBATCH --gres=gpu:p100:1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/.env"
  set +a
fi

# shellcheck disable=SC1091
source "${REPO_ROOT}/runners/ace/activate_env.sh"

: "${CAMPAIGN:=ace_repr_v1}"
: "${BENCHMARK:=finer}"
: "${SAMPLE:=finer_repr_a}"
: "${CONFIG:=all_cheap}"
: "${LATEST:=1}"
: "${TELEMETRY:=1}"
: "${TEST_WORKERS:=1}"
: "${MAX_TOKENS:=4096}"
: "${EVAL_STEPS:=100}"
: "${APPWORLD_MAX_STEPS:=30}"
: "${CHECKPOINT_EVERY_TASK:=1}"
: "${CHECKPOINT_ENABLED:=1}"
: "${STOP_AFTER_STAGE:=}"
: "${STOP_AFTER_STEP:=}"
: "${STOP_AFTER_TASK:=}"
: "${SEED_OVERRIDE:=}"

cd "${REPO_ROOT}"

cmd=(
  "${PYTHON_BIN}" -m runner resume
  --campaign "${CAMPAIGN}"
  --benchmark "${BENCHMARK}"
  --sample "${SAMPLE}"
  --config "${CONFIG}"
  --telemetry "${TELEMETRY}"
  --test-workers "${TEST_WORKERS}"
  --max-tokens "${MAX_TOKENS}"
  --eval-steps "${EVAL_STEPS}"
  --appworld-max-steps "${APPWORLD_MAX_STEPS}"
  --checkpoint-every-task "${CHECKPOINT_EVERY_TASK}"
)

if [[ "${LATEST}" == "1" ]]; then
  cmd+=(--latest)
fi
if [[ "${CHECKPOINT_ENABLED}" == "1" ]]; then
  cmd+=(--checkpoint-enabled)
fi
if [[ -n "${STOP_AFTER_STAGE}" ]]; then
  cmd+=(--stop-after-stage "${STOP_AFTER_STAGE}")
fi
if [[ -n "${STOP_AFTER_STEP}" ]]; then
  cmd+=(--stop-after-step "${STOP_AFTER_STEP}")
fi
if [[ -n "${STOP_AFTER_TASK}" ]]; then
  cmd+=(--stop-after-task "${STOP_AFTER_TASK}")
fi
if [[ -n "${SEED_OVERRIDE}" ]]; then
  cmd+=(--seed "${SEED_OVERRIDE}")
fi

"${cmd[@]}" "$@"
