from typing import Any, Dict, List, Tuple

from .react_agent import AppWorldReActAgent
from logger import log_bullet_usage
from playbook_utils import get_playbook_stats, update_bullet_counts


class AppWorldTaskAdapter:
    """Task adapter that runs AppWorld episodes and computes compatible metrics."""

    def __init__(
        self, ace_system, data_processor, config: Dict[str, Any], log_dir: str
    ):
        self.ace = ace_system
        self.data_processor = data_processor
        self.config = config
        self.log_dir = log_dir
        self.agent = AppWorldReActAgent(
            ace_system.generator, config=config, log_dir=log_dir
        )

    def _prediction_from_result(self, result: Dict[str, Any]) -> str:
        evaluation = result.get("evaluation", {})
        if isinstance(evaluation, dict):
            for key in [
                "task_goal_completion",
                "tgc",
                "passed",
                "success",
                "completed",
            ]:
                if key in evaluation:
                    return "true" if bool(evaluation[key]) else "false"
        return "true" if result.get("task_completed", False) else "false"

    def _scenario_ids(self, samples: List[Dict[str, Any]]) -> List[str]:
        ids: List[str] = []
        for sample in samples:
            others = sample.get("others", {})
            scenario_id = (
                others.get("scenario_id")
                or others.get("task_id")
                or sample.get("target", "")
            )
            ids.append(str(scenario_id))
        return ids

    def run_test(
        self, samples: List[Dict[str, Any]], playbook: str, prefix: str
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        answers: List[str] = []
        targets: List[str] = []
        detailed: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        for i, sample in enumerate(samples):
            task_id = sample.get("others", {}).get("task_id") or sample.get(
                "target", ""
            )
            call_prefix = f"{prefix}_task_{i}_{task_id}"
            try:
                result = self.agent.solve_task(
                    sample=sample, playbook=playbook, call_prefix=call_prefix
                )
                pred = self._prediction_from_result(result)
                answers.append(pred)
                targets.append("true")
                detailed.append(
                    {
                        "index": i,
                        "task_id": task_id,
                        "prediction": pred,
                        "task_completed": result.get("task_completed", False),
                        "evaluation": result.get("evaluation", {}),
                        "final_error": result.get("final_error", ""),
                    }
                )
                if not self.data_processor.answer_is_correct(pred, "true"):
                    errors.append(
                        {
                            "index": i,
                            "prediction": pred,
                            "ground_truth": "true",
                        }
                    )
            except Exception as exc:
                answers.append("false")
                targets.append("true")
                errors.append(
                    {
                        "index": i,
                        "prediction": "false",
                        "ground_truth": "true",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

        metrics = self.data_processor.evaluate_metrics(
            answers,
            targets,
            scenario_ids=self._scenario_ids(samples),
        )

        results = {
            "accuracy": float(metrics.get("accuracy", 0.0)),
            "correct": sum(
                1
                for a, t in zip(answers, targets)
                if self.data_processor.answer_is_correct(a, t)
            ),
            "total": len(samples),
            "tgc": float(metrics.get("tgc", 0.0)),
            "sgc": float(metrics.get("sgc", 0.0)),
            "num_tasks": int(metrics.get("num_tasks", len(samples))),
            "num_scenarios": int(metrics.get("num_scenarios", len(samples))),
            "details": detailed,
        }
        return results, {"accuracy": results["accuracy"], "errors": errors}

    def train_single_sample(
        self,
        task_dict: Dict[str, Any],
        step_id: str,
        usage_log_path: str,
        config_params: Dict[str, Any],
        step: int,
        epoch: int,
        total_samples: int,
    ):
        token_budget = config_params["token_budget"]
        no_ground_truth = config_params["no_ground_truth"]
        use_json_mode = config_params["use_json_mode"]

        target = task_dict.get("target", "true")
        task_identifier = task_dict.get("others", {}).get("task_id", "")

        pre_result = self.agent.solve_task(
            task_dict, self.ace.playbook, f"{step_id}_pre"
        )
        pre_answer = self._prediction_from_result(pre_result)
        pre_correct = self.data_processor.answer_is_correct(pre_answer, target)

        tracking_dict = {
            "pre_train_result": {
                "final_answer": pre_answer,
                "is_correct": pre_correct,
                "playbook_num_tokens": len(self.ace.playbook),
                "playbook_length": len(self.ace.playbook),
                "task_completed": pre_result.get("task_completed", False),
            }
        }

        reflection_content = "(empty)"
        if not pre_correct:
            trace_summary = str(pre_result.get("execution_trace", []))
            env_feedback = pre_result.get("final_error") or str(
                pre_result.get("evaluation", {})
            )
            reflection_content, bullet_tags, _ = self.ace._invoke_agent(
                "reflector",
                {
                    "step_id": step_id,
                    "phase": "appworld_reflect_error",
                    "task_id": task_identifier,
                },
                lambda: self.ace.reflector.reflect(
                    question=task_dict.get("question", ""),
                    reasoning_trace=trace_summary,
                    predicted_answer=pre_answer,
                    ground_truth=target if not no_ground_truth else None,
                    environment_feedback=env_feedback,
                    bullets_used="(AppWorld execution trace)",
                    use_ground_truth=not no_ground_truth,
                    use_json_mode=use_json_mode,
                    task_type="appworld",
                    call_id=f"{step_id}_app_reflect",
                    log_dir=self.log_dir,
                ),
            )

            if bullet_tags:
                self.ace.playbook = update_bullet_counts(self.ace.playbook, bullet_tags)

            stats = get_playbook_stats(self.ace.playbook)
            self.ace.playbook, self.ace.next_global_id, _, _ = self.ace._invoke_agent(
                "curator",
                {
                    "step_id": step_id,
                    "phase": "appworld_curate",
                    "task_id": task_identifier,
                },
                lambda: self.ace.curator.curate(
                    current_playbook=self.ace.playbook,
                    recent_reflection=reflection_content,
                    question_context=task_dict.get("context", ""),
                    current_step=step,
                    total_samples=total_samples,
                    token_budget=token_budget,
                    playbook_stats=stats,
                    use_ground_truth=not no_ground_truth,
                    use_json_mode=use_json_mode,
                    task_type="appworld",
                    call_id=f"{step_id}_app_curate",
                    log_dir=self.log_dir,
                    next_global_id=self.ace.next_global_id,
                ),
            )

        post_result = self.agent.solve_task(
            task_dict, self.ace.playbook, f"{step_id}_post"
        )
        post_answer = self._prediction_from_result(post_result)
        post_correct = self.data_processor.answer_is_correct(post_answer, target)
        tracking_dict["post_train_result"] = {
            "final_answer": post_answer,
            "is_correct": post_correct,
            "playbook_num_tokens": len(self.ace.playbook),
            "playbook_length": len(self.ace.playbook),
            "task_completed": post_result.get("task_completed", False),
        }

        log_bullet_usage(
            usage_log_path,
            epoch,
            step,
            task_dict,
            bullet_ids_used=[],
            playbook=self.ace.playbook,
            reflection_content=reflection_content,
            is_correct=post_correct,
        )

        return pre_answer, post_answer, tracking_dict
