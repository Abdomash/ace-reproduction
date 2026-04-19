import json
import os
from typing import Any, Dict, List


def load_data(data_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data file not found: {data_path}")

    data: List[Dict[str, Any]] = []
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))

    print(f"Loaded {len(data)} samples from {data_path}")
    return data


class DataProcessor:
    """Processor for AppWorld tasks and metrics aggregation."""

    def __init__(self, task_name: str):
        self.task_name = task_name

    def process_task_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        processed: List[Dict[str, Any]] = []
        for item in raw_data:
            instruction = item.get("instruction", "")
            task_id = item.get("task_id", "")

            others = {
                "task_id": task_id,
                "dataset_name": item.get("dataset_name", ""),
                "difficulty": item.get("difficulty"),
                "supervisor": item.get("supervisor", {}),
                "app_descriptions": item.get("app_descriptions", {}),
                "scenario_id": item.get("scenario_id"),
                "task": self.task_name,
            }

            processed.append(
                {
                    "context": json.dumps(
                        {
                            "supervisor": others["supervisor"],
                            "app_descriptions": others["app_descriptions"],
                        },
                        ensure_ascii=True,
                    ),
                    "question": instruction,
                    "target": "true",
                    "others": others,
                }
            )
        return processed

    def answer_is_correct(self, predicted: str, ground_truth: str) -> bool:
        pred = (predicted or "").strip().lower()
        gt = (ground_truth or "").strip().lower()

        if pred in {"", "no final answer found"}:
            return False

        positive = {"1", "true", "pass", "passed", "success", "succeeded"}
        negative = {"0", "false", "fail", "failed", "error"}

        if pred in positive:
            return True
        if pred in negative:
            return False
        return pred == gt

    def evaluate_accuracy(self, out: List[str], target: List[str]) -> float:
        if len(out) != len(target):
            raise ValueError(
                "Input lists 'out' and 'target' must have the same length."
            )
        if not out:
            return 0.0
        correct = sum(
            1
            for predicted, gt in zip(out, target)
            if self.answer_is_correct(predicted, gt)
        )
        return correct / len(out)

    def evaluate_metrics(
        self,
        out: List[str],
        target: List[str],
        scenario_ids: List[str] | None = None,
    ) -> Dict[str, Any]:
        tgc = self.evaluate_accuracy(out, target)

        if not scenario_ids or len(scenario_ids) != len(out):
            return {
                "tgc": tgc,
                "sgc": tgc,
                "num_tasks": len(out),
                "num_scenarios": len(set(scenario_ids or [])),
                "accuracy": tgc,
            }

        by_scenario: Dict[str, List[bool]] = {}
        for predicted, gt, scenario_id in zip(out, target, scenario_ids):
            key = str(scenario_id)
            by_scenario.setdefault(key, []).append(
                self.answer_is_correct(predicted, gt)
            )

        scenario_successes = [all(flags) for flags in by_scenario.values()]
        sgc = (
            sum(1 for ok in scenario_successes if ok) / len(scenario_successes)
            if scenario_successes
            else 0.0
        )

        return {
            "tgc": tgc,
            "sgc": sgc,
            "num_tasks": len(out),
            "num_scenarios": len(by_scenario),
            "accuracy": tgc,
        }
