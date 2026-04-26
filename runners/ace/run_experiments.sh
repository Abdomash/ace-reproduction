#!/usr/bin/env bash
set -euo pipefail

# Unified runner for local/quick/full ACE experiment entrypoints.
# Supports FiNER, Formula, Mind2Web, and AppWorld.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ACE_ROOT="${ACE_ROOT:-${REPO_ROOT}/projects/ace}"
APPWORLD_ROOT="${APPWORLD_ROOT:-${REPO_ROOT}/projects/ace-appworld}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
APPWORLD_BIN="${APPWORLD_BIN:-}"

usage() {
  cat <<'EOF'
Usage:
  runners/ace/run_experiments.sh <preset> [options]

Presets:
  finer_subset          Small FiNER offline run (section-sized style)
  finer_full            FiNER full config-backed run
  formula_subset        Small Formula offline run
  appworld_adaptation   AppWorld adaptation run through ace-appworld
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
  --results-root <dir>      Root result directory (default: <repo>/results)
  --run-type <slug>         Run type (default from preset: subset or full)
  --config-slug <slug>      Explicit config identity for result paths
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
  --resume-from <run_dir>
  --checkpoint-enabled
  --stop-after-stage <stage>
  --stop-after-step <n>
  --stop-after-task <n>
  --checkpoint-every-task <n>
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
RESULTS_ROOT="${RESULTS_ROOT:-${REPO_ROOT}/results}"
RUN_TYPE="${RUN_TYPE:-}"
CONFIG_SLUG="${CONFIG_SLUG:-default}"
SAVE_PATH_OVERRIDE="${SAVE_PATH:-}"
CONFIG_NAME="default"
SEED="42"
MODE="offline"
EVAL_STEPS="100"
TEST_WORKERS="${TEST_WORKERS:-20}"
TEST_WORKERS_SET="0"
MAX_TOKENS="${MAX_TOKENS:-4096}"
TELEMETRY="1"
TELEMETRY_INTERVAL=""
APPWORLD_MAX_STEPS="30"
RESUME_FROM=""
CHECKPOINT_ENABLED="0"
STOP_AFTER_STAGE=""
STOP_AFTER_STEP=""
STOP_AFTER_TASK=""
CHECKPOINT_EVERY_TASK="1"
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
    --results-root|--results_root) RESULTS_ROOT="$2"; shift 2 ;;
    --run-type|--run_type) RUN_TYPE="$2"; shift 2 ;;
    --config-slug|--config_slug) CONFIG_SLUG="$2"; shift 2 ;;
    --save-path) SAVE_PATH_OVERRIDE="$2"; shift 2 ;;
    --config-name) CONFIG_NAME="$2"; shift 2 ;;
    --seed) SEED="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --eval-steps|--eval_steps) EVAL_STEPS="$2"; shift 2 ;;
    --test-workers|--test_workers) TEST_WORKERS="$2"; TEST_WORKERS_SET="1"; shift 2 ;;
    --max-tokens|--max_tokens) MAX_TOKENS="$2"; shift 2 ;;
    --telemetry) TELEMETRY="$2"; shift 2 ;;
    --telemetry-interval) TELEMETRY_INTERVAL="$2"; shift 2 ;;
    --appworld-root) APPWORLD_ROOT="$2"; shift 2 ;;
    --appworld-max-steps) APPWORLD_MAX_STEPS="$2"; shift 2 ;;
    --resume-from) RESUME_FROM="$2"; shift 2 ;;
    --checkpoint-enabled) CHECKPOINT_ENABLED="1"; shift ;;
    --stop-after-stage) STOP_AFTER_STAGE="$2"; shift 2 ;;
    --stop-after-step) STOP_AFTER_STEP="$2"; shift 2 ;;
    --stop-after-task) STOP_AFTER_TASK="$2"; shift 2 ;;
    --checkpoint-every-task) CHECKPOINT_EVERY_TASK="$2"; shift 2 ;;
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

default_benchmark() {
  case "$1" in
    finer_subset|finer_full) echo "ace-finer" ;;
    formula_subset) echo "ace-formula" ;;
    appworld_adaptation|appworld_subset|appworld_full_eval) echo "ace-appworld" ;;
    all_full) echo "ace-finer" ;;
    *) echo "ace-${1}" ;;
  esac
}

default_run_type() {
  case "$1" in
    *_subset) echo "subset" ;;
    *_full|*_full_eval|all_full) echo "full" ;;
    *) echo "debug" ;;
  esac
}

BENCHMARK="$(default_benchmark "${PRESET}")"
if [[ -z "${RUN_TYPE}" ]]; then
  RUN_TYPE="$(default_run_type "${PRESET}")"
fi
SAVE_PATH="${SAVE_PATH_OVERRIDE:-${RESULTS_ROOT}/${BENCHMARK}/${RUN_TYPE}/${CONFIG_SLUG}}"
IDENTITY_ARGS="--benchmark ${BENCHMARK} --run_type ${RUN_TYPE} --config_slug ${CONFIG_SLUG}"

if [[ "${DRY_RUN}" == "0" ]]; then
  check_api_key
  mkdir -p "${SAVE_PATH}"
fi

TELEMETRY_ARGS="$(telemetry_args)"

common_finance_args="--api_provider ${API_PROVIDER} --generator_model ${GENERATOR_MODEL} --reflector_model ${REFLECTOR_MODEL} --curator_model ${CURATOR_MODEL} --seed ${SEED} --config_name ${CONFIG_NAME} --save_path ${SAVE_PATH} ${IDENTITY_ARGS} --eval_steps ${EVAL_STEPS} --test_workers ${TEST_WORKERS} --max_tokens ${MAX_TOKENS} ${TELEMETRY_ARGS}"
if [[ -n "${RESUME_FROM}" ]]; then
  common_finance_args="${common_finance_args} --resume-from ${RESUME_FROM}"
fi
if [[ "${CHECKPOINT_ENABLED}" == "1" ]]; then
  common_finance_args="${common_finance_args} --checkpoint-enabled"
fi
if [[ -n "${STOP_AFTER_STAGE}" ]]; then
  common_finance_args="${common_finance_args} --stop-after-stage ${STOP_AFTER_STAGE}"
fi
if [[ -n "${STOP_AFTER_STEP}" ]]; then
  common_finance_args="${common_finance_args} --stop-after-step ${STOP_AFTER_STEP}"
fi

if [[ -n "${GENERATOR_PROVIDER}" ]]; then
  common_finance_args="${common_finance_args} --generator_provider ${GENERATOR_PROVIDER}"
fi
if [[ -n "${REFLECTOR_PROVIDER}" ]]; then
  common_finance_args="${common_finance_args} --reflector_provider ${REFLECTOR_PROVIDER}"
fi
if [[ -n "${CURATOR_PROVIDER}" ]]; then
  common_finance_args="${common_finance_args} --curator_provider ${CURATOR_PROVIDER}"
fi

provider_for_role() {
  local role_provider="$1"
  if [[ -n "${role_provider}" ]]; then
    echo "${role_provider}"
  else
    echo "${API_PROVIDER}"
  fi
}

appworld_base_config() {
  case "$1" in
    offline) echo "ACE_offline_no_GT_adaptation" ;;
    online) echo "ACE_online_no_GT" ;;
    eval_only) echo "ACE_offline_no_GT_evaluation" ;;
    *) echo "Unsupported AppWorld mode: $1" >&2; exit 1 ;;
  esac
}

ensure_appworld_config() {
  local experiment_name="$1"
  local base_config="$2"
  local config_dir="${APPWORLD_EXPERIMENT_CONFIGS}"
  local target="${config_dir}/${experiment_name}.jsonnet"
  local source="${APPWORLD_ROOT}/experiments/configs/${base_config}.jsonnet"

  if [[ -f "${target}" ]]; then
    return
  fi
  if [[ ! -f "${source}" ]]; then
    echo "Missing ace-appworld config template: ${source}" >&2
    exit 1
  fi
  if [[ "${DRY_RUN}" == "0" ]]; then
    mkdir -p "${config_dir}"
    cp "${source}" "${target}"
  fi
}

resolve_appworld_bin() {
  if [[ -n "${APPWORLD_BIN}" ]]; then
    echo "${APPWORLD_BIN}"
    return
  fi
  if [[ -x "${APPWORLD_ROOT}/.venv/bin/appworld" ]]; then
    echo "${APPWORLD_ROOT}/.venv/bin/appworld"
    return
  fi
  if command -v appworld >/dev/null 2>&1; then
    command -v appworld
    return
  fi
  echo "appworld"
}

appworld_python_from_bin() {
  local appworld_bin="$1"
  local shebang

  if [[ -f "${appworld_bin}" ]]; then
    shebang="$(sed -n '1s/^#!//p' "${appworld_bin}")"
    if [[ -n "${shebang}" && -x "${shebang}" ]]; then
      echo "${shebang}"
      return
    fi
  fi
  echo ""
}

print_appworld_setup_help() {
  cat >&2 <<EOF
AppWorld is not installed in the Python environment used by the runner.

The ace-appworld README requires installing both packages from source:

  cd ${APPWORLD_ROOT}
  python3.11 -m venv .venv
  source .venv/bin/activate
  python -m pip install --upgrade pip setuptools wheel
  python -m pip install -e .
  python -m pip install -e "experiments[simplified]"
  appworld install --repo
  appworld download data

Then rerun this command, or set APPWORLD_BIN=/path/to/appworld if you use
a different Python 3.11 environment.
EOF
}

check_appworld_environment() {
  local appworld_bin="$1"
  local appworld_python
  appworld_python="$(appworld_python_from_bin "${appworld_bin}")"

  if [[ -z "${appworld_python}" ]]; then
    echo "Could not determine Python interpreter for AppWorld command: ${appworld_bin}" >&2
    print_appworld_setup_help
    exit 1
  fi

  if ! "${appworld_python}" - <<'PY'
import importlib
import sys

missing = []
for module_name in ("appworld", "appworld_experiments", "litellm"):
    try:
        importlib.import_module(module_name)
    except Exception as exc:
        missing.append(f"{module_name}: {exc}")

if missing:
    print("\n".join(missing), file=sys.stderr)
    raise SystemExit(1)
PY
  then
    echo "AppWorld command failed environment check: ${appworld_bin}" >&2
    print_appworld_setup_help
    exit 1
  fi
}

appworld_override_json() {
  local mode="$1"
  local dataset="$2"
  local max_steps="$3"
  local playbook_path="$4"
  local generator_provider
  local reflector_provider
  local curator_provider
  generator_provider="$(provider_for_role "${GENERATOR_PROVIDER}")"
  reflector_provider="$(provider_for_role "${REFLECTOR_PROVIDER}")"
  curator_provider="$(provider_for_role "${CURATOR_PROVIDER}")"

  "${PYTHON_BIN}" - "$mode" "$dataset" "$max_steps" "$playbook_path" \
    "$generator_provider" "$GENERATOR_MODEL" \
    "$reflector_provider" "$REFLECTOR_MODEL" \
    "$curator_provider" "$CURATOR_MODEL" \
    "$SEED" "$MAX_TOKENS" <<'PY'
import json
import sys

(
    mode,
    dataset,
    max_steps,
    playbook_path,
    generator_provider,
    generator_model,
    reflector_provider,
    reflector_model,
    curator_provider,
    curator_model,
    seed,
    max_tokens,
) = sys.argv[1:]

def model_config(provider: str, model: str) -> dict:
    config = {
        "name": model,
        "provider": provider,
        "temperature": 0,
        "seed": 100,
        "stop": ["<|endoftext|>", "<|eot_id|>", "<|start_header_id|>"],
        "logprobs": False,
        "top_logprobs": None,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "n": 1,
        "response_format": {"type": "text"},
        "retry_after_n_seconds": 10,
        "use_cache": True,
        "max_retries": 50,
        "max_tokens": int(max_tokens),
    }
    token_cost_data = openrouter_token_cost_data(provider, model)
    if token_cost_data:
        config["token_cost_data"] = token_cost_data
    return config

def openrouter_token_cost_data(provider: str, model: str) -> dict | None:
    if provider.lower() != "openrouter":
        return None
    # USD per token, matching LiteLLM's custom model pricing format.
    pricing_by_model = {
        "openai/gpt-oss-120b:nitro": {
            "input_cost_per_token": 0.039 / 1_000_000,
            "output_cost_per_token": 0.19 / 1_000_000,
            "litellm_provider": "openai",
            "mode": "chat",
            "max_input_tokens": 131072,
            "max_output_tokens": 32768,
        },
        "openai/gpt-oss-20b:nitro": {
            "input_cost_per_token": 0.03 / 1_000_000,
            "output_cost_per_token": 0.14 / 1_000_000,
            "litellm_provider": "openai",
            "mode": "chat",
            "max_input_tokens": 131072,
            "max_output_tokens": 32768,
        },
        "minimax/minimax-m2.7": {
            "input_cost_per_token": 0.30 / 1_000_000,
            "output_cost_per_token": 1.20 / 1_000_000,
            "litellm_provider": "openai",
            "mode": "chat",
            "max_input_tokens": 196608,
        },
    }
    return pricing_by_model.get(model.lower())

run_type = "ace-evaluation" if mode == "eval_only" else "ace-adaptation"
agent = {
    "appworld_config": {"random_seed": int(seed)},
    "max_steps": int(max_steps),
}
if mode == "eval_only":
    agent["generator_model_config"] = model_config(generator_provider, generator_model)
    agent["trained_playbook_file_path"] = playbook_path
else:
    agent["generator_model_config"] = model_config(generator_provider, generator_model)
    agent["reflector_model_config"] = model_config(reflector_provider, reflector_model)
    agent["curator_model_config"] = model_config(curator_provider, curator_model)
    agent["trained_playbook_file_path"] = playbook_path

print(json.dumps({"config": {"run_type": run_type, "dataset": dataset, "agent": agent}}))
PY
}

run_appworld() {
  local mode="$1"
  local dataset="$2"
  local experiment_name="$3"
  local save_path="$4"
  local max_steps="$5"
  local playbook_path="$6"
  local base_config
  local override_json
  base_config="$(appworld_base_config "${mode}")"

  export APPWORLD_PROJECT_PATH="${APPWORLD_ROOT}"
  export APPWORLD_EXPERIMENT_OUTPUTS="${save_path}"
  export APPWORLD_EXPERIMENT_CONFIGS="${save_path}/_appworld_configs"
  export APPWORLD_MAESTRO_TELEMETRY="${TELEMETRY}"
  if [[ -n "${TELEMETRY_INTERVAL}" ]]; then
    export APPWORLD_MAESTRO_METRICS_INTERVAL_SECONDS="${TELEMETRY_INTERVAL}"
  fi

  ensure_appworld_config "${experiment_name}" "${base_config}"
  override_json="$(appworld_override_json "${mode}" "${dataset}" "${max_steps}" "${playbook_path}")"

  local appworld_bin
  appworld_bin="$(resolve_appworld_bin)"
  if [[ "${DRY_RUN}" == "0" ]]; then
    check_appworld_environment "${appworld_bin}"
  fi

  local cmd="cd ${APPWORLD_ROOT} && ${appworld_bin} run ${experiment_name} --root ${APPWORLD_ROOT} --num-processes ${TEST_WORKERS} --override '${override_json}'"
  run_cmd "${cmd}"

  if [[ "${DRY_RUN}" == "0" ]]; then
    mkdir -p "${save_path}"
  fi
}

case "${PRESET}" in
  finer_subset)
    cd "${ACE_ROOT}"
    run_cmd "python -m eval.finance.run --task_name finer --mode ${MODE} --sample_config_path ${ACE_ROOT}/eval/finance/data/sample_config.json --train_limit 60 --val_limit 40 --test_limit 80 ${common_finance_args}"
    ;;

  finer_full)
    cd "${ACE_ROOT}"
    run_cmd "python -m eval.finance.run --task_name finer --mode ${MODE} ${common_finance_args}"
    ;;

  formula_subset)
    cd "${ACE_ROOT}"
    run_cmd "python -m eval.finance.run --task_name formula --mode ${MODE} --sample_config_path ${ACE_ROOT}/eval/finance/data/sample_config.json --train_limit 80 --val_limit 40 --test_limit 80 ${common_finance_args}"
    ;;

  appworld_adaptation)
    run_appworld "${MODE}" "train" "${CONFIG_NAME}" "${SAVE_PATH}" "${APPWORLD_MAX_STEPS}" "${APPWORLD_PLAYBOOK_PATH:-${APPWORLD_ROOT}/experiments/playbooks/${CONFIG_NAME}_playbook.txt}"
    ;;

  appworld_subset)
    run_appworld "eval_only" "dev" "${CONFIG_NAME}" "${SAVE_PATH}" "${APPWORLD_MAX_STEPS}" "${APPWORLD_PLAYBOOK_PATH:-${APPWORLD_ROOT}/experiments/playbooks/appworld_online_trained_playbook.txt}"
    ;;

  appworld_full_eval)
    APPWORLD_FULL_TEST_WORKERS="${TEST_WORKERS}"
    if [[ "${TEST_WORKERS_SET}" != "1" ]]; then
      APPWORLD_FULL_TEST_WORKERS="1"
    fi
    local_cmd="${PYTHON_BIN} ${REPO_ROOT}/runners/ace/run_appworld_full.py --appworld-root ${APPWORLD_ROOT} --save-path ${SAVE_PATH} --config-name ${CONFIG_NAME} --seed ${SEED} --generator-provider $(provider_for_role "${GENERATOR_PROVIDER}") --generator-model ${GENERATOR_MODEL} --reflector-provider $(provider_for_role "${REFLECTOR_PROVIDER}") --reflector-model ${REFLECTOR_MODEL} --curator-provider $(provider_for_role "${CURATOR_PROVIDER}") --curator-model ${CURATOR_MODEL} --max-steps ${APPWORLD_MAX_STEPS} --max-tokens ${MAX_TOKENS} --telemetry ${TELEMETRY} --test-workers ${APPWORLD_FULL_TEST_WORKERS} --initial-playbook-path ${APPWORLD_PLAYBOOK_PATH:-${APPWORLD_ROOT}/experiments/playbooks/appworld_initial_playbook.txt}"
    if [[ -n "${TELEMETRY_INTERVAL}" ]]; then
      local_cmd="${local_cmd} --telemetry-interval ${TELEMETRY_INTERVAL}"
    fi
    if [[ -n "${RESUME_FROM}" ]]; then
      local_cmd="${local_cmd} --resume-from ${RESUME_FROM}"
    fi
    if [[ "${CHECKPOINT_ENABLED}" == "1" ]]; then
      local_cmd="${local_cmd} --checkpoint-enabled"
    fi
    if [[ -n "${STOP_AFTER_STAGE}" ]]; then
      local_cmd="${local_cmd} --stop-after-stage ${STOP_AFTER_STAGE}"
    fi
    if [[ -n "${STOP_AFTER_TASK}" ]]; then
      local_cmd="${local_cmd} --stop-after-task ${STOP_AFTER_TASK}"
    fi
    if [[ -n "${CHECKPOINT_EVERY_TASK}" ]]; then
      local_cmd="${local_cmd} --checkpoint-every-task ${CHECKPOINT_EVERY_TASK}"
    fi
    run_cmd "${local_cmd}"
    ;;

  all_full)
    finer_save_path="${SAVE_PATH_OVERRIDE:-${RESULTS_ROOT}/ace-finer/${RUN_TYPE}/${CONFIG_SLUG}}"
    appworld_save_path="${SAVE_PATH_OVERRIDE:-${RESULTS_ROOT}/ace-appworld/${RUN_TYPE}/${CONFIG_SLUG}}"
    finer_identity_args="--benchmark ace-finer --run_type ${RUN_TYPE} --config_slug ${CONFIG_SLUG}"
    all_full_finance_args="--api_provider ${API_PROVIDER} --generator_model ${GENERATOR_MODEL} --reflector_model ${REFLECTOR_MODEL} --curator_model ${CURATOR_MODEL} --seed ${SEED} --config_name ${CONFIG_NAME} --save_path ${finer_save_path} ${finer_identity_args} --eval_steps ${EVAL_STEPS} --test_workers ${TEST_WORKERS} --max_tokens ${MAX_TOKENS} ${TELEMETRY_ARGS}"
    if [[ -n "${GENERATOR_PROVIDER}" ]]; then
      all_full_finance_args="${all_full_finance_args} --generator_provider ${GENERATOR_PROVIDER}"
    fi
    if [[ -n "${REFLECTOR_PROVIDER}" ]]; then
      all_full_finance_args="${all_full_finance_args} --reflector_provider ${REFLECTOR_PROVIDER}"
    fi
    if [[ -n "${CURATOR_PROVIDER}" ]]; then
      all_full_finance_args="${all_full_finance_args} --curator_provider ${CURATOR_PROVIDER}"
    fi
    cd "${ACE_ROOT}"
    run_cmd "python -m eval.finance.run --task_name finer --mode offline ${all_full_finance_args}"
    APPWORLD_FULL_TEST_WORKERS="${TEST_WORKERS}"
    if [[ "${TEST_WORKERS_SET}" != "1" ]]; then
      APPWORLD_FULL_TEST_WORKERS="1"
    fi
    run_cmd "${PYTHON_BIN} ${REPO_ROOT}/runners/ace/run_appworld_full.py --appworld-root ${APPWORLD_ROOT} --save-path ${appworld_save_path} --config-name ${CONFIG_NAME} --seed ${SEED} --generator-provider $(provider_for_role "${GENERATOR_PROVIDER}") --generator-model ${GENERATOR_MODEL} --reflector-provider $(provider_for_role "${REFLECTOR_PROVIDER}") --reflector-model ${REFLECTOR_MODEL} --curator-provider $(provider_for_role "${CURATOR_PROVIDER}") --curator-model ${CURATOR_MODEL} --max-steps ${APPWORLD_MAX_STEPS} --max-tokens ${MAX_TOKENS} --telemetry ${TELEMETRY} --test-workers ${APPWORLD_FULL_TEST_WORKERS} --initial-playbook-path ${APPWORLD_PLAYBOOK_PATH:-${APPWORLD_ROOT}/experiments/playbooks/appworld_initial_playbook.txt}"
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
case "${PRESET}" in
  appworld_adaptation|appworld_subset|appworld_full_eval)
    echo "AppWorld writes runs directly under the configured results path."
    ;;
  *)
    echo "Each run writes: run_config.json, final_results.json, detailed_llm_logs/, and telemetry/ (if enabled)."
    ;;
esac
