#!/bin/bash --login
#SBATCH --job-name=ace_appworld_subset
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --qos=normal
#SBATCH --time=01:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16GB
#SBATCH --gres=gpu:p100:1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
: "${APPWORLD_ROOT:=${REPO_ROOT}/projects/ace-appworld}"
: "${RESULTS_ROOT:=${REPO_ROOT}/results}"

if [ -n "${MAMBA_ENV:-}" ]; then
  mamba activate "${MAMBA_ENV}"
fi

: "${API_PROVIDER:=openrouter}"
: "${GENERATOR_MODEL:=openai/gpt-oss-120b:nitro}"
: "${REFLECTOR_MODEL:=openai/gpt-oss-120b:nitro}"
: "${CURATOR_MODEL:=openai/gpt-oss-120b:nitro}"
: "${CONFIG_NAME:=subset}"
: "${CONFIG_SLUG:=openrouter-gpt-oss-120b}"
: "${SEED:=42}"
: "${SAVE_PATH:=${RESULTS_ROOT}/ace-appworld/subset/${CONFIG_SLUG}}"

"${REPO_ROOT}/runners/ace/run_experiments.sh" appworld_subset \
  --provider "${API_PROVIDER}" \
  --generator "${GENERATOR_MODEL}" \
  --reflector "${REFLECTOR_MODEL}" \
  --curator "${CURATOR_MODEL}" \
  --config-name "${CONFIG_NAME}" \
  --config-slug "${CONFIG_SLUG}" \
  --results-root "${RESULTS_ROOT}" \
  --run-type subset \
  --seed "${SEED}" \
  --appworld-root "${APPWORLD_ROOT}" \
  --appworld-max-steps 10 \
  --save-path "${SAVE_PATH}" \
  --telemetry 1 \
  --telemetry-interval 15
