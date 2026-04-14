#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   APPWORLD_COMMIT=<sha> ./scripts/setup_appworld.sh

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APPWORLD_DIR="${REPO_ROOT}/../ace-appworld"

: "${APPWORLD_COMMIT:?Set APPWORLD_COMMIT to a pinned ace-appworld commit SHA}"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required" >&2
  exit 1
fi

git lfs install

if [ ! -d "${APPWORLD_DIR}" ]; then
  git clone https://github.com/ace-agent/ace-appworld.git "${APPWORLD_DIR}"
fi

git -C "${APPWORLD_DIR}" fetch --all --tags
git -C "${APPWORLD_DIR}" checkout "${APPWORLD_COMMIT}"

export APPWORLD_PROJECT_PATH="${APPWORLD_DIR}"

python3.11 -m venv "${APPWORLD_DIR}/.venv"
# shellcheck disable=SC1091
source "${APPWORLD_DIR}/.venv/bin/activate"

pip install -e "${APPWORLD_DIR}"
pip install -e "${APPWORLD_DIR}/experiments[simplified]"
appworld install --repo
appworld download data
appworld verify tests
appworld verify tasks

echo "AppWorld setup complete at ${APPWORLD_DIR} (commit ${APPWORLD_COMMIT})"
