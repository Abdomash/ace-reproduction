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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
: "${APPWORLD_ROOT:=${REPO_ROOT}/projects/ace-appworld}"
: "${RESULTS_ROOT:=${REPO_ROOT}/results}"

if [ -n "${MAMBA_ENV:-}" ]; then
  mamba activate "${MAMBA_ENV}"
fi

run_one() {
  local config_name="$1"
  local seed="$2"
  local api_provider="$3"
  local generator_model="$4"
  local reflector_model="$5"
  local curator_model="$6"
  local config_slug="$7"
  local save_path="${RESULTS_ROOT}/ace-appworld/full/${config_slug}"
  local playbook_path="${APPWORLD_ROOT}/experiments/playbooks/${config_name}_${seed}_playbook.txt"

  APPWORLD_PLAYBOOK_PATH="${playbook_path}" \
    "${REPO_ROOT}/runners/ace/run_experiments.sh" appworld_adaptation \
      --mode offline \
      --provider "${api_provider}" \
      --generator "${generator_model}" \
      --reflector "${reflector_model}" \
      --curator "${curator_model}" \
      --config-name "${config_name}_offline" \
      --config-slug "${config_slug}" \
      --results-root "${RESULTS_ROOT}" \
      --run-type full \
      --seed "${seed}" \
      --appworld-root "${APPWORLD_ROOT}" \
      --appworld-max-steps 30 \
      --save-path "${save_path}" \
      --telemetry 1 \
      --telemetry-interval 15

  APPWORLD_PLAYBOOK_PATH="${playbook_path}" \
    "${REPO_ROOT}/runners/ace/run_experiments.sh" appworld_full_eval \
      --provider "${api_provider}" \
      --generator "${generator_model}" \
      --reflector "${reflector_model}" \
      --curator "${curator_model}" \
      --config-name "${config_name}_eval" \
      --config-slug "${config_slug}" \
      --results-root "${RESULTS_ROOT}" \
      --run-type full \
      --seed "${seed}" \
      --appworld-root "${APPWORLD_ROOT}" \
      --appworld-max-steps 30 \
      --save-path "${save_path}" \
      --telemetry 1 \
      --telemetry-interval 15
}

for seed in 42 43 44; do
  run_one "ace_all_openrouter_gptoss120b" "${seed}" "openrouter" "openai/gpt-oss-120b:nitro" "openai/gpt-oss-120b:nitro" "openai/gpt-oss-120b:nitro" "openrouter-gpt-oss-120b"
  run_one "ace_all_openrouter_minimax_m27" "${seed}" "openrouter" "minimax/minimax-m2.7" "minimax/minimax-m2.7" "minimax/minimax-m2.7" "openrouter-minimax-m2-7"
  run_one "ace_mixed_openrouter_minimax_m27_reflector" "${seed}" "openrouter" "openai/gpt-oss-120b:nitro" "minimax/minimax-m2.7" "openai/gpt-oss-120b:nitro" "openrouter-gpt-oss-120b-minimax-reflector"
done
