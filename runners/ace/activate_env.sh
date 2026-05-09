#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   source runners/ace/activate_env.sh
#
# Supported selectors:
#   VENV_PATH=/path/to/venv
#   MAMBA_ENV=env-name
#   CONDA_ENV_NAME=env-name
#
# If no selector is set, this script keeps the current Python environment.

if [[ -n "${VENV_PATH:-}" ]]; then
  # shellcheck disable=SC1090
  source "${VENV_PATH}/bin/activate"
  return 0
fi

ENV_NAME="${MAMBA_ENV:-${CONDA_ENV_NAME:-}}"
if [[ -z "${ENV_NAME}" ]]; then
  return 0
fi

if command -v micromamba >/dev/null 2>&1; then
  eval "$(micromamba shell hook --shell bash)"
  micromamba activate "${ENV_NAME}"
  return 0
fi

CONDA_SH=""
if [[ -n "${CONDA_EXE:-}" ]]; then
  CONDA_SH="$(cd "$(dirname "${CONDA_EXE}")/.." && pwd)/etc/profile.d/conda.sh"
elif command -v conda >/dev/null 2>&1; then
  CONDA_SH="$(conda info --base)/etc/profile.d/conda.sh"
elif command -v mamba >/dev/null 2>&1; then
  MAMBA_BIN="$(command -v mamba)"
  CONDA_SH="$(cd "$(dirname "${MAMBA_BIN}")/.." && pwd)/etc/profile.d/conda.sh"
fi

if [[ -z "${CONDA_SH}" || ! -f "${CONDA_SH}" ]]; then
  cat >&2 <<'EOF'
Could not find conda/mamba shell initialization for environment activation.
Set VENV_PATH to a virtualenv, or ensure conda/mamba is installed and initialized.
EOF
  return 1
fi

# shellcheck disable=SC1090
source "${CONDA_SH}"
conda activate "${ENV_NAME}"
