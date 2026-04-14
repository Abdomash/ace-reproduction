#!/bin/bash --login
#SBATCH --job-name=ace_appworld_full
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --qos=normal
#SBATCH --time=24:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=40GB
#SBATCH --gres=gpu:v100:1

set -euo pipefail

if [ -n "${MAMBA_ENV:-}" ]; then
  mamba activate "${MAMBA_ENV}"
fi

: "${SAVE_PATH:=./results}"
: "${TASK_NAME:=appworld}"
: "${APPWORLD_ROOT:=../ace-appworld}"

run_one() {
  local config_name="$1"
  local seed="$2"
  local api_provider="$3"
  local generator_model="$4"
  local reflector_model="$5"
  local curator_model="$6"

  python -m eval.appworld.run \
    --task_name "${TASK_NAME}" \
    --mode offline \
    --dataset_name train \
    --max_agent_steps 30 \
    --api_provider "${api_provider}" \
    --generator_model "${generator_model}" \
    --reflector_model "${reflector_model}" \
    --curator_model "${curator_model}" \
    --json_mode \
    --telemetry_enabled \
    --telemetry_metrics_interval_seconds 15 \
    --config_name "${config_name}_offline" \
    --seed "${seed}" \
    --appworld_root "${APPWORLD_ROOT}" \
    --save_path "${SAVE_PATH}"

  python -m eval.appworld.run \
    --task_name "${TASK_NAME}" \
    --mode eval_only \
    --dataset_name test_normal \
    --max_agent_steps 30 \
    --api_provider "${api_provider}" \
    --generator_model "${generator_model}" \
    --telemetry_enabled \
    --telemetry_metrics_interval_seconds 15 \
    --config_name "${config_name}_eval_test_normal" \
    --seed "${seed}" \
    --appworld_root "${APPWORLD_ROOT}" \
    --save_path "${SAVE_PATH}"

  python -m eval.appworld.run \
    --task_name "${TASK_NAME}" \
    --mode eval_only \
    --dataset_name test_challenge \
    --max_agent_steps 30 \
    --api_provider "${api_provider}" \
    --generator_model "${generator_model}" \
    --telemetry_enabled \
    --telemetry_metrics_interval_seconds 15 \
    --config_name "${config_name}_eval_test_challenge" \
    --seed "${seed}" \
    --appworld_root "${APPWORLD_ROOT}" \
    --save_path "${SAVE_PATH}"
}

for seed in 42 43 44; do
  run_one "all_gptoss20b" "${seed}" "openai" "gpt-oss:20b" "gpt-oss:20b" "gpt-oss:20b"
  run_one "all_minimax" "${seed}" "minimax" "MiniMax-M2.5" "MiniMax-M2.5" "MiniMax-M2.5"
  run_one "mixed_reflector_strong" "${seed}" "openai" "gpt-oss:20b" "MiniMax-M2.5" "gpt-oss:20b"
done
