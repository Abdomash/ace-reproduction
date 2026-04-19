#!/bin/bash --login
#SBATCH --job-name=ace_appworld_smoke
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --qos=normal
#SBATCH --time=01:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16GB
#SBATCH --gres=gpu:p100:1

set -euo pipefail

if [ -n "${MAMBA_ENV:-}" ]; then
  mamba activate "${MAMBA_ENV}"
fi

: "${API_PROVIDER:=openrouter}"
: "${GENERATOR_MODEL:=openai/gpt-oss-120b:nitro}"
: "${REFLECTOR_MODEL:=openai/gpt-oss-120b:nitro}"
: "${CURATOR_MODEL:=openai/gpt-oss-120b:nitro}"
: "${SAVE_PATH:=./results}"
: "${TASK_NAME:=appworld}"
: "${CONFIG_NAME:=smoke}"
: "${SEED:=42}"
: "${APPWORLD_ROOT:=../ace-appworld}"

python -m eval.appworld.run \
  --task_name "${TASK_NAME}" \
  --mode eval_only \
  --dataset_name dev \
  --max_agent_steps 10 \
  --api_provider "${API_PROVIDER}" \
  --generator_model "${GENERATOR_MODEL}" \
  --reflector_model "${REFLECTOR_MODEL}" \
  --curator_model "${CURATOR_MODEL}" \
  --telemetry_enabled \
  --telemetry_metrics_interval_seconds 15 \
  --config_name "${CONFIG_NAME}" \
  --seed "${SEED}" \
  --appworld_root "${APPWORLD_ROOT}" \
  --save_path "${SAVE_PATH}"
