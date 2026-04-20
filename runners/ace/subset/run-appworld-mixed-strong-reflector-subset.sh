#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

usage() {
  cat <<'EOF'
Usage:
  runners/ace/subset/run-appworld-mixed-strong-reflector-subset.sh [options]

Examples:
  runners/ace/subset/run-appworld-mixed-strong-reflector-subset.sh
  runners/ace/subset/run-appworld-mixed-strong-reflector-subset.sh --dry-run
  runners/ace/subset/run-appworld-mixed-strong-reflector-subset.sh --seed 43

Default model assignment (per EXPERIMENTS.md §2 "ace_mixed_strong_reflector"):
  Generator:  openai/gpt-oss-120b  (cheap, via OpenRouter)
  Reflector:  minimax/minimax-m2.7 (strong, via OpenRouter)
  Curator:    openai/gpt-oss-120b  (cheap, via OpenRouter)

Wrapper options:
  --generator <model>       Override the generator model.
  --reflector <model>       Override the reflector model.
  --curator <model>         Override the curator model.
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

PROVIDER="${PROVIDER:-${API_PROVIDER:-openrouter}}"
CONFIG_NAME_OVERRIDE="${CONFIG_NAME:-}"
CONFIG_SLUG_OVERRIDE="${CONFIG_SLUG:-}"
DRY_RUN_REQUESTED=0
EXTRA_ARGS=()

GENERATOR_MODEL="${GENERATOR_MODEL:-openai/gpt-oss-120b}"
REFLECTOR_MODEL="${REFLECTOR_MODEL:-minimax/minimax-m2.7}"
CURATOR_MODEL="${CURATOR_MODEL:-openai/gpt-oss-120b}"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

PROVIDER="${PROVIDER:-${API_PROVIDER:-openrouter}}"
CONFIG_NAME_OVERRIDE="${CONFIG_NAME_OVERRIDE:-${CONFIG_NAME:-}}"
CONFIG_SLUG_OVERRIDE="${CONFIG_SLUG_OVERRIDE:-${CONFIG_SLUG:-}}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --generator)
      GENERATOR_MODEL="$2"
      shift 2
      ;;
    --reflector)
      REFLECTOR_MODEL="$2"
      shift 2
      ;;
    --curator)
      CURATOR_MODEL="$2"
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
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

default_config_slug="${PROVIDER}-mixed-strong-reflector"
default_config_name="ace_mixed_strong_reflector_appworld_subset"

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
  --generator "${GENERATOR_MODEL}"
  --reflector "${REFLECTOR_MODEL}"
  --curator "${CURATOR_MODEL}"
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