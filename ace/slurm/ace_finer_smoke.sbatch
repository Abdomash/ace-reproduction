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

if [ -n "${MAMBA_ENV:-}" ]; then
  mamba activate "${MAMBA_ENV}"
fi

: "${API_PROVIDER:=openai}"
: "${GENERATOR_MODEL:=gpt-oss:20b}"
: "${REFLECTOR_MODEL:=gpt-oss:20b}"
: "${CURATOR_MODEL:=gpt-oss:20b}"
: "${SAVE_PATH:=./results}"
: "${TASK_NAME:=finer}"
: "${CONFIG_NAME:=all_gptoss20b}"
: "${SEED:=42}"

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
