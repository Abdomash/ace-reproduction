#!/usr/bin/env bash
set -euo pipefail

# Unified runner for local/quick/full ACE experiment entrypoints.
# Supports FiNER, Formula, Mind2Web, and AppWorld.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/run_experiments.sh <preset> [options]

Presets:
  finer_subset          Small FiNER offline run (section-sized style)
  finer_full            FiNER full config-backed run
  formula_subset        Small Formula offline run
  appworld_subset       Small AppWorld eval_only run
  appworld_full_eval    AppWorld eval_only over test_normal and test_challenge
  all_full              Runs finer_full then appworld_full_eval

Options (override defaults):
  --provider <name>         API provider: openai|together|sambanova|minimax
  --generator <model>
  --reflector <model>
  --curator <model>
  --save-path <dir>         Output root (default: ./results)
  --config-name <label>
  --seed <int>
  --mode <offline|online|eval_only>  (for single-task presets)
  --eval-steps <int>       Evaluate validation every N training steps
  --max-tokens <int>       Overall completion budget (default: 8192 for thinking models)
  --reasoning-max-tokens <int>
                           OpenRouter thinking budget; 0 disables explicit reasoning (default: 4096)
  --telemetry <0|1>
  --telemetry-interval <sec>
  --json-mode <0|1>       Enable JSON mode for LLM calls (default: 0, matching ACE docs)
  --appworld-root <path>
  --appworld-max-steps <int>
  --dry-run

Environment variables for API keys (depending on --provider):
  OPENAI_API_KEY, TOGETHER_API_KEY, SAMBANOVA_API_KEY, MINIMAX_API_KEY

Examples:
  ./scripts/run_experiments.sh finer_subset --provider openai --generator gpt-oss:20b
  ./scripts/run_experiments.sh appworld_subset --provider openai --generator gpt-oss:20b --appworld-root ../ace-appworld
  ./scripts/run_experiments.sh all_full --provider minimax --generator MiniMax-M2.5 --reflector MiniMax-M2.5 --curator MiniMax-M2.5
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

PRESET="$1"
shift

API_PROVIDER="openai"
GENERATOR_MODEL="gpt-oss:20b"
REFLECTOR_MODEL="gpt-oss:20b"
CURATOR_MODEL="gpt-oss:20b"
SAVE_PATH="${ACE_ROOT}/results"
CONFIG_NAME="default"
SEED="42"
MODE="offline"
EVAL_STEPS="100"
MAX_TOKENS="${MAX_TOKENS:-8192}"
REASONING_MAX_TOKENS="${ACE_REASONING_MAX_TOKENS:-4096}"
TELEMETRY="1"
TELEMETRY_INTERVAL=""
JSON_MODE="${JSON_MODE:-0}"
APPWORLD_ROOT="${ACE_ROOT}/../ace-appworld"
APPWORLD_MAX_STEPS="30"
DRY_RUN="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --provider) API_PROVIDER="$2"; shift 2 ;;
    --generator) GENERATOR_MODEL="$2"; shift 2 ;;
    --reflector) REFLECTOR_MODEL="$2"; shift 2 ;;
    --curator) CURATOR_MODEL="$2"; shift 2 ;;
    --save-path) SAVE_PATH="$2"; shift 2 ;;
    --config-name) CONFIG_NAME="$2"; shift 2 ;;
    --seed) SEED="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --eval-steps|--eval_steps) EVAL_STEPS="$2"; shift 2 ;;
    --max-tokens|--max_tokens) MAX_TOKENS="$2"; shift 2 ;;
    --reasoning-max-tokens|--reasoning_max_tokens) REASONING_MAX_TOKENS="$2"; shift 2 ;;
    --telemetry) TELEMETRY="$2"; shift 2 ;;
    --telemetry-interval) TELEMETRY_INTERVAL="$2"; shift 2 ;;
    --json-mode|--json_mode) JSON_MODE="$2"; shift 2 ;;
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
    minimax) [[ -n "${MINIMAX_API_KEY:-}" ]] || { echo "Missing MINIMAX_API_KEY"; exit 1; } ;;
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

ensure_subset_file() {
  local source_file="$1"
  local dest_file="$2"
  local count="$3"
  python3 - "$source_file" "$dest_file" "$count" <<'PY'
import json
import os
import sys

source, dest, count = sys.argv[1], sys.argv[2], int(sys.argv[3])
os.makedirs(os.path.dirname(dest), exist_ok=True)
with open(source, "r", encoding="utf-8") as f:
    lines = [ln for ln in f if ln.strip()]
subset = lines[:count]
with open(dest, "w", encoding="utf-8") as f:
    for ln in subset:
        f.write(ln)
print(f"Wrote {len(subset)} lines -> {dest}", file=sys.stderr)
PY
}

make_finer_subset_config() {
  local cfg_dir="${ACE_ROOT}/eval/finance/data/generated"
  local cfg_file="${cfg_dir}/sample_config_finer_subset.json"
  local train_src="${ACE_ROOT}/eval/finance/data/finer_train_batched_1000_samples.jsonl"
  local val_src="${ACE_ROOT}/eval/finance/data/finer_val_batched_500_samples.jsonl"
  local test_src="${ACE_ROOT}/eval/finance/data/finer_test_subset_006_seed42.jsonl"
  local train_out="${cfg_dir}/finer_train_60.jsonl"
  local val_out="${cfg_dir}/finer_val_40.jsonl"
  local test_out="${cfg_dir}/finer_test_80.jsonl"

  ensure_subset_file "${train_src}" "${train_out}" 60
  ensure_subset_file "${val_src}" "${val_out}" 40
  ensure_subset_file "${test_src}" "${test_out}" 80

  cat > "${cfg_file}" <<EOF
{
  "finer": {
    "train_data": "./eval/finance/data/generated/finer_train_60.jsonl",
    "val_data": "./eval/finance/data/generated/finer_val_40.jsonl",
    "test_data": "./eval/finance/data/generated/finer_test_80.jsonl"
  }
}
EOF
  echo "${cfg_file}"
}

make_formula_subset_config() {
  local cfg_dir="${ACE_ROOT}/eval/finance/data/generated"
  local cfg_file="${cfg_dir}/sample_config_formula_subset.json"
  local train_src="${ACE_ROOT}/eval/finance/data/formula_train_subset_500.jsonl"
  local val_src="${ACE_ROOT}/eval/finance/data/formula_val_subset_300.jsonl"
  local test_src="${ACE_ROOT}/eval/finance/data/formula_test.jsonl"
  local train_out="${cfg_dir}/formula_train_80.jsonl"
  local val_out="${cfg_dir}/formula_val_40.jsonl"
  local test_out="${cfg_dir}/formula_test_80.jsonl"

  ensure_subset_file "${train_src}" "${train_out}" 80
  ensure_subset_file "${val_src}" "${val_out}" 40
  ensure_subset_file "${test_src}" "${test_out}" 80

  cat > "${cfg_file}" <<EOF
{
  "formula": {
    "train_data": "./eval/finance/data/generated/formula_train_80.jsonl",
    "val_data": "./eval/finance/data/generated/formula_val_40.jsonl",
    "test_data": "./eval/finance/data/generated/formula_test_80.jsonl"
  }
}
EOF
  echo "${cfg_file}"
}

check_api_key
mkdir -p "${SAVE_PATH}"

TELEMETRY_ARGS="$(telemetry_args)"
JSON_MODE_ARGS=""
if [[ "${JSON_MODE}" == "1" ]]; then
  JSON_MODE_ARGS="--json_mode"
fi
export ACE_REASONING_MAX_TOKENS="${REASONING_MAX_TOKENS}"

cd "${ACE_ROOT}"

common_finance_args="--api_provider ${API_PROVIDER} --generator_model ${GENERATOR_MODEL} --reflector_model ${REFLECTOR_MODEL} --curator_model ${CURATOR_MODEL} --seed ${SEED} --config_name ${CONFIG_NAME} --save_path ${SAVE_PATH} --eval_steps ${EVAL_STEPS} --max_tokens ${MAX_TOKENS} ${TELEMETRY_ARGS}"

case "${PRESET}" in
  finer_subset)
    cfg_path="$(make_finer_subset_config)"
    run_cmd "python -m eval.finance.run --task_name finer --mode ${MODE} ${JSON_MODE_ARGS} --sample_config_path ${cfg_path} ${common_finance_args}"
    ;;

  finer_full)
    run_cmd "python -m eval.finance.run --task_name finer --mode ${MODE} ${JSON_MODE_ARGS} ${common_finance_args}"
    ;;

  formula_subset)
    cfg_path="$(make_formula_subset_config)"
    run_cmd "python -m eval.finance.run --task_name formula --mode ${MODE} ${JSON_MODE_ARGS} --sample_config_path ${cfg_path} ${common_finance_args}"
    ;;

  appworld_subset)
    run_cmd "python -m eval.appworld.run --task_name appworld --mode eval_only --dataset_name dev --max_agent_steps ${APPWORLD_MAX_STEPS} --api_provider ${API_PROVIDER} --generator_model ${GENERATOR_MODEL} --reflector_model ${REFLECTOR_MODEL} --curator_model ${CURATOR_MODEL} --seed ${SEED} --config_name ${CONFIG_NAME} --appworld_root ${APPWORLD_ROOT} --save_path ${SAVE_PATH} --max_tokens ${MAX_TOKENS} ${TELEMETRY_ARGS}"
    ;;

  appworld_full_eval)
    run_cmd "python -m eval.appworld.run --task_name appworld --mode eval_only --dataset_name test_normal --max_agent_steps ${APPWORLD_MAX_STEPS} --api_provider ${API_PROVIDER} --generator_model ${GENERATOR_MODEL} --reflector_model ${REFLECTOR_MODEL} --curator_model ${CURATOR_MODEL} --seed ${SEED} --config_name ${CONFIG_NAME}_test_normal --appworld_root ${APPWORLD_ROOT} --save_path ${SAVE_PATH} --max_tokens ${MAX_TOKENS} ${TELEMETRY_ARGS}"
    run_cmd "python -m eval.appworld.run --task_name appworld --mode eval_only --dataset_name test_challenge --max_agent_steps ${APPWORLD_MAX_STEPS} --api_provider ${API_PROVIDER} --generator_model ${GENERATOR_MODEL} --reflector_model ${REFLECTOR_MODEL} --curator_model ${CURATOR_MODEL} --seed ${SEED} --config_name ${CONFIG_NAME}_test_challenge --appworld_root ${APPWORLD_ROOT} --save_path ${SAVE_PATH} --max_tokens ${MAX_TOKENS} ${TELEMETRY_ARGS}"
    ;;

  all_full)
    run_cmd "python -m eval.finance.run --task_name finer --mode offline ${JSON_MODE_ARGS} ${common_finance_args}"
    run_cmd "python -m eval.appworld.run --task_name appworld --mode eval_only --dataset_name test_normal --max_agent_steps ${APPWORLD_MAX_STEPS} --api_provider ${API_PROVIDER} --generator_model ${GENERATOR_MODEL} --reflector_model ${REFLECTOR_MODEL} --curator_model ${CURATOR_MODEL} --seed ${SEED} --config_name ${CONFIG_NAME}_test_normal --appworld_root ${APPWORLD_ROOT} --save_path ${SAVE_PATH} --max_tokens ${MAX_TOKENS} ${TELEMETRY_ARGS}"
    run_cmd "python -m eval.appworld.run --task_name appworld --mode eval_only --dataset_name test_challenge --max_agent_steps ${APPWORLD_MAX_STEPS} --api_provider ${API_PROVIDER} --generator_model ${GENERATOR_MODEL} --reflector_model ${REFLECTOR_MODEL} --curator_model ${CURATOR_MODEL} --seed ${SEED} --config_name ${CONFIG_NAME}_test_challenge --appworld_root ${APPWORLD_ROOT} --save_path ${SAVE_PATH} --max_tokens ${MAX_TOKENS} ${TELEMETRY_ARGS}"
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
