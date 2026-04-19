#!/bin/bash --login
#SBATCH --job-name=ace_appworld_pilot
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --qos=normal
#SBATCH --time=08:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32GB
#SBATCH --gres=gpu:v100:1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
: "${ACE_ROOT:=${REPO_ROOT}/projects/ace}"
: "${APPWORLD_ROOT:=${REPO_ROOT}/projects/ace-appworld}"
: "${RESULTS_ROOT:=${REPO_ROOT}/results}"

if [ -n "${MAMBA_ENV:-}" ]; then
  mamba activate "${MAMBA_ENV}"
fi

: "${API_PROVIDER:=openrouter}"
: "${GENERATOR_MODEL:=openai/gpt-oss-120b:nitro}"
: "${REFLECTOR_MODEL:=openai/gpt-oss-120b:nitro}"
: "${CURATOR_MODEL:=openai/gpt-oss-120b:nitro}"
: "${TASK_NAME:=appworld}"
: "${CONFIG_NAME:=pilot}"
: "${CONFIG_SLUG:=pilot}"
: "${SEED:=42}"
: "${SAVE_PATH:=${RESULTS_ROOT}/ace-appworld/debug/${CONFIG_SLUG}}"

cd "${ACE_ROOT}"

python -m eval.appworld.run \
  --task_name "${TASK_NAME}" \
  --mode offline \
  --dataset_name train \
  --max_agent_steps 20 \
  --api_provider "${API_PROVIDER}" \
  --generator_model "${GENERATOR_MODEL}" \
  --reflector_model "${REFLECTOR_MODEL}" \
  --curator_model "${CURATOR_MODEL}" \
  --telemetry_enabled \
  --telemetry_metrics_interval_seconds 15 \
  --config_name "${CONFIG_NAME}" \
  --benchmark ace-appworld \
  --run_type debug \
  --config_slug "${CONFIG_SLUG}" \
  --seed "${SEED}" \
  --appworld_root "${APPWORLD_ROOT}" \
  --save_path "${SAVE_PATH}"
