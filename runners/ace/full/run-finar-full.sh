#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

usage() {
  cat <<'EOF'
Usage:
  runners/ace/full/run-finar-full.sh <model-slug> [options]
  runners/ace/full/run-finar-full.sh --model-slug <model-slug> [options]

Examples:
  runners/ace/full/run-finar-full.sh openai/gpt-oss-120b
  runners/ace/full/run-finar-full.sh openai/gpt-oss-120b:nitro --config-name ace_all_gptoss120b_nitro
  runners/ace/full/run-finar-full.sh minimax/minimax-m2.7 --eval-steps 50
  runners/ace/full/run-finar-full.sh openai/gpt-oss-20b:nitro --dry-run

Wrapper options:
  -m, --model-slug <model>  Model to use for generator, reflector, and curator.
  --provider <name>         Provider passed to the ACE runner (default: openrouter).
  --config-name <name>      Override the display/config label.
  --config-slug <slug>      Override the result path/config identity slug.
  -h, --help                Show this help.

All other options are forwarded to runners/ace/run_experiments.sh finer_full.
Environment variables such as CONFIG_NAME, CONFIG_SLUG, RESULTS_ROOT, SEED,
MODE, EVAL_STEPS, TEST_WORKERS, MAX_TOKENS, TELEMETRY, and TELEMETRY_INTERVAL
can also override defaults.
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
default_test_workers=""

case "${MODEL_SLUG}" in
  openai/gpt-oss-120b)
    default_config_slug="${PROVIDER}-gpt-oss-120b"
    default_config_name="ace_all_${PROVIDER}_gptoss120b"
    ;;
  openai/gpt-oss-120b:nitro)
    default_config_slug="${PROVIDER}-gpt-oss-120b-nitro"
    default_config_name="ace_all_${PROVIDER}_gptoss120b_nitro"
    ;;
  openai/gpt-oss-20b:nitro)
    default_config_slug="${PROVIDER}-gpt-oss-20b"
    default_config_name="ace_all_${PROVIDER}_gptoss20b"
    default_test_workers="7"
    ;;
  minimax/minimax-m2.7)
    default_config_slug="${PROVIDER}-minimax-m2-7"
    default_config_name="ace_all_${PROVIDER}_minimax_m27"
    default_test_workers="5"
    ;;
  *)
    default_config_slug="${PROVIDER}-${safe_model_slug}"
    default_config_name="ace_all_${PROVIDER}_${safe_model_name}"
    ;;
esac

config_name="${CONFIG_NAME_OVERRIDE:-${default_config_name}}"
config_slug="${CONFIG_SLUG_OVERRIDE:-${default_config_slug}}"

RUN_ARGS=(
  finer_full
  --provider "${PROVIDER}"
  --generator "${GENERATOR_MODEL:-${MODEL_SLUG}}"
  --reflector "${REFLECTOR_MODEL:-${MODEL_SLUG}}"
  --curator "${CURATOR_MODEL:-${MODEL_SLUG}}"
  --config-name "${config_name}"
  --config-slug "${config_slug}"
  --results-root "${RESULTS_ROOT:-${REPO_ROOT}/results}"
  --run-type "${RUN_TYPE:-full}"
  --seed "${SEED:-42}"
  --mode "${MODE:-offline}"
  --eval-steps "${EVAL_STEPS:-100}"
  --max-tokens "${MAX_TOKENS:-4096}"
  --telemetry "${TELEMETRY:-1}"
  --telemetry-interval "${TELEMETRY_INTERVAL:-5}"
)

if [[ -n "${TEST_WORKERS:-${default_test_workers}}" ]]; then
  RUN_ARGS+=(--test-workers "${TEST_WORKERS:-${default_test_workers}}")
fi

"${REPO_ROOT}/runners/ace/run_experiments.sh" "${RUN_ARGS[@]}" "${EXTRA_ARGS[@]}"