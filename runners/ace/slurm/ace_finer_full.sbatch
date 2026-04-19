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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
: "${ACE_ROOT:=${REPO_ROOT}/projects/ace}"
: "${APPWORLD_ROOT:=${REPO_ROOT}/projects/ace-appworld}"
: "${RESULTS_ROOT:=${REPO_ROOT}/results}"

if [ -n "${MAMBA_ENV:-}" ]; then
  mamba activate "${MAMBA_ENV}"
fi

: "${TASK_NAME:=finer}"

cd "${ACE_ROOT}"

run_one() {
  local config_name="$1"
  local seed="$2"
  local api_provider="$3"
  local generator_model="$4"
  local reflector_model="$5"
  local curator_model="$6"
  local config_slug="$7"
  local save_path="${RESULTS_ROOT}/ace-finer/full/${config_slug}"

  python -m eval.finance.run \
    --task_name "${TASK_NAME}" \
    --mode offline \
    --api_provider "${api_provider}" \
    --generator_model "${generator_model}" \
    --reflector_model "${reflector_model}" \
    --curator_model "${curator_model}" \
    --num_epochs 1 \
    --telemetry_enabled \
    --telemetry_metrics_interval_seconds 5 \
    --config_name "${config_name}" \
    --benchmark ace-finer \
    --run_type full \
    --config_slug "${config_slug}" \
    --seed "${seed}" \
    --save_path "${save_path}"
}

for seed in 42 43 44; do
  run_one "ace_all_openrouter_gptoss120b" "${seed}" "openrouter" "openai/gpt-oss-120b:nitro" "openai/gpt-oss-120b:nitro" "openai/gpt-oss-120b:nitro" "openrouter-gpt-oss-120b"
  run_one "ace_all_openrouter_minimax_m27" "${seed}" "openrouter" "minimax/minimax-m2.7" "minimax/minimax-m2.7" "minimax/minimax-m2.7" "openrouter-minimax-m2-7"
  run_one "ace_mixed_openrouter_minimax_m27_reflector" "${seed}" "openrouter" "openai/gpt-oss-120b:nitro" "minimax/minimax-m2.7" "openai/gpt-oss-120b:nitro" "openrouter-gpt-oss-120b-minimax-reflector"
done
