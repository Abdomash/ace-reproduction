#!/usr/bin/env bash
set -euo pipefail

# One-time host bootstrap for representative ACE runner jobs on SLURM.
#
# Examples:
#   runners/ace/setup_cluster_env.sh
#   ENV_NAME=ace-repr-runner PYTHON_VERSION=3.11 runners/ace/setup_cluster_env.sh
#   ENV_NAME=ace-repr-runner APPWORLD_VERIFY=0 runners/ace/setup_cluster_env.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_NAME="${ENV_NAME:-ace-repr-runner}"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
APPWORLD_DOWNLOAD_DATA="${APPWORLD_DOWNLOAD_DATA:-1}"
APPWORLD_VERIFY="${APPWORLD_VERIFY:-1}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

detect_env_manager() {
  if command -v micromamba >/dev/null 2>&1; then
    echo "micromamba"
    return
  fi
  if command -v mamba >/dev/null 2>&1; then
    echo "mamba"
    return
  fi
  if command -v conda >/dev/null 2>&1; then
    echo "conda"
    return
  fi
  echo ""
}

ENV_MANAGER="$(detect_env_manager)"
if [[ -z "${ENV_MANAGER}" ]]; then
  cat >&2 <<'EOF'
No conda-compatible environment manager found.
Install one of: micromamba, mamba, or conda, then rerun this script.
EOF
  exit 1
fi

require_command git
require_command git-lfs

echo "Using environment manager: ${ENV_MANAGER}"
echo "Bootstrapping environment: ${ENV_NAME}"

case "${ENV_MANAGER}" in
  micromamba)
    if ! micromamba env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
      micromamba create -y -n "${ENV_NAME}" "python=${PYTHON_VERSION}"
    fi
    export MAMBA_ENV="${ENV_NAME}"
    ;;
  mamba)
    if ! mamba env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
      mamba create -y -n "${ENV_NAME}" "python=${PYTHON_VERSION}"
    fi
    export MAMBA_ENV="${ENV_NAME}"
    ;;
  conda)
    if ! conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
      conda create -y -n "${ENV_NAME}" "python=${PYTHON_VERSION}"
    fi
    export CONDA_ENV_NAME="${ENV_NAME}"
    ;;
esac

# shellcheck disable=SC1091
source "${REPO_ROOT}/runners/ace/activate_env.sh"

cd "${REPO_ROOT}"

git lfs install
git lfs pull

python -m pip install --upgrade pip setuptools wheel
python -m pip install -e "projects/maestro[telemetry]"
python -m pip install -e "projects/ace"
python -m pip install -e "projects/ace-appworld"
python -m pip install -e "projects/ace-appworld/experiments[simplified]"

export APPWORLD_PROJECT_PATH="${REPO_ROOT}/projects/ace-appworld"
python -m appworld.cli install --repo
if [[ "${APPWORLD_DOWNLOAD_DATA}" == "1" ]]; then
  python -m appworld.cli download data --root "${APPWORLD_PROJECT_PATH}"
fi
if [[ "${APPWORLD_VERIFY}" == "1" ]]; then
  python -m appworld.cli verify tests --root "${APPWORLD_PROJECT_PATH}"
  python -m appworld.cli verify tasks --root "${APPWORLD_PROJECT_PATH}"
fi

if [[ ! -f "${REPO_ROOT}/.env" ]]; then
  cat <<'EOF'

Reminder: create the repository root .env with the provider keys you need, for example:

  OPENROUTER_API_KEY=...
  OPENAI_API_KEY=...
  TOGETHER_API_KEY=...
  SAMBANOVA_API_KEY=...
EOF
fi

cat <<EOF

Cluster environment setup complete.

Recommended SLURM usage:
  MAMBA_ENV=${ENV_NAME} sbatch runners/ace/slurm/ace_repr_finer_launch.sbatch
  MAMBA_ENV=${ENV_NAME} sbatch runners/ace/slurm/ace_repr_appworld_launch.sbatch
  MAMBA_ENV=${ENV_NAME} sbatch runners/ace/slurm/ace_repr_resume.sbatch

If you use plain conda instead of mamba:
  CONDA_ENV_NAME=${ENV_NAME} sbatch runners/ace/slurm/ace_repr_finer_launch.sbatch
EOF
