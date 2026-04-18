#!/bin/bash --login
#SBATCH --job-name=ace_local_noapi_smoke
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --qos=normal
#SBATCH --time=00:10:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4GB

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ -n "${VENV_PATH:-}" ]; then
  source "${VENV_PATH}/bin/activate"
elif [ -n "${MAMBA_ENV:-}" ]; then
  mamba activate "${MAMBA_ENV}"
fi

export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"
export OPENAI_API_KEY="dummy-key"

python - <<'PY'
import json
import tempfile
from pathlib import Path

from ace import ACE


class DummyProcessor:
    def answer_is_correct(self, pred, target):
        return pred == target

    def evaluate_accuracy(self, answers, targets):
        if not answers:
            return 0.0
        return sum(a == b for a, b in zip(answers, targets)) / len(answers)


out_dir = Path(tempfile.mkdtemp(prefix="ace_slurm_smoke_", dir="/tmp"))

ace_system = ACE(
    api_provider="openai",
    generator_model="gpt-oss:20b",
    reflector_model="gpt-oss:20b",
    curator_model="gpt-oss:20b",
    max_tokens=128,
)

config = {
    "task_name": "finer",
    "num_epochs": 1,
    "max_num_rounds": 1,
    "curator_frequency": 1,
    "eval_steps": 10,
    "save_steps": 10,
    "playbook_token_budget": 1000,
    "json_mode": False,
    "no_ground_truth": False,
    "save_dir": str(out_dir),
    "test_workers": 1,
    "api_provider": "openai",
    "telemetry_enabled": True,
    "telemetry_metrics_interval_seconds": 1,
    "seed": 42,
    "config_name": "slurm_noapi_smoke",
}

results = ace_system.run(
    mode="offline",
    train_samples=[],
    val_samples=[],
    test_samples=None,
    data_processor=DummyProcessor(),
    config=config,
)

run_dir = next(p for p in out_dir.iterdir() if p.is_dir())
run_config = json.loads((run_dir / "run_config.json").read_text())
final_results = json.loads((run_dir / "final_results.json").read_text())

telemetry = run_config.get("telemetry", {})
assert run_config.get("run_id", "").startswith("ace_finer_offline_"), run_config.get("run_id")
assert telemetry.get("enabled") is True, telemetry
assert Path(telemetry.get("trace_path", "")).exists(), telemetry
assert Path(telemetry.get("metrics_path", "")).exists(), telemetry
assert "training_results" in final_results, final_results.keys()
assert "results" in final_results, final_results.keys()
assert "training_results" in results, results.keys()

print("SLURM_SMOKE_OK")
print(f"run_dir={run_dir}")
print(f"run_id={run_config.get('run_id')}")
print(f"trace_path={telemetry.get('trace_path')}")
print(f"metrics_path={telemetry.get('metrics_path')}")
PY
