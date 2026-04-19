#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   runners/ace/setup_appworld.sh
#   APPWORLD_COMMIT=<sha> runners/ace/setup_appworld.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
APPWORLD_DIR="${APPWORLD_DIR:-${REPO_ROOT}/projects/ace-appworld}"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required" >&2
  exit 1
fi

git lfs install

if [ ! -d "${APPWORLD_DIR}" ]; then
  : "${APPWORLD_COMMIT:?Set APPWORLD_COMMIT to clone ace-appworld when APPWORLD_DIR does not exist}"
  git clone https://github.com/ace-agent/ace-appworld.git "${APPWORLD_DIR}"
fi

if [ -n "${APPWORLD_COMMIT:-}" ]; then
  git -C "${APPWORLD_DIR}" fetch --all --tags
  git -C "${APPWORLD_DIR}" checkout "${APPWORLD_COMMIT}"
fi

export APPWORLD_PROJECT_PATH="${APPWORLD_DIR}"

if command -v uv >/dev/null 2>&1; then
  uv venv --python 3.11 --clear --seed "${APPWORLD_DIR}/.venv"
else
  if ! python3.11 -m venv --clear "${APPWORLD_DIR}/.venv"; then
    cat >&2 <<'EOF'
Failed to create the AppWorld virtualenv with python3.11 -m venv.

If python3.11 comes from uv, install/use uv and rerun this script. Otherwise,
make sure the system venv package is installed, for example:

  sudo apt-get install python3.11-venv
EOF
    exit 1
  fi
fi

APPWORLD_PY="${APPWORLD_DIR}/.venv/bin/python"
if [ ! -x "${APPWORLD_PY}" ]; then
  echo "Expected virtualenv Python at ${APPWORLD_PY}" >&2
  exit 1
fi

"${APPWORLD_PY}" -m pip install --upgrade pip setuptools wheel
"${APPWORLD_PY}" -m pip install -e "${APPWORLD_DIR}"
"${APPWORLD_PY}" -m pip install -e "${APPWORLD_DIR}/experiments[simplified]"
(
  cd "${APPWORLD_DIR}"
  "${APPWORLD_PY}" -m appworld.cli install --repo
  "${APPWORLD_PY}" -m appworld.cli download data --root "${APPWORLD_DIR}"
  "${APPWORLD_PY}" -m appworld.cli verify tests --root "${APPWORLD_DIR}"
  "${APPWORLD_PY}" -m appworld.cli verify tasks --root "${APPWORLD_DIR}"
)

echo "AppWorld setup complete at ${APPWORLD_DIR}"
