#!/bin/bash --login
#SBATCH --job-name=ace_finer_smoke
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --qos=normal
#SBATCH --time=00:30:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16GB
#SBATCH --gres=gpu:p100:1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
: "${ACE_ROOT:=${REPO_ROOT}/projects/ace}"
: "${APPWORLD_ROOT:=${REPO_ROOT}/projects/ace-appworld}"
: "${SAVE_PATH:=${REPO_ROOT}/results}"

if [ -n "${MAMBA_ENV:-}" ]; then
  mamba activate "${MAMBA_ENV}"
fi

: "${API_PROVIDER:=openrouter}"
: "${GENERATOR_MODEL:=openai/gpt-oss-120b:nitro}"
: "${REFLECTOR_MODEL:=openai/gpt-oss-120b:nitro}"
: "${CURATOR_MODEL:=openai/gpt-oss-120b:nitro}"
: "${TASK_NAME:=finer}"
: "${CONFIG_NAME:=ace_all_openrouter_gptoss120b}"
: "${SEED:=42}"

cd "${ACE_ROOT}"

python -m eval.finance.run \
  --task_name "${TASK_NAME}" \
  --mode offline \
  --api_provider "${API_PROVIDER}" \
  --generator_model "${GENERATOR_MODEL}" \
  --reflector_model "${REFLECTOR_MODEL}" \
  --curator_model "${CURATOR_MODEL}" \
  --num_epochs 1 \
  --eval_steps 10 \
  --save_steps 10 \
  --telemetry_enabled \
  --telemetry_metrics_interval_seconds 5 \
  --config_name "${CONFIG_NAME}" \
  --seed "${SEED}" \
  --save_path "${SAVE_PATH}"
