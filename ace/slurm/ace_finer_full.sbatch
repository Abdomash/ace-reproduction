#!/bin/bash --login
#SBATCH --job-name=ace_finer_full
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --qos=normal
#SBATCH --time=12:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=40GB
#SBATCH --gres=gpu:v100:1

set -euo pipefail

if [ -n "${MAMBA_ENV:-}" ]; then
  mamba activate "${MAMBA_ENV}"
fi

: "${SAVE_PATH:=./results}"
: "${TASK_NAME:=finer}"

run_one() {
  local config_name="$1"
  local seed="$2"
  local api_provider="$3"
  local generator_model="$4"
  local reflector_model="$5"
  local curator_model="$6"

  python -m eval.finance.run \
    --task_name "${TASK_NAME}" \
    --mode offline \
    --api_provider "${api_provider}" \
    --generator_model "${generator_model}" \
    --reflector_model "${reflector_model}" \
    --curator_model "${curator_model}" \
    --num_epochs 1 \
    --json_mode \
    --telemetry_enabled \
    --telemetry_metrics_interval_seconds 5 \
    --config_name "${config_name}" \
    --seed "${seed}" \
    --save_path "${SAVE_PATH}"
}

for seed in 42 43 44; do
  run_one "all_gptoss20b" "${seed}" "openai" "gpt-oss:20b" "gpt-oss:20b" "gpt-oss:20b"
  run_one "all_minimax" "${seed}" "minimax" "MiniMax-M2.5" "MiniMax-M2.5" "MiniMax-M2.5"
  run_one "mixed_reflector_strong" "${seed}" "openai" "gpt-oss:20b" "MiniMax-M2.5" "gpt-oss:20b"
done
