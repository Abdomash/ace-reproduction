#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Add OPENROUTER_API_KEY=... to that file." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "OPENROUTER_API_KEY is not set in ${ENV_FILE}." >&2
  exit 1
fi

# The current ACE runner does not expose an explicit OpenRouter provider yet.
# Reuse its OpenAI-compatible MiniMax provider path with OpenRouter credentials.
export MINIMAX_API_KEY="${OPENROUTER_API_KEY}"
export MINIMAX_BASE_URL="${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}"

cd "${PROJECT_ROOT}/ace"

./scripts/run_experiments.sh finer_subset \
  --provider minimax \
  --generator openai/gpt-oss-20b:nitro \
  --reflector openai/gpt-oss-20b:nitro \
  --curator openai/gpt-oss-20b:nitro \
  --config-name "${CONFIG_NAME:-ace_all_gptoss20b_subset_smoke}" \
  --save-path "${SAVE_PATH:-../results/openrouter_gptoss20b_smoke}" \
  --seed "${SEED:-42}" \
  --mode "${MODE:-offline}" \
  --eval-steps "${EVAL_STEPS:-15}" \
  --telemetry "${TELEMETRY:-1}" \
  --telemetry-interval "${TELEMETRY_INTERVAL:-5}" \
  "$@"
