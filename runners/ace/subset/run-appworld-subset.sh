#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

usage() {
  cat <<'EOF'
Usage:
  runners/ace/subset/run-appworld-subset.sh <model-slug> [options]
  runners/ace/subset/run-appworld-subset.sh --model-slug <model-slug> [options]

Examples:
  runners/ace/subset/run-appworld-subset.sh minimax/minimax-m2.7
  runners/ace/subset/run-appworld-subset.sh openai/gpt-oss-120b:nitro --appworld-max-steps 10
  runners/ace/subset/run-appworld-subset.sh openai/gpt-oss-20b:nitro --config-name appworld_gptoss20b_dev --dry-run

Wrapper options:
  -m, --model-slug <model>  Model to use for generator, reflector, and curator.
  --provider <name>         Provider passed to the ACE runner (default: openrouter).
  --config-name <name>      Override the display/config label.
  --config-slug <slug>      Override the result path/config identity slug.
  -h, --help                Show this help.

All other options are forwarded to runners/ace/run_experiments.sh appworld_subset.
Environment variables such as CONFIG_NAME, CONFIG_SLUG, APPWORLD_ROOT,
APPWORLD_MAX_STEPS, RESULTS_ROOT, SEED, TEST_WORKERS, MAX_TOKENS, TELEMETRY,
and TELEMETRY_INTERVAL can also override defaults.
EOF
}

sanitize_hyphen() {
  printf '%s' "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//'
}

sanitize_underscore() {
  printf '%s' "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/_/g; s/^_+//; s/_+$//'
}

MODEL_SLUG="${MODEL_SLUG:-}"
PROVIDER="${PROVIDER:-${API_PROVIDER:-openrouter}}"
CONFIG_NAME_OVERRIDE="${CONFIG_NAME:-}"
CONFIG_SLUG_OVERRIDE="${CONFIG_SLUG:-}"
DRY_RUN_REQUESTED=0
EXTRA_ARGS=()

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

MODEL_SLUG="${MODEL_SLUG:-}"
PROVIDER="${PROVIDER:-${API_PROVIDER:-openrouter}}"
CONFIG_NAME_OVERRIDE="${CONFIG_NAME:-}"
CONFIG_SLUG_OVERRIDE="${CONFIG_SLUG:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--model|--model-slug|--model_slug)
      MODEL_SLUG="$2"
      shift 2
      ;;
    --provider)
      PROVIDER="$2"
      shift 2
      ;;
    --config-name|--config_name)
      CONFIG_NAME_OVERRIDE="$2"
      shift 2
      ;;
    --config-slug|--config_slug)
      CONFIG_SLUG_OVERRIDE="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN_REQUESTED=1
      EXTRA_ARGS+=("$1")
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      EXTRA_ARGS+=("$@")
      break
      ;;
    -*)
      EXTRA_ARGS+=("$1")
      shift
      if [[ $# -gt 0 && "$1" != -* ]]; then
        EXTRA_ARGS+=("$1")
        shift
      fi
      ;;
    *)
      if [[ -z "${MODEL_SLUG}" ]]; then
        MODEL_SLUG="$1"
      else
        EXTRA_ARGS+=("$1")
      fi
      shift
      ;;
  esac
done

if [[ -z "${MODEL_SLUG}" ]]; then
  usage >&2
  exit 1
fi

safe_model_slug="$(sanitize_hyphen "${MODEL_SLUG}")"
safe_model_name="$(sanitize_underscore "${MODEL_SLUG}")"

case "${MODEL_SLUG}" in
  minimax/minimax-m2.7)
    default_config_slug="${PROVIDER}-minimax-m2-7"
    default_config_name="ace_appworld_${PROVIDER}_minimax_m27_subset"
    ;;
  openai/gpt-oss-120b:nitro)
    default_config_slug="${PROVIDER}-gpt-oss-120b"
    default_config_name="ace_appworld_gptoss120b_subset"
    ;;
  openai/gpt-oss-20b:nitro)
    default_config_slug="${PROVIDER}-gpt-oss-20b"
    default_config_name="ace_appworld_gptoss20b_subset"
    ;;
  *)
    default_config_slug="${PROVIDER}-${safe_model_slug}"
    default_config_name="ace_appworld_${PROVIDER}_${safe_model_name}_subset"
    ;;
esac

config_name="${CONFIG_NAME_OVERRIDE:-${default_config_name}}"
config_slug="${CONFIG_SLUG_OVERRIDE:-${default_config_slug}}"
if [[ -z "${CONFIG_NAME_OVERRIDE}" && "${APPWORLD_UNIQUE_RUNS:-1}" != "0" ]]; then
  config_name="${config_name}_$(date -u +%Y%m%d_%H%M%S)"
fi
results_root="${RESULTS_ROOT:-${REPO_ROOT}/results}"
run_type="${RUN_TYPE:-subset}"
appworld_root="${APPWORLD_ROOT:-${REPO_ROOT}/projects/ace-appworld}"

RUN_ARGS=(
  appworld_subset
  --provider "${PROVIDER}"
  --generator "${GENERATOR_MODEL:-${MODEL_SLUG}}"
  --reflector "${REFLECTOR_MODEL:-${MODEL_SLUG}}"
  --curator "${CURATOR_MODEL:-${MODEL_SLUG}}"
  --config-name "${config_name}"
  --config-slug "${config_slug}"
  --results-root "${results_root}"
  --run-type "${run_type}"
  --seed "${SEED:-42}"
  --appworld-root "${appworld_root}"
  --appworld-max-steps "${APPWORLD_MAX_STEPS:-30}"
  --max-tokens "${MAX_TOKENS:-4096}"
  --telemetry "${TELEMETRY:-1}"
  --telemetry-interval "${TELEMETRY_INTERVAL:-5}"
)

if [[ -n "${TEST_WORKERS:-}" ]]; then
  RUN_ARGS+=(--test-workers "${TEST_WORKERS}")
fi

"${REPO_ROOT}/runners/ace/run_experiments.sh" "${RUN_ARGS[@]}" "${EXTRA_ARGS[@]}"

if [[ "${DRY_RUN_REQUESTED}" == "0" && "${APPWORLD_EXPORT_SUMMARY:-1}" != "0" ]]; then
  run_dir="${results_root}/ace-appworld/${run_type}/${config_slug}/${config_name}"
  export_args=(
    --run-dir "${run_dir}"
    --dataset "${APPWORLD_SUMMARY_DATASET:-dev}"
    --experiment-name "${config_name}"
    --appworld-root "${appworld_root}"
  )
  if [[ "${APPWORLD_PRUNE_RAW_TASKS:-1}" != "0" ]]; then
    export_args+=(--prune)
  fi
  python3 "${REPO_ROOT}/runners/ace/export_appworld_summary.py" "${export_args[@]}"
fi
