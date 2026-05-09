#!/bin/bash --login
# Representative FiNER subset launch via `python -m runner launch`.
# Override resources at submission time when needed, for example:
#   sbatch --gres=gpu:v100:1 --time=08:00:00 runners/ace/slurm/ace_repr_finer_launch.sbatch
#
# Common env overrides:
#   MAMBA_ENV=<env>
#   CONDA_ENV_NAME=<env>
#   VENV_PATH=<venv>
#   SAMPLES=finer_repr_a,finer_repr_b
#   CONFIGS=all_cheap,expensive_reflector
#   SEED=42
#   CHEAP_MODEL=openai/gpt-oss-120b
#   EXPENSIVE_MODEL=deepseek/deepseek-v3.2
#   CHEAP_PROVIDER=openrouter
#   EXPENSIVE_PROVIDER=openrouter
#   TELEMETRY=1
#   TEST_WORKERS=1
#   MAX_TOKENS=4096
#   CHECKPOINT_ENABLED=1
#   STOP_AFTER_STAGE=train

#SBATCH --job-name=ace_repr_finer
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --qos=normal
#SBATCH --time=04:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16GB
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
: "${SAMPLES:=finer_repr_a}"
: "${CONFIGS:=all_cheap}"
: "${SEED:=42}"
: "${CHEAP_MODEL:=openai/gpt-oss-120b}"
: "${EXPENSIVE_MODEL:=deepseek/deepseek-v3.2}"
: "${CHEAP_PROVIDER:=openrouter}"
: "${EXPENSIVE_PROVIDER:=openrouter}"
: "${TELEMETRY:=1}"
: "${TEST_WORKERS:=1}"
: "${MAX_TOKENS:=4096}"
: "${EVAL_STEPS:=100}"
: "${KEEP_GOING:=0}"
: "${CHECKPOINT_ENABLED:=1}"
: "${STOP_AFTER_STAGE:=}"
: "${STOP_AFTER_STEP:=}"

append_csv_flags() {
  local -n argv_ref="$1"
  local flag="$2"
  local csv="$3"
  local item trimmed
  IFS=',' read -r -a items <<< "${csv}"
  for item in "${items[@]}"; do
    trimmed="$(printf '%s' "${item}" | xargs)"
    if [[ -n "${trimmed}" ]]; then
      argv_ref+=("${flag}" "${trimmed}")
    fi
  done
}

cd "${REPO_ROOT}"

cmd=(
  "${PYTHON_BIN}" -m runner launch
  --campaign "${CAMPAIGN}"
  --benchmark finer
  --seed "${SEED}"
  --tier "cheap=${CHEAP_MODEL}"
  --tier "expensive=${EXPENSIVE_MODEL}"
  --tier-provider "cheap=${CHEAP_PROVIDER}"
  --tier-provider "expensive=${EXPENSIVE_PROVIDER}"
  --telemetry "${TELEMETRY}"
  --test-workers "${TEST_WORKERS}"
  --max-tokens "${MAX_TOKENS}"
  --eval-steps "${EVAL_STEPS}"
)

append_csv_flags cmd --sample "${SAMPLES}"
append_csv_flags cmd --config "${CONFIGS}"

if [[ "${KEEP_GOING}" == "1" ]]; then
  cmd+=(--keep-going)
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

"${cmd[@]}" "$@"
