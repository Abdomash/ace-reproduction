#!/usr/bin/env bash
set -euo pipefail

# Unified runner for local/quick/full ACE experiment entrypoints.
# Supports FiNER, Formula, Mind2Web, and AppWorld.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ACE_ROOT="${ACE_ROOT:-${REPO_ROOT}/projects/ace}"
APPWORLD_ROOT="${APPWORLD_ROOT:-${REPO_ROOT}/projects/ace-appworld}"

usage() {
  cat <<'EOF'
Usage:
  runners/ace/run_experiments.sh <preset> [options]

Presets:
  finer_subset          Small FiNER offline run (section-sized style)
  finer_full            FiNER full config-backed run
  formula_subset        Small Formula offline run
  appworld_subset       Small AppWorld eval_only run
  appworld_full_eval    AppWorld eval_only over test_normal and test_challenge
  all_full              Runs finer_full then appworld_full_eval

Options (override defaults):
  --provider <name>         API provider: openrouter|openai|together|sambanova
  --generator-provider <name>
  --reflector-provider <name>
  --curator-provider <name>
  --generator <model>
  --reflector <model>
  --curator <model>
  --save-path <dir>         Output root (default: <repo>/results)
  --config-name <label>
  --seed <int>
  --mode <offline|online|eval_only>  (for single-task presets)
  --eval-steps <int>       Evaluate validation every N training steps
  --test-workers <int>     Parallel workers for test/validation calls (default: 20)
  --max-tokens <int>       Overall completion budget (default: 4096)
  --telemetry <0|1>
  --telemetry-interval <sec>
  --appworld-root <path>
  --appworld-max-steps <int>
  --dry-run

Environment variables for API keys (depending on --provider):
  OPENROUTER_API_KEY, OPENAI_API_KEY, TOGETHER_API_KEY, SAMBANOVA_API_KEY

Examples:
  runners/ace/run_experiments.sh finer_subset --provider openrouter --generator openai/gpt-oss-120b:nitro
  runners/ace/run_experiments.sh appworld_subset --provider openrouter --generator openai/gpt-oss-120b:nitro
  runners/ace/run_experiments.sh all_full --provider openrouter --generator minimax/minimax-m2.7 --reflector minimax/minimax-m2.7 --curator minimax/minimax-m2.7
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

PRESET="$1"
shift

API_PROVIDER="openrouter"
GENERATOR_PROVIDER=""
REFLECTOR_PROVIDER=""
CURATOR_PROVIDER=""
GENERATOR_MODEL="openai/gpt-oss-120b:nitro"
REFLECTOR_MODEL="openai/gpt-oss-120b:nitro"
CURATOR_MODEL="openai/gpt-oss-120b:nitro"
SAVE_PATH="${SAVE_PATH:-${REPO_ROOT}/results}"
CONFIG_NAME="default"
SEED="42"
MODE="offline"
EVAL_STEPS="100"
TEST_WORKERS="${TEST_WORKERS:-20}"
MAX_TOKENS="${MAX_TOKENS:-4096}"
TELEMETRY="1"
TELEMETRY_INTERVAL=""
APPWORLD_MAX_STEPS="30"
DRY_RUN="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --provider) API_PROVIDER="$2"; shift 2 ;;
    --generator-provider|--generator_provider) GENERATOR_PROVIDER="$2"; shift 2 ;;
    --reflector-provider|--reflector_provider) REFLECTOR_PROVIDER="$2"; shift 2 ;;
    --curator-provider|--curator_provider) CURATOR_PROVIDER="$2"; shift 2 ;;
    --generator) GENERATOR_MODEL="$2"; shift 2 ;;
    --reflector) REFLECTOR_MODEL="$2"; shift 2 ;;
    --curator) CURATOR_MODEL="$2"; shift 2 ;;
    --save-path) SAVE_PATH="$2"; shift 2 ;;
    --config-name) CONFIG_NAME="$2"; shift 2 ;;
    --seed) SEED="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --eval-steps|--eval_steps) EVAL_STEPS="$2"; shift 2 ;;
    --test-workers|--test_workers) TEST_WORKERS="$2"; shift 2 ;;
    --max-tokens|--max_tokens) MAX_TOKENS="$2"; shift 2 ;;
    --telemetry) TELEMETRY="$2"; shift 2 ;;
    --telemetry-interval) TELEMETRY_INTERVAL="$2"; shift 2 ;;
    --appworld-root) APPWORLD_ROOT="$2"; shift 2 ;;
    --appworld-max-steps) APPWORLD_MAX_STEPS="$2"; shift 2 ;;
    --dry-run) DRY_RUN="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

check_api_key() {
  case "${API_PROVIDER}" in
    openai) [[ -n "${OPENAI_API_KEY:-}" ]] || { echo "Missing OPENAI_API_KEY"; exit 1; } ;;
    together) [[ -n "${TOGETHER_API_KEY:-}" ]] || { echo "Missing TOGETHER_API_KEY"; exit 1; } ;;
    sambanova) [[ -n "${SAMBANOVA_API_KEY:-}" ]] || { echo "Missing SAMBANOVA_API_KEY"; exit 1; } ;;
    openrouter) [[ -n "${OPENROUTER_API_KEY:-}" ]] || { echo "Missing OPENROUTER_API_KEY"; exit 1; } ;;
    minimax) echo "Provider 'minimax' is deprecated; use '--provider openrouter' with model 'minimax/minimax-m2.7'"; exit 1 ;;
    *) echo "Unsupported provider: ${API_PROVIDER}"; exit 1 ;;
  esac
}

telemetry_args() {
  if [[ "${TELEMETRY}" == "1" ]]; then
    if [[ -n "${TELEMETRY_INTERVAL}" ]]; then
      echo "--telemetry_enabled --telemetry_metrics_interval_seconds ${TELEMETRY_INTERVAL}"
    else
      echo "--telemetry_enabled"
    fi
  else
    echo ""
  fi
}

run_cmd() {
  local cmd="$*"
  echo
  echo ">>> ${cmd}"
  if [[ "${DRY_RUN}" == "0" ]]; then
    eval "${cmd}"
  fi
}

if [[ "${DRY_RUN}" == "0" ]]; then
  check_api_key
  mkdir -p "${SAVE_PATH}"
fi

TELEMETRY_ARGS="$(telemetry_args)"

cd "${ACE_ROOT}"

common_finance_args="--api_provider ${API_PROVIDER} --generator_model ${GENERATOR_MODEL} --reflector_model ${REFLECTOR_MODEL} --curator_model ${CURATOR_MODEL} --seed ${SEED} --config_name ${CONFIG_NAME} --save_path ${SAVE_PATH} --eval_steps ${EVAL_STEPS} --test_workers ${TEST_WORKERS} --max_tokens ${MAX_TOKENS} ${TELEMETRY_ARGS}"

if [[ -n "${GENERATOR_PROVIDER}" ]]; then
  common_finance_args="${common_finance_args} --generator_provider ${GENERATOR_PROVIDER}"
fi
if [[ -n "${REFLECTOR_PROVIDER}" ]]; then
  common_finance_args="${common_finance_args} --reflector_provider ${REFLECTOR_PROVIDER}"
fi
if [[ -n "${CURATOR_PROVIDER}" ]]; then
  common_finance_args="${common_finance_args} --curator_provider ${CURATOR_PROVIDER}"
fi

role_provider_args=""
if [[ -n "${GENERATOR_PROVIDER}" ]]; then
  role_provider_args="${role_provider_args} --generator_provider ${GENERATOR_PROVIDER}"
fi
if [[ -n "${REFLECTOR_PROVIDER}" ]]; then
  role_provider_args="${role_provider_args} --reflector_provider ${REFLECTOR_PROVIDER}"
fi
if [[ -n "${CURATOR_PROVIDER}" ]]; then
  role_provider_args="${role_provider_args} --curator_provider ${CURATOR_PROVIDER}"
fi

case "${PRESET}" in
  finer_subset)
    run_cmd "python -m eval.finance.run --task_name finer --mode ${MODE} --sample_config_path ${ACE_ROOT}/eval/finance/data/sample_config.json --train_limit 60 --val_limit 40 --test_limit 80 ${common_finance_args}"
    ;;

  finer_full)
    run_cmd "python -m eval.finance.run --task_name finer --mode ${MODE} ${common_finance_args}"
    ;;

  formula_subset)
    run_cmd "python -m eval.finance.run --task_name formula --mode ${MODE} --sample_config_path ${ACE_ROOT}/eval/finance/data/sample_config.json --train_limit 80 --val_limit 40 --test_limit 80 ${common_finance_args}"
    ;;

  appworld_subset)
    run_cmd "python -m eval.appworld.run --task_name appworld --mode eval_only --dataset_name dev --max_agent_steps ${APPWORLD_MAX_STEPS} --api_provider ${API_PROVIDER} ${role_provider_args} --generator_model ${GENERATOR_MODEL} --reflector_model ${REFLECTOR_MODEL} --curator_model ${CURATOR_MODEL} --seed ${SEED} --config_name ${CONFIG_NAME} --appworld_root ${APPWORLD_ROOT} --save_path ${SAVE_PATH} --test_workers ${TEST_WORKERS} --max_tokens ${MAX_TOKENS} ${TELEMETRY_ARGS}"
    ;;

  appworld_full_eval)
    run_cmd "python -m eval.appworld.run --task_name appworld --mode eval_only --dataset_name test_normal --max_agent_steps ${APPWORLD_MAX_STEPS} --api_provider ${API_PROVIDER} ${role_provider_args} --generator_model ${GENERATOR_MODEL} --reflector_model ${REFLECTOR_MODEL} --curator_model ${CURATOR_MODEL} --seed ${SEED} --config_name ${CONFIG_NAME}_test_normal --appworld_root ${APPWORLD_ROOT} --save_path ${SAVE_PATH} --test_workers ${TEST_WORKERS} --max_tokens ${MAX_TOKENS} ${TELEMETRY_ARGS}"
    run_cmd "python -m eval.appworld.run --task_name appworld --mode eval_only --dataset_name test_challenge --max_agent_steps ${APPWORLD_MAX_STEPS} --api_provider ${API_PROVIDER} ${role_provider_args} --generator_model ${GENERATOR_MODEL} --reflector_model ${REFLECTOR_MODEL} --curator_model ${CURATOR_MODEL} --seed ${SEED} --config_name ${CONFIG_NAME}_test_challenge --appworld_root ${APPWORLD_ROOT} --save_path ${SAVE_PATH} --test_workers ${TEST_WORKERS} --max_tokens ${MAX_TOKENS} ${TELEMETRY_ARGS}"
    ;;

  all_full)
    run_cmd "python -m eval.finance.run --task_name finer --mode offline ${common_finance_args}"
    run_cmd "python -m eval.appworld.run --task_name appworld --mode eval_only --dataset_name test_normal --max_agent_steps ${APPWORLD_MAX_STEPS} --api_provider ${API_PROVIDER} ${role_provider_args} --generator_model ${GENERATOR_MODEL} --reflector_model ${REFLECTOR_MODEL} --curator_model ${CURATOR_MODEL} --seed ${SEED} --config_name ${CONFIG_NAME}_test_normal --appworld_root ${APPWORLD_ROOT} --save_path ${SAVE_PATH} --test_workers ${TEST_WORKERS} --max_tokens ${MAX_TOKENS} ${TELEMETRY_ARGS}"
    run_cmd "python -m eval.appworld.run --task_name appworld --mode eval_only --dataset_name test_challenge --max_agent_steps ${APPWORLD_MAX_STEPS} --api_provider ${API_PROVIDER} ${role_provider_args} --generator_model ${GENERATOR_MODEL} --reflector_model ${REFLECTOR_MODEL} --curator_model ${CURATOR_MODEL} --seed ${SEED} --config_name ${CONFIG_NAME}_test_challenge --appworld_root ${APPWORLD_ROOT} --save_path ${SAVE_PATH} --test_workers ${TEST_WORKERS} --max_tokens ${MAX_TOKENS} ${TELEMETRY_ARGS}"
    ;;

  *)
    echo "Unknown preset: ${PRESET}"
    usage
    exit 1
    ;;
esac

echo
echo "Completed preset: ${PRESET}"
echo "Outputs are under: ${SAVE_PATH}"
echo "Each run writes: run_config.json, final_results.json, detailed_llm_logs/, and telemetry/ (if enabled)."
