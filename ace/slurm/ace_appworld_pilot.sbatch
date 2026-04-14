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

if [ -n "${MAMBA_ENV:-}" ]; then
  mamba activate "${MAMBA_ENV}"
fi

: "${API_PROVIDER:=openai}"
: "${GENERATOR_MODEL:=gpt-oss:20b}"
: "${REFLECTOR_MODEL:=gpt-oss:20b}"
: "${CURATOR_MODEL:=gpt-oss:20b}"
: "${SAVE_PATH:=./results}"
: "${TASK_NAME:=appworld}"
: "${CONFIG_NAME:=pilot}"
: "${SEED:=42}"
: "${APPWORLD_ROOT:=../ace-appworld}"

python -m eval.appworld.run \
  --task_name "${TASK_NAME}" \
  --mode offline \
  --dataset_name train \
  --max_agent_steps 20 \
  --api_provider "${API_PROVIDER}" \
  --generator_model "${GENERATOR_MODEL}" \
  --reflector_model "${REFLECTOR_MODEL}" \
  --curator_model "${CURATOR_MODEL}" \
  --json_mode \
  --telemetry_enabled \
  --telemetry_metrics_interval_seconds 15 \
  --config_name "${CONFIG_NAME}" \
  --seed "${SEED}" \
  --appworld_root "${APPWORLD_ROOT}" \
  --save_path "${SAVE_PATH}"
