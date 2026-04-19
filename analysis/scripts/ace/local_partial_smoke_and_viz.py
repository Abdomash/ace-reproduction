#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt

from _provenance import (
    finalize_output,
    existing_file_records,
    output_dir_for,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
ACE_ROOT = REPO_ROOT / "projects" / "ace"
if str(ACE_ROOT) not in sys.path:
    sys.path.insert(0, str(ACE_ROOT))

from ace import ACE


@dataclass
class RunArtifacts:
    run_dir: Path
    trace_path: Path
    metrics_path: Path
    llm_log_dir: Path
    summary_path: Path
    plots_dir: Path


class DummyProcessor:
    def answer_is_correct(self, pred: str, target: str) -> bool:
        return str(pred).strip() == str(target).strip()

    def evaluate_accuracy(self, answers: List[str], targets: List[str]) -> float:
        if not answers:
            return 0.0
        total = min(len(answers), len(targets))
        if total == 0:
            return 0.0
        correct = sum(
            self.answer_is_correct(answers[i], targets[i]) for i in range(total)
        )
        return correct / total


class FakeCompletions:
    def create(self, **kwargs: Any) -> Any:
        prompt = kwargs.get("messages", [{}])[0].get("content", "")
        prompt_tokens = max(1, len(prompt) // 8)
        response_payload = {
            "final_answer": "A",
            "bullet_ids": [],
            "reflection": "No correction needed.",
            "bullet_tags": [],
            "reasoning": "Keep playbook unchanged for this synthetic smoke run.",
            "operations": [],
        }
        response_text = json.dumps(response_payload)
        completion_tokens = max(1, len(response_text) // 8)
        usage = SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        message = SimpleNamespace(content=response_text)
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice], usage=usage)


class FakeClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions())


def _replace_clients_with_fakes(ace_system: ACE) -> None:
    generator_client = FakeClient()
    reflector_client = FakeClient()
    curator_client = FakeClient()

    ace_system.generator_client = generator_client
    ace_system.reflector_client = reflector_client
    ace_system.curator_client = curator_client
    ace_system.generator.api_client = generator_client
    ace_system.reflector.api_client = reflector_client
    ace_system.curator.api_client = curator_client


def _collect_run_artifacts(run_root: Path, analysis_output_dir: Path) -> RunArtifacts:
    run_dirs = sorted(
        [p for p in run_root.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime
    )
    if not run_dirs:
        raise RuntimeError(f"No run directory created under {run_root}")
    run_dir = run_dirs[-1]

    run_config = json.loads((run_dir / "run_config.json").read_text())
    telemetry = run_config.get("telemetry", {})

    trace_path = Path(str(telemetry.get("trace_path", "")))
    metrics_path = Path(str(telemetry.get("metrics_path", "")))
    llm_log_dir = run_dir / "detailed_llm_logs"
    plots_dir = analysis_output_dir / "plots"
    summary_path = analysis_output_dir / "reports" / "summary.json"

    plots_dir.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    return RunArtifacts(
        run_dir=run_dir,
        trace_path=trace_path,
        metrics_path=metrics_path,
        llm_log_dir=llm_log_dir,
        plots_dir=plots_dir,
        summary_path=summary_path,
    )


def _load_jsonl_dicts(path: Path) -> List[Dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _load_metrics(path: Path) -> List[Tuple[str, float, float]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    metrics: List[Tuple[str, float, float]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if not isinstance(payload, list):
                continue
            for item in payload:
                name = item.get("metric_name")
                data_points = item.get("data_points") or []
                if not name or not data_points:
                    continue
                point = data_points[0]
                ts = float(point.get("timestamp", 0))
                val = float(point.get("value", 0))
                metrics.append((str(name), ts, val))
    return metrics


def _load_llm_logs(log_dir: Path) -> List[Dict[str, Any]]:
    if not log_dir.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for file in sorted(log_dir.glob("*.json")):
        try:
            rows.append(json.loads(file.read_text(encoding="utf-8")))
        except Exception:
            continue
    return rows


def _plot_operation_counts(spans: List[Dict[str, Any]], output: Path) -> Dict[str, int]:
    op_counts: Counter[str] = Counter()
    for s in spans:
        attrs = s.get("attributes") or {}
        op = attrs.get("gen_ai.operation.name", "unknown")
        op_counts[str(op)] += 1

    labels = list(op_counts.keys())
    values = [op_counts[l] for l in labels]

    plt.figure(figsize=(7, 4))
    plt.bar(
        labels,
        values,
        color=["#4e79a7", "#e15759", "#76b041", "#9c755f"][: len(labels)],
    )
    plt.title("Span Operation Counts")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(output)
    plt.close()

    return dict(op_counts)


def _plot_duration_by_agent_and_operation(
    spans: List[Dict[str, Any]], output: Path
) -> Dict[str, Dict[str, float]]:
    table: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    agents: List[str] = []
    operations: List[str] = []

    for s in spans:
        attrs = s.get("attributes") or {}
        agent = str(attrs.get("agent.name") or s.get("agent_name") or "unknown")
        op = str(attrs.get("gen_ai.operation.name") or "unknown")
        dur_s = float(s.get("duration_ns", 0)) / 1e9
        table[agent][op] += dur_s
        if agent not in agents:
            agents.append(agent)
        if op not in operations:
            operations.append(op)

    if not agents or not operations:
        plt.figure(figsize=(7, 4))
        plt.title("Duration by Agent and Operation")
        plt.text(0.5, 0.5, "No span data", ha="center", va="center")
        plt.tight_layout()
        plt.savefig(output)
        plt.close()
        return {}

    bottoms = [0.0] * len(agents)
    x = list(range(len(agents)))

    plt.figure(figsize=(9, 4.5))
    palette = ["#4e79a7", "#e15759", "#76b041", "#9c755f", "#59a14f"]
    for idx, op in enumerate(operations):
        vals = [table[a].get(op, 0.0) for a in agents]
        plt.bar(x, vals, bottom=bottoms, label=op, color=palette[idx % len(palette)])
        bottoms = [bottoms[i] + vals[i] for i in range(len(vals))]

    plt.xticks(x, agents)
    plt.ylabel("Total Duration (s)")
    plt.title("Duration by Agent and Operation")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output)
    plt.close()

    return {a: dict(v) for a, v in table.items()}


def _plot_tokens_by_role(
    llm_rows: List[Dict[str, Any]], output: Path
) -> Dict[str, int]:
    totals: Counter[str] = Counter()
    for row in llm_rows:
        role = str(row.get("role", "unknown"))
        total_tokens = int(
            row.get("total_num_tokens")
            or (
                int(row.get("prompt_num_tokens", 0))
                + int(row.get("response_num_tokens", 0))
            )
        )
        totals[role] += total_tokens

    labels = list(totals.keys())
    values = [totals[k] for k in labels]

    plt.figure(figsize=(7, 4))
    plt.bar(
        labels,
        values,
        color=["#4e79a7", "#e15759", "#76b041", "#9c755f"][: len(labels)],
    )
    plt.title("LLM Tokens by Role")
    plt.ylabel("Total Tokens")
    plt.tight_layout()
    plt.savefig(output)
    plt.close()
    return dict(totals)


def _plot_cpu_memory_timeline(
    metrics: List[Tuple[str, float, float]], output: Path
) -> Dict[str, float]:
    cpu_points = [(ts, val) for name, ts, val in metrics if name == "process.cpu.usage"]
    mem_points = [
        (ts, val) for name, ts, val in metrics if name == "process.memory.usage_bytes"
    ]

    if not cpu_points and not mem_points:
        plt.figure(figsize=(8, 4))
        plt.title("CPU and Memory Timeline")
        plt.text(0.5, 0.5, "No metrics data", ha="center", va="center")
        plt.tight_layout()
        plt.savefig(output)
        plt.close()
        return {"avg_cpu_pct": 0.0, "peak_mem_mb": 0.0}

    ts0 = (
        min([p[0] for p in cpu_points + mem_points])
        if (cpu_points or mem_points)
        else 0.0
    )
    cpu_x = [(ts - ts0) / 1e9 for ts, _ in cpu_points]
    cpu_y = [v for _, v in cpu_points]
    mem_x = [(ts - ts0) / 1e9 for ts, _ in mem_points]
    mem_y = [v / (1024 * 1024) for _, v in mem_points]

    fig, ax1 = plt.subplots(figsize=(9, 4.5))
    ax1.plot(cpu_x, cpu_y, color="#4e79a7", label="CPU %")
    ax1.set_xlabel("Elapsed Time (s)")
    ax1.set_ylabel("CPU Usage (%)", color="#4e79a7")
    ax1.tick_params(axis="y", labelcolor="#4e79a7")

    ax2 = ax1.twinx()
    ax2.plot(mem_x, mem_y, color="#e15759", label="Memory MB")
    ax2.set_ylabel("Memory Usage (MB)", color="#e15759")
    ax2.tick_params(axis="y", labelcolor="#e15759")

    plt.title("CPU and Memory Timeline")
    fig.tight_layout()
    plt.savefig(output)
    plt.close(fig)

    avg_cpu = sum(cpu_y) / len(cpu_y) if cpu_y else 0.0
    peak_mem = max(mem_y) if mem_y else 0.0
    return {"avg_cpu_pct": avg_cpu, "peak_mem_mb": peak_mem}


def run_partial_smoke_and_visualize(output_root: Path, analysis_output_dir: Path) -> RunArtifacts:
    os.environ.setdefault("OPENAI_API_KEY", "dummy-key")

    ace_system = ACE(
        api_provider="openai",
        generator_model="gpt-oss:20b",
        reflector_model="gpt-oss:20b",
        curator_model="gpt-oss:20b",
        max_tokens=256,
    )
    _replace_clients_with_fakes(ace_system)

    train_samples = [
        {"question": "Q1", "context": "C1", "target": "A"},
        {"question": "Q2", "context": "C2", "target": "A"},
        {"question": "Q3", "context": "C3", "target": "A"},
    ]
    val_samples = [
        {"question": "V1", "context": "VC1", "target": "A"},
        {"question": "V2", "context": "VC2", "target": "A"},
    ]
    test_samples = [
        {"question": "T1", "context": "TC1", "target": "A"},
        {"question": "T2", "context": "TC2", "target": "A"},
    ]

    config = {
        "task_name": "finer",
        "num_epochs": 1,
        "max_num_rounds": 1,
        "curator_frequency": 1,
        "eval_steps": 1,
        "save_steps": 5,
        "playbook_token_budget": 3000,
        "json_mode": False,
        "no_ground_truth": False,
        "save_dir": str(output_root),
        "test_workers": 1,
        "telemetry_enabled": True,
        "telemetry_metrics_interval_seconds": 1,
        "seed": 42,
        "config_name": "partial_local_viz",
    }

    processor = DummyProcessor()
    ace_system.run(
        mode="offline",
        train_samples=train_samples,
        val_samples=val_samples,
        test_samples=test_samples,
        data_processor=processor,
        config=config,
    )

    artifacts = _collect_run_artifacts(output_root, analysis_output_dir)

    spans = _load_jsonl_dicts(artifacts.trace_path)
    metrics = _load_metrics(artifacts.metrics_path)
    llm_rows = _load_llm_logs(artifacts.llm_log_dir)

    op_counts = _plot_operation_counts(spans, artifacts.plots_dir / "op_counts.png")
    duration_table = _plot_duration_by_agent_and_operation(
        spans,
        artifacts.plots_dir / "duration_by_agent_operation.png",
    )
    tokens_by_role = _plot_tokens_by_role(
        llm_rows, artifacts.plots_dir / "tokens_by_role.png"
    )
    cpu_mem_stats = _plot_cpu_memory_timeline(
        metrics, artifacts.plots_dir / "cpu_mem_timeline.png"
    )

    final_results = json.loads((artifacts.run_dir / "final_results.json").read_text())
    core_results = final_results.get("results", {})

    summary = {
        "run_dir": str(artifacts.run_dir),
        "trace_path": str(artifacts.trace_path),
        "metrics_path": str(artifacts.metrics_path),
        "llm_log_dir": str(artifacts.llm_log_dir),
        "plots_dir": str(artifacts.plots_dir),
        "span_count": len(spans),
        "llm_call_count": len(llm_rows),
        "operation_counts": op_counts,
        "duration_by_agent_operation_seconds": duration_table,
        "tokens_by_role": tokens_by_role,
        "resource_stats": cpu_mem_stats,
        "accuracy": {
            "initial_test": (core_results.get("initial_test_results") or {}).get(
                "accuracy"
            ),
            "final_test": (core_results.get("final_test_results") or {}).get(
                "accuracy"
            ),
            "best_validation": (core_results.get("training_results") or {}).get(
                "best_validation_accuracy"
            ),
        },
    }
    artifacts.summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return artifacts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run local partial ACE smoke and generate visualization artifacts."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPO_ROOT / "results" / "local_partial_run",
        help="Directory where the smoke run output folder will be created.",
    )
    parser.add_argument(
        "--analysis-output-dir",
        type=Path,
        default=None,
        help="Analysis output directory (default: analysis/outputs/<analysis_id>)",
    )
    args = parser.parse_args()

    analysis_id, created_at, analysis_output_dir = output_dir_for(
        "local_partial_viz",
        "local_partial_run",
        args.analysis_output_dir,
    )
    args.output_root.mkdir(parents=True, exist_ok=True)
    analysis_output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = run_partial_smoke_and_visualize(args.output_root, analysis_output_dir)

    input_records = existing_file_records(
        [
            (artifacts.run_dir / "run_config.json", "run_config"),
            (artifacts.run_dir / "final_results.json", "final_results"),
            (artifacts.trace_path, "telemetry_trace"),
            (artifacts.metrics_path, "telemetry_metrics"),
            *[(path, "llm_log") for path in sorted(artifacts.llm_log_dir.glob("*.json"))],
        ]
    )
    plot_outputs = [
        path.relative_to(analysis_output_dir).as_posix()
        for path in sorted(artifacts.plots_dir.glob("*.png"))
    ]
    finalize_output(
        analysis_output_dir,
        analysis_id=analysis_id,
        analysis_kind="local_partial_viz",
        label="local_partial_run",
        created_at=created_at,
        command="python " + " ".join(sys.argv),
        parameters={"output_root": str(args.output_root)},
        input_records=input_records,
        outputs=[artifacts.summary_path.relative_to(analysis_output_dir).as_posix(), *plot_outputs],
    )

    print("PARTIAL_LOCAL_VIZ_OK")
    print(f"run_dir={artifacts.run_dir}")
    print(f"summary={artifacts.summary_path}")
    print(f"plots_dir={artifacts.plots_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
