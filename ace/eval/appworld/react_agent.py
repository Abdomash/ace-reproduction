import importlib
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from jinja2 import Template


class AppWorldReActAgent:
    """ReAct-style AppWorld task solver using ACE's generator interface."""

    def __init__(
        self,
        generator,
        config: Dict[str, Any],
        log_dir: Optional[str] = None,
    ):
        self.generator = generator
        self.config = config
        self.log_dir = log_dir
        self.max_steps = int(config.get("max_agent_steps", 30))
        self.max_prompt_length = config.get("max_prompt_length")
        self.ignore_multiple_calls = bool(config.get("ignore_multiple_calls", False))
        self._appworld_root = config.get("appworld_root")
        self._world_class = None

        prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
        with open(
            os.path.join(prompts_dir, "generator.txt"), "r", encoding="utf-8"
        ) as f:
            self.generator_template = f.read()

    def _load_world_class(self):
        if self._world_class is not None:
            return self._world_class

        if self._appworld_root:
            expanded = os.path.expanduser(self._appworld_root)
            if os.path.isdir(expanded):
                repo_src = os.path.join(expanded, "src")
                if repo_src not in os.sys.path and os.path.isdir(repo_src):
                    os.sys.path.insert(0, repo_src)
                if expanded not in os.sys.path:
                    os.sys.path.insert(0, expanded)

        module_candidates = [
            "appworld.world",
            "appworld.environment.world",
            "appworld.env.world",
        ]
        class_candidates = ["World", "AppWorld", "Environment"]

        for module_name in module_candidates:
            try:
                mod = importlib.import_module(module_name)
            except Exception:
                continue

            for cls_name in class_candidates:
                cls = getattr(mod, cls_name, None)
                if cls is not None:
                    self._world_class = cls
                    return cls

        raise ImportError(
            "Could not import AppWorld world class. Ensure ace-appworld is installed "
            "and pass --appworld_root if needed."
        )

    def _create_world(self, task_id: str):
        world_cls = self._load_world_class()

        constructor_variants = [
            {"task_id": task_id},
            {"id": task_id},
            {"task": task_id},
            {},
        ]

        last_error = None
        for kwargs in constructor_variants:
            try:
                world = world_cls(**kwargs)
                # Some versions require explicit load/reset.
                if hasattr(world, "load_task"):
                    try:
                        world.load_task(task_id)
                    except Exception:
                        pass
                elif hasattr(world, "reset"):
                    try:
                        world.reset(task_id=task_id)
                    except Exception:
                        try:
                            world.reset(task_id)
                        except Exception:
                            pass
                return world
            except Exception as exc:
                last_error = exc

        raise RuntimeError(
            f"Failed to instantiate AppWorld world for task {task_id}: {last_error}"
        )

    def _render_prompt(self, sample: Dict[str, Any], playbook: str) -> str:
        others = sample.get("others", {})
        supervisor = others.get("supervisor", {})
        app_descriptions = others.get("app_descriptions", {})
        instruction = sample.get("question", "")

        templ = Template(self.generator_template)
        prompt = templ.render(
            input_str=instruction,
            main_user=supervisor,
            app_descriptions=app_descriptions,
            playbook=playbook,
        )

        if self.max_prompt_length and len(prompt) > int(self.max_prompt_length):
            prompt = prompt[-int(self.max_prompt_length) :]
        return prompt

    def _extract_code_blocks(self, text: str) -> List[str]:
        if not text:
            return []

        blocks = re.findall(r"```python\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if not blocks:
            open_block = re.search(
                r"```python\s*(.*)$", text, re.DOTALL | re.IGNORECASE
            )
            if open_block:
                blocks = [open_block.group(1).strip()]

        if not blocks:
            return [text.strip()]

        if self.ignore_multiple_calls and len(blocks) > 1:
            return [blocks[0]]
        return blocks

    def _execute_code(self, world: Any, code: str) -> Tuple[str, bool, str]:
        if not code.strip():
            return "", False, "Generated code block is empty"

        try:
            if hasattr(world, "execute"):
                result = world.execute(code)
            elif hasattr(world, "step"):
                result = world.step(code)
            else:
                return "", False, "World object has no execute/step method"

            if isinstance(result, tuple):
                rendered = "\n".join(str(x) for x in result)
            elif isinstance(result, dict):
                rendered = json.dumps(result, ensure_ascii=True)
            else:
                rendered = str(result)
            return rendered, True, ""
        except Exception as exc:
            return "", False, f"Execution error: {type(exc).__name__}: {exc}"

    def _is_task_completed(self, world: Any, execution_output: str) -> bool:
        if hasattr(world, "task_completed"):
            try:
                return bool(world.task_completed())
            except Exception:
                pass
        if hasattr(world, "is_task_completed"):
            try:
                return bool(world.is_task_completed())
            except Exception:
                pass
        lowered = (execution_output or "").lower()
        return "task completed" in lowered or "complete_task" in lowered

    def _evaluate_world(self, world: Any) -> Dict[str, Any]:
        if hasattr(world, "evaluate"):
            try:
                result = world.evaluate()
                if isinstance(result, dict):
                    return result
                return {"raw": result}
            except Exception as exc:
                return {"error": f"evaluate_failed: {exc}"}
        return {}

    def solve_task(
        self, sample: Dict[str, Any], playbook: str, call_prefix: str
    ) -> Dict[str, Any]:
        task_id = sample.get("others", {}).get("task_id") or sample.get("target", "")
        world = self._create_world(task_id)
        prompt = self._render_prompt(sample, playbook)

        message_history: List[str] = [prompt]
        execution_trace: List[Dict[str, Any]] = []
        task_completed = False
        final_error = ""

        for step in range(1, self.max_steps + 1):
            reflection = "\n\n".join(message_history[-6:])
            response, code_blocks, _ = self.generator.generate_for_appworld(
                question=sample.get("question", ""),
                playbook=playbook,
                context=sample.get("context", ""),
                reflection=reflection,
                call_id=f"{call_prefix}_step_{step}",
                log_dir=self.log_dir,
            )

            code_candidates = code_blocks or self._extract_code_blocks(response)
            step_record: Dict[str, Any] = {
                "step": step,
                "generator_response": response,
                "code_blocks": code_candidates,
                "executions": [],
            }

            executed_any = False
            for code in code_candidates:
                output, ok, err = self._execute_code(world, code)
                executed_any = True
                step_record["executions"].append(
                    {"code": code, "ok": ok, "output": output, "error": err}
                )
                if ok:
                    message_history.append(f"OBSERVATION:\n{output}")
                    if self._is_task_completed(world, output):
                        task_completed = True
                        break
                else:
                    message_history.append(f"OBSERVATION_ERROR:\n{err}")
                    final_error = err

                if self.ignore_multiple_calls:
                    break

            if not executed_any:
                final_error = "No executable code generated"
                message_history.append(
                    "OBSERVATION_ERROR:\nNo executable code generated"
                )

            execution_trace.append(step_record)

            if task_completed:
                break

        evaluation = self._evaluate_world(world)

        return {
            "task_id": task_id,
            "task_completed": task_completed,
            "execution_trace": execution_trace,
            "messages": message_history,
            "evaluation": evaluation,
            "final_error": final_error,
        }
