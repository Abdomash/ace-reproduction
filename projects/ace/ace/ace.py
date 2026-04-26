"""
ACE (Agent-Curator-Environment) System
Main orchestrator class for training and testing with playbook-based learning.

This module coordinates three agents:
- Generator: Produces answers using playbook knowledge
- Reflector: Analyzes outputs and tags bullets
- Curator: Updates the playbook based on feedback
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from .core import Generator, Reflector, Curator, BulletpointAnalyzer
from playbook_utils import *
from logger import *
from utils import *
from llm import set_telemetry_runtime
from result_layout import (
    build_run_leaf,
    parse_run_leaf,
    update_run_group,
    write_result_path_json,
)
from lifecycle import (
    STATUS_CHECKPOINTED,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_IN_PROGRESS,
    checkpoints_dir,
    lifecycle_fields_from_state,
    load_json as load_lifecycle_json,
    load_run_state,
    load_train_checkpoint,
    new_run_state,
    persist_run_state,
    persist_train_checkpoint,
    start_session,
    finish_session,
    train_checkpoint_path,
)
from telemetry import (
    get_invoke_helpers,
    start_telemetry,
    stop_telemetry,
    telemetry_runtime_metadata,
)


def _empty_llm_usage_row() -> Dict[str, Any]:
    return {
        "calls": 0,
        "prompt_tokens": 0,
        "response_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
        "cached_input_tokens": 0,
        "cached_output_tokens": 0,
        "total_time": 0.0,
        "cost_usd": 0.0,
        "calls_with_cost": 0,
    }


def _summarize_detailed_llm_logs(log_dir: str) -> Dict[str, Any]:
    roles: Dict[str, Dict[str, Any]] = {}
    if not log_dir or not os.path.isdir(log_dir):
        empty_total = _empty_llm_usage_row()
        return {
            "roles": {},
            "total": empty_total,
            "costs": {
                "roles": {},
                "total": {
                    key: empty_total[key]
                    for key in (
                        "calls",
                        "prompt_tokens",
                        "response_tokens",
                        "reasoning_tokens",
                        "total_tokens",
                        "cached_input_tokens",
                        "cached_output_tokens",
                        "cost_usd",
                    )
                },
            },
        }

    for filename in sorted(os.listdir(log_dir)):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(log_dir, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        role = str(data.get("role") or "unknown")
        row = roles.setdefault(role, _empty_llm_usage_row())
        row["calls"] += 1
        row["prompt_tokens"] += int(data.get("prompt_num_tokens") or 0)
        row["response_tokens"] += int(data.get("response_num_tokens") or 0)
        row["reasoning_tokens"] += int(data.get("reasoning_num_tokens") or 0)
        row["total_tokens"] += int(data.get("total_num_tokens") or 0)
        row["cached_input_tokens"] += int(data.get("cached_input_tokens") or 0)
        row["cached_output_tokens"] += int(data.get("cached_output_tokens") or 0)
        row["total_time"] += float(data.get("total_time") or data.get("call_time") or 0.0)
        if data.get("cost_usd") is not None:
            row["cost_usd"] += float(data.get("cost_usd") or 0.0)
            row["calls_with_cost"] += 1

    total = _empty_llm_usage_row()
    for row in roles.values():
        total["calls"] += row["calls"]
        total["prompt_tokens"] += row["prompt_tokens"]
        total["response_tokens"] += row["response_tokens"]
        total["reasoning_tokens"] += row["reasoning_tokens"]
        total["total_tokens"] += row["total_tokens"]
        total["cached_input_tokens"] += row["cached_input_tokens"]
        total["cached_output_tokens"] += row["cached_output_tokens"]
        total["total_time"] += row["total_time"]
        total["cost_usd"] += row["cost_usd"]
        total["calls_with_cost"] += row["calls_with_cost"]

    costs = {
        "roles": {
            role: {
                "calls": row["calls"],
                "prompt_tokens": row["prompt_tokens"],
                "response_tokens": row["response_tokens"],
                "reasoning_tokens": row["reasoning_tokens"],
                "total_tokens": row["total_tokens"],
                "cached_input_tokens": row["cached_input_tokens"],
                "cached_output_tokens": row["cached_output_tokens"],
                "cost_usd": row["cost_usd"],
            }
            for role, row in roles.items()
        },
        "total": {
            "calls": total["calls"],
            "prompt_tokens": total["prompt_tokens"],
            "response_tokens": total["response_tokens"],
            "reasoning_tokens": total["reasoning_tokens"],
            "total_tokens": total["total_tokens"],
            "cached_input_tokens": total["cached_input_tokens"],
            "cached_output_tokens": total["cached_output_tokens"],
            "cost_usd": total["cost_usd"],
        },
    }
    return {"roles": roles, "total": total, "costs": costs}


class ACE:
    """
    Main ACE system orchestrator.

    Manages the training loop where:
    1. Generator produces answers using playbook
    2. Reflector analyzes answers and tags bullets
    3. Curator updates playbook based on feedback

    """

    def __init__(
        self,
        api_provider: str,
        generator_model: str,
        reflector_model: str,
        curator_model: str,
        generator_provider: Optional[str] = None,
        reflector_provider: Optional[str] = None,
        curator_provider: Optional[str] = None,
        max_tokens: int = 4096,
        initial_playbook: Optional[str] = None,
        use_bulletpoint_analyzer: bool = False,
        bulletpoint_analyzer_threshold: float = 0.90,
        task_type: str = "standard",
    ):
        """
        Initialize the ACE system.

        Args:
            api_provider: API provider for LLM calls
            generator_model: Model name for generator
            reflector_model: Model name for reflector
            curator_model: Model name for curator
            generator_provider: Optional provider override for generator calls
            reflector_provider: Optional provider override for reflector calls
            curator_provider: Optional provider override for curator calls
            max_tokens: Maximum tokens for LLM calls
            initial_playbook: Initial playbook content (optional)
            use_bulletpoint_analyzer: Whether to use bulletpoint analyzer for deduplication
            bulletpoint_analyzer_threshold: Similarity threshold for bulletpoint analyzer (0-1)
        """
        self.api_provider = api_provider
        self.generator_provider = generator_provider or api_provider
        self.reflector_provider = reflector_provider or api_provider
        self.curator_provider = curator_provider or api_provider

        # Initialize API clients
        generator_client, reflector_client, curator_client = initialize_clients(
            api_provider,
            generator_provider=self.generator_provider,
            reflector_provider=self.reflector_provider,
            curator_provider=self.curator_provider,
        )

        # Initialize the three agents
        self.generator = Generator(
            generator_client, self.generator_provider, generator_model, max_tokens
        )
        self.reflector = Reflector(
            reflector_client, self.reflector_provider, reflector_model, max_tokens
        )
        self.curator = Curator(
            curator_client, self.curator_provider, curator_model, max_tokens
        )

        # Initialize bulletpoint analyzer if requested and available
        self.use_bulletpoint_analyzer = use_bulletpoint_analyzer
        self.bulletpoint_analyzer_threshold = bulletpoint_analyzer_threshold

        if use_bulletpoint_analyzer:
            self.bulletpoint_analyzer = BulletpointAnalyzer(
                curator_client, curator_model, max_tokens
            )
            print(
                f"✓ BulletpointAnalyzer initialized (threshold={bulletpoint_analyzer_threshold})"
            )
        else:
            self.bulletpoint_analyzer = None

        # Store configuration
        self.generator_client = generator_client
        self.reflector_client = reflector_client
        self.curator_client = curator_client
        self.max_tokens = max_tokens
        self.task_type = (task_type or "standard").lower()

        # Initialize playbook
        if initial_playbook:
            self.playbook = initial_playbook
        else:
            self.playbook = self._initialize_empty_playbook()

        self.best_playbook = self.playbook
        # Track global bullet ID
        self.next_global_id = 1
        self._telemetry_runtime = None
        self._invoke_agent_span = None
        self._record_invoke_agent_output = None
        self._appworld_adapter_cache = {}

    def _provider_run_metadata(self) -> Dict[str, Any]:
        providers = {
            "api": self.api_provider,
            "generator": self.generator_provider,
            "reflector": self.reflector_provider,
            "curator": self.curator_provider,
        }
        return {
            role: provider_metadata(provider)
            for role, provider in providers.items()
        }

    def _provider_call_failed(self, call_info: Optional[Dict[str, Any]]) -> bool:
        return isinstance(call_info, dict) and bool(call_info.get("error_type"))

    def _resolve_run_identity(
        self, config: Dict[str, Any], task_name: str, mode: str
    ) -> Tuple[str, str]:
        configured_run_id = config.get("run_id") if config else None
        if configured_run_id:
            run_id = str(configured_run_id)
            parsed = parse_run_leaf(run_id)
            timestamp = (
                parsed["timestamp"]
                if parsed
                else datetime.now().strftime("%Y%m%d_%H%M%S")
            )
            return run_id, timestamp
        seed = str(config.get("seed", "na")) if config else "na"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return build_run_leaf(mode, seed, timestamp), timestamp

    def _invoke_agent(self, agent_name: str, payload: Dict[str, Any], invoke_fn):
        if not self._invoke_agent_span or not self._record_invoke_agent_output:
            return invoke_fn()
        span_name = f"invoke_agent.{agent_name}"
        with self._invoke_agent_span(
            self._telemetry_runtime.get("tracer") if self._telemetry_runtime else None,
            span_name,
            agent_name=agent_name,
            payload=payload,
            in_process_call=True,
        ) as (span, input_bytes):
            result = invoke_fn()
            self._record_invoke_agent_output(span, result, input_bytes)
            return result

    def _initialize_empty_playbook(self) -> str:
        """Initialize an empty playbook with standard sections."""
        if self.task_type == "appworld":
            return """## STRATEGIES AND HARD RULES

## APIS TO USE FOR SPECIFIC INFORMATION

## USEFUL CODE SNIPPETS AND TEMPLATES

## COMMON MISTAKES AND CORRECT STRATEGIES

## PROBLEM-SOLVING HEURISTICS AND WORKFLOWS

## VERIFICATION CHECKLIST

## TROUBLESHOOTING AND PITFALLS

## OTHERS"""

        return """## STRATEGIES & INSIGHTS

## FORMULAS & CALCULATIONS

## CODE SNIPPETS & TEMPLATES

## COMMON MISTAKES TO AVOID

## PROBLEM-SOLVING HEURISTICS

## CONTEXT CLUES & INDICATORS

## OTHERS"""

    def _extract_config_params(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract common configuration parameters.

        Args:
            config: Configuration dictionary

        Returns:
            Dictionary with extracted parameters
        """
        return {
            "num_epochs": config.get("num_epochs", 1),
            "max_num_rounds": config.get("max_num_rounds", 3),
            "curator_frequency": config.get("curator_frequency", 1),
            "eval_steps": config.get("eval_steps", 100),
            "save_steps": config.get("save_steps", 50),
            "token_budget": config.get("playbook_token_budget", 80000),
            "task_name": config.get("task_name", "default"),
            "use_json_mode": config.get("json_mode", False),
            "no_ground_truth": config.get("no_ground_truth", False),
            "save_dir": config.get("save_dir", "./results"),
            "test_workers": config.get("test_workers", 20),
            "use_bulletpoint_analyzer": config.get("use_bulletpoint_analyzer", False),
            "bulletpoint_analyzer_threshold": config.get(
                "bulletpoint_analyzer_threshold", 0.90
            ),
            "dataset_name": config.get("dataset_name", "train"),
            "max_agent_steps": config.get("max_agent_steps", 30),
            "appworld_root": config.get("appworld_root"),
            "max_retries": config.get("max_retries", 5),
            "ignore_multiple_calls": config.get("ignore_multiple_calls", False),
            "max_prompt_length": config.get("max_prompt_length"),
        }

    def _is_finer_lifecycle_run(self, mode: str, config: Dict[str, Any]) -> bool:
        task_name = str((config or {}).get("task_name") or "").lower()
        return mode == "offline" and task_name == "finer"

    def _write_final_results(
        self,
        save_path: str,
        run_id: str,
        telemetry_metadata: Dict[str, Any],
        results: Dict[str, Any],
        run_state: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        log_dir = os.path.join(save_path, "detailed_llm_logs")
        llm_usage = _summarize_detailed_llm_logs(log_dir)
        payload = {
            "run_id": run_id,
            "telemetry": telemetry_metadata,
            "llm_usage": {
                "roles": llm_usage["roles"],
                "total": llm_usage["total"],
            },
            "costs": llm_usage["costs"],
            "results": results,
            **results,
        }
        if run_state:
            payload.update(lifecycle_fields_from_state(run_state))
        final_results_path = os.path.join(save_path, "final_results.json")
        with open(final_results_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        return payload

    def _write_result_metadata(
        self,
        *,
        config: Dict[str, Any],
        save_dir: str,
        save_path: str,
        run_id: str,
        mode: str,
        run_timestamp: str,
        run_state: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        result_metadata = write_result_path_json(
            config=config,
            save_dir=save_dir,
            run_dir=save_path,
            run_leaf=run_id,
            mode=mode,
            seed=(config or {}).get("seed", "na"),
            timestamp=run_timestamp,
            run_state=run_state,
        )
        update_run_group(save_dir, result_metadata, run_state=run_state)
        return result_metadata

    def _refresh_run_metadata(
        self,
        *,
        config: Dict[str, Any],
        save_dir: str,
        save_path: str,
        run_id: str,
        mode: str,
        run_timestamp: str,
    ) -> Dict[str, Any] | None:
        run_state = load_run_state(save_path)
        if not run_state:
            return None
        return self._write_result_metadata(
            config=config,
            save_dir=save_dir,
            save_path=save_path,
            run_id=run_id,
            mode=mode,
            run_timestamp=run_timestamp,
            run_state=run_state,
        )

    def _persist_training_checkpoint_files(
        self, save_path: str, checkpoint_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        checkpoint_dir = checkpoints_dir(save_path)
        current_playbook_path = checkpoint_dir / "current_playbook.txt"
        best_playbook_path = checkpoint_dir / "best_playbook.txt"
        current_playbook_path.write_text(
            checkpoint_payload.get("current_playbook", self.playbook),
            encoding="utf-8",
        )
        best_playbook_path.write_text(
            checkpoint_payload.get("best_playbook", self.best_playbook),
            encoding="utf-8",
        )
        payload = dict(checkpoint_payload)
        payload["current_playbook_path"] = str(current_playbook_path)
        payload["best_playbook_path"] = str(best_playbook_path)
        payload.pop("current_playbook", None)
        payload.pop("best_playbook", None)
        persist_train_checkpoint(save_path, payload)
        return payload

    def _get_appworld_adapter(
        self, data_processor, config: Dict[str, Any], log_dir: str
    ):
        cache_key = f"{id(data_processor)}::{log_dir}"
        adapter = self._appworld_adapter_cache.get(cache_key)
        if adapter is not None:
            return adapter

        from eval.appworld.task_adapter import AppWorldTaskAdapter

        adapter = AppWorldTaskAdapter(
            ace_system=self,
            data_processor=data_processor,
            config=config or {},
            log_dir=log_dir,
        )
        self._appworld_adapter_cache[cache_key] = adapter
        return adapter

    def _setup_paths(
        self, save_dir: str, task_name: str, mode: str, run_id: str
    ) -> Tuple[str, str]:
        """
        Setup logging paths and directories.

        Args:
            save_dir: Base path for saving results
            task_name: task name
            mode: 'offline', 'online', or 'eval_only'

        Returns:
            Tuple of (usage_log_path, playbook_dir)
        """
        # Create run folder using canonical run_id
        save_path = os.path.join(save_dir, run_id)
        os.makedirs(save_path, exist_ok=True)
        log_dir = os.path.join(save_path, "detailed_llm_logs")
        os.makedirs(log_dir, exist_ok=True)

        if mode == "eval_only":
            return save_path, log_dir

        usage_log_path = os.path.join(save_path, "bullet_usage_log.jsonl")
        playbook_dir = os.path.join(save_path, "intermediate_playbooks")
        os.makedirs(playbook_dir, exist_ok=True)

        return save_path, usage_log_path, playbook_dir, log_dir

    def run(
        self,
        mode: str,
        train_samples: Optional[List[Dict[str, Any]]] = None,
        val_samples: Optional[List[Dict[str, Any]]] = None,
        test_samples: Optional[List[Dict[str, Any]]] = None,
        data_processor=None,
        config: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Main entrypoint for running ACE system in different modes.

        Args:
            mode: Run mode - 'offline', 'online', or 'eval_only'
            train_samples: Training samples (required for offline mode)
            val_samples: Validation samples (required for offline mode)
            test_samples: Test samples (required for online and eval_only modes)
            data_processor: Data processor instance for the task
            config: Configuration dictionary

        Returns:
            Dictionary with results depending on the mode
        """
        # Validate inputs
        if mode not in ["offline", "online", "eval_only"]:
            raise ValueError(
                f"Invalid mode: {mode}. Must be 'offline', 'online', or 'eval_only'"
            )

        if mode == "offline" and (train_samples is None or val_samples is None):
            raise ValueError("Offline mode requires train_samples and val_samples")

        if mode == "online" and test_samples is None:
            raise ValueError("Online mode requires test_samples")

        if mode == "eval_only" and test_samples is None:
            raise ValueError("eval_only mode requires test_samples")

        # Extract configuration
        config_params = self._extract_config_params(config)
        task_name = config_params["task_name"]
        save_dir = config_params["save_dir"]
        resume_from = (config or {}).get("resume_from")
        if resume_from:
            save_path = os.path.abspath(str(resume_from))
            run_id = os.path.basename(save_path.rstrip(os.sep))
            _, run_timestamp = self._resolve_run_identity({"run_id": run_id}, task_name, mode)
            save_dir = os.path.dirname(save_path)
            config["run_id"] = run_id
            config["save_dir"] = save_dir
        else:
            run_id, run_timestamp = self._resolve_run_identity(config, task_name, mode)
            save_path = None

        # Setup paths based on mode
        if save_path is None and mode == "eval_only":
            save_path, log_dir = self._setup_paths(save_dir, task_name, mode, run_id)
            usage_log_path = None
            playbook_dir = None
        elif save_path is None:
            save_path, usage_log_path, playbook_dir, log_dir = self._setup_paths(
                save_dir, task_name, mode, run_id
            )
        elif mode == "eval_only":
            os.makedirs(save_path, exist_ok=True)
            log_dir = os.path.join(save_path, "detailed_llm_logs")
            os.makedirs(log_dir, exist_ok=True)
            usage_log_path = None
            playbook_dir = None
        else:
            os.makedirs(save_path, exist_ok=True)
            log_dir = os.path.join(save_path, "detailed_llm_logs")
            os.makedirs(log_dir, exist_ok=True)
            usage_log_path = os.path.join(save_path, "bullet_usage_log.jsonl")
            playbook_dir = os.path.join(save_path, "intermediate_playbooks")
            os.makedirs(playbook_dir, exist_ok=True)

        self._telemetry_runtime = start_telemetry(
            config=config,
            save_path=save_path,
            task_name=task_name,
            mode=mode,
            run_id=run_id,
        )
        set_telemetry_runtime(self._telemetry_runtime)
        self._invoke_agent_span, self._record_invoke_agent_output = get_invoke_helpers()

        # Save configuration
        config_path = os.path.join(save_path, "run_config.json")
        provider_run_metadata = self._provider_run_metadata()
        with open(config_path, "w") as f:
            json.dump(
                {
                    "run_id": run_id,
                    "task_name": task_name,
                    "mode": mode,
                    "api_provider": self.api_provider,
                    "generator_provider": self.generator_provider,
                    "reflector_provider": self.reflector_provider,
                    "curator_provider": self.curator_provider,
                    "generator_model": self.generator.model,
                    "reflector_model": self.reflector.model,
                    "curator_model": self.curator.model,
                    "provider_metadata": provider_run_metadata,
                    "provider_base_url_labels": {
                        role: meta.get("base_url_label")
                        for role, meta in provider_run_metadata.items()
                    },
                    "pricing_snapshot": pricing_snapshot(
                        {
                            "generator": self.generator.model,
                            "reflector": self.reflector.model,
                            "curator": self.curator.model,
                        }
                    ),
                    "telemetry": telemetry_runtime_metadata(self._telemetry_runtime),
                    "config": config,
                },
                f,
                indent=2,
            )
        run_state = None
        if self._is_finer_lifecycle_run(mode, config or {}):
            run_state = load_run_state(save_path)
            if not run_state:
                run_state = new_run_state(
                    run_id=run_id,
                    checkpointing_enabled=bool((config or {}).get("checkpoint_enabled")),
                    resume_enabled=bool((config or {}).get("resume_enabled", True)),
                    current_stage="baseline-eval" if test_samples else "train",
                )
                persist_run_state(save_path, run_state)
        self._write_result_metadata(
            config=config,
            save_dir=save_dir,
            save_path=save_path,
            run_id=run_id,
            mode=mode,
            run_timestamp=run_timestamp,
            run_state=run_state,
        )

        # Print initial banner
        print(f"\n{'=' * 60}")
        print(f"ACE SYSTEM - {mode.upper().replace('_', ' ')} MODE")
        print(f"{'=' * 60}")
        print(f"Task: {task_name}")
        if mode == "offline":
            print(f"Train samples: {len(train_samples)}")
            print(f"Validation samples: {len(val_samples)}")
            if test_samples:
                print(f"Test samples: {len(test_samples)}")
        elif mode == "online":
            print(f"Test samples (used for training and testing): {len(test_samples)}")
        else:  # eval_only
            print(f"Test samples: {len(test_samples)}")
        print(f"{'=' * 60}\n")

        telemetry_metadata = telemetry_runtime_metadata(self._telemetry_runtime)
        if telemetry_metadata.get("enabled"):
            print("Telemetry: enabled")
            print(f"Telemetry trace: {telemetry_metadata.get('trace_path')}")
            print(f"Telemetry metrics: {telemetry_metadata.get('metrics_path')}")
            print(
                f"Telemetry interval (s): {telemetry_metadata.get('metrics_interval_seconds')}"
            )
        else:
            print("Telemetry: disabled")
            if telemetry_metadata.get("error"):
                print(f"Telemetry startup error: {telemetry_metadata.get('error')}")
        print()

        if self._is_finer_lifecycle_run(mode, config or {}):
            return self._run_finer_offline_lifecycle(
                train_samples=train_samples or [],
                val_samples=val_samples or [],
                test_samples=test_samples or [],
                data_processor=data_processor,
                config=config or {},
                save_path=save_path,
                save_dir=save_dir,
                run_id=run_id,
                run_timestamp=run_timestamp,
                usage_log_path=usage_log_path,
                playbook_dir=playbook_dir,
                log_dir=log_dir,
                telemetry_metadata=telemetry_metadata,
            )

        # Execute based on mode
        results = {}
        try:
            if mode == "offline":
                # OFFLINE MODE WORKFLOW
                # 1. Run initial test if test_samples provided
                if test_samples:
                    print(f"\n{'=' * 60}")
                    print(f"INITIAL TEST (before training)")
                    print(f"{'=' * 60}\n")
                    initial_test_results = self._run_test(
                        test_samples=test_samples,
                        data_processor=data_processor,
                        playbook=self.playbook,
                        config=config,
                        log_dir=log_dir,
                        save_path=save_path,
                        prefix="initial",
                    )
                    results["initial_test_results"] = initial_test_results
                    print(
                        f"Initial Test Accuracy: {initial_test_results['accuracy']:.3f}\n"
                    )

                # 2. Run offline training
                print(f"\n{'=' * 60}")
                print(f"STARTING OFFLINE TRAINING")
                print(f"{'=' * 60}\n")
                training_results = self._offline_train(
                    train_samples=train_samples,
                    val_samples=val_samples,
                    data_processor=data_processor,
                    config=config,
                    save_path=save_path,
                    usage_log_path=usage_log_path,
                    playbook_dir=playbook_dir,
                    log_dir=log_dir,
                )
                results["training_results"] = training_results

                # 3. Run final test if test_samples provided
                if test_samples:
                    print(f"\n{'=' * 60}")
                    print(f"FINAL TEST (with best playbook)")
                    print(f"{'=' * 60}\n")
                    final_test_results = self._run_test(
                        test_samples=test_samples,
                        data_processor=data_processor,
                        playbook=self.best_playbook,
                        config=config,
                        log_dir=log_dir,
                        save_path=save_path,
                        prefix="final",
                    )
                    results["final_test_results"] = final_test_results
                    print(
                        f"Final Test Accuracy: {final_test_results['accuracy']:.3f}\n"
                    )

            elif mode == "online":
                # ONLINE MODE WORKFLOW
                # 1. Run initial test
                print(f"\n{'=' * 60}")
                print(f"INITIAL TEST (before training)")
                print(f"{'=' * 60}\n")
                initial_test_results = self._run_test(
                    test_samples=test_samples,
                    data_processor=data_processor,
                    playbook=self.playbook,
                    config=config,
                    log_dir=log_dir,
                    save_path=save_path,
                    prefix="initial",
                )
                results["initial_test_results"] = initial_test_results
                print(
                    f"Initial Test Accuracy: {initial_test_results['accuracy']:.3f}\n"
                )

                # 2. Run online training and testing
                print(f"\n{'=' * 60}")
                print(f"STARTING ONLINE TRAIN AND TEST")
                print(f"{'=' * 60}\n")
                online_results = self._online_train_and_test(
                    test_samples=test_samples,
                    data_processor=data_processor,
                    config=config,
                    save_path=save_path,
                    usage_log_path=usage_log_path,
                    playbook_dir=playbook_dir,
                    log_dir=log_dir,
                )
                results["online_test_results"] = online_results

            else:  # eval_only
                # EVAL ONLY MODE WORKFLOW
                print(f"\n{'=' * 60}")
                print(f"RUNNING TEST")
                print(f"{'=' * 60}\n")
                test_results = self._run_test(
                    test_samples=test_samples,
                    data_processor=data_processor,
                    playbook=self.playbook,
                    config=config,
                    log_dir=log_dir,
                    save_path=save_path,
                    prefix="test",
                )
                results["test_results"] = test_results
        finally:
            stop_telemetry(self._telemetry_runtime)
            set_telemetry_runtime(None)

        # Save consolidated results
        llm_usage = _summarize_detailed_llm_logs(log_dir)
        final_results_path = os.path.join(save_path, "final_results.json")
        with open(final_results_path, "w") as f:
            json.dump(
                {
                    "run_id": run_id,
                    "telemetry": telemetry_metadata,
                    "llm_usage": {
                        "roles": llm_usage["roles"],
                        "total": llm_usage["total"],
                    },
                    "costs": llm_usage["costs"],
                    "results": results,
                    **results,
                },
                f,
                indent=2,
            )

        # Print final summary
        print(f"\n{'=' * 60}")
        print(f"RUN COMPLETE")
        print(f"{'=' * 60}")
        print(f"Mode: {mode.upper().replace('_', ' ')}")
        if mode == "offline":
            print(
                f"Best Validation Accuracy: {results['training_results']['best_validation_accuracy']:.3f}"
            )
            if test_samples:
                print(
                    f"Initial Test Accuracy: {results['initial_test_results']['accuracy']:.3f}"
                )
                print(
                    f"Final Test Accuracy: {results['final_test_results']['accuracy']:.3f}"
                )
        elif mode == "online":
            print(
                f"Initial Test Accuracy: {results['initial_test_results']['accuracy']:.3f}"
            )
            print(
                f"Final Test Accuracy: {results['online_test_results']['accuracy']:.3f}"
            )
        else:  # eval_only
            print(f"Test Accuracy: {results['test_results']['accuracy']:.3f}")
        print(f"Results saved to: {save_path}")
        print(f"Run ID: {run_id}")
        print(f"{'=' * 60}\n")

        return results

    def _stage_rank(self, stage: str | None) -> int:
        order = {
            None: -1,
            "baseline-eval": 0,
            "train": 1,
            "final-eval": 2,
        }
        return order.get(stage, -1)

    def _stage_is_complete(self, run_state: Dict[str, Any], stage: str) -> bool:
        return self._stage_rank(run_state.get("last_completed_stage")) >= self._stage_rank(stage)

    def _restore_finer_training_checkpoint(self, checkpoint: Dict[str, Any] | None) -> None:
        if not checkpoint:
            return
        current_playbook_path = checkpoint.get("current_playbook_path")
        best_playbook_path = checkpoint.get("best_playbook_path")
        if current_playbook_path and os.path.exists(current_playbook_path):
            self.playbook = Path(current_playbook_path).read_text(encoding="utf-8")
        if best_playbook_path and os.path.exists(best_playbook_path):
            self.best_playbook = Path(best_playbook_path).read_text(encoding="utf-8")
        self.next_global_id = int(checkpoint.get("next_global_bullet_id") or self.next_global_id)

    def _run_finer_offline_lifecycle(
        self,
        *,
        train_samples: List[Dict[str, Any]],
        val_samples: List[Dict[str, Any]],
        test_samples: List[Dict[str, Any]],
        data_processor,
        config: Dict[str, Any],
        save_path: str,
        save_dir: str,
        run_id: str,
        run_timestamp: str,
        usage_log_path: str,
        playbook_dir: str,
        log_dir: str,
        telemetry_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        run_state = load_run_state(save_path) or new_run_state(
            run_id=run_id,
            checkpointing_enabled=bool(config.get("checkpoint_enabled")),
            resume_enabled=bool(config.get("resume_enabled", True)),
            current_stage="baseline-eval" if test_samples else "train",
        )
        persist_run_state(save_path, run_state)
        self._refresh_run_metadata(
            config=config,
            save_dir=save_dir,
            save_path=save_path,
            run_id=run_id,
            mode="offline",
            run_timestamp=run_timestamp,
        )

        existing_final_results = load_lifecycle_json(os.path.join(save_path, "final_results.json")) or {}
        existing_results = existing_final_results.get("results") if isinstance(existing_final_results, dict) else {}
        results: Dict[str, Any] = dict(existing_results or {})

        checkpoint = load_train_checkpoint(save_path)
        self._restore_finer_training_checkpoint(checkpoint)

        next_stage = run_state.get("current_stage") or "baseline-eval"
        if self._stage_is_complete(run_state, "baseline-eval"):
            next_stage = "train"
        if self._stage_is_complete(run_state, "train"):
            next_stage = "final-eval"
        if self._stage_is_complete(run_state, "final-eval"):
            next_stage = "final-eval"

        session = start_session(
            save_path,
            run_state,
            stage_entered=next_stage,
            resume_from_checkpoint=bool(config.get("resume_from") or checkpoint),
        )

        def persist_state_and_results() -> None:
            persist_run_state(save_path, run_state)
            self._refresh_run_metadata(
                config=config,
                save_dir=save_dir,
                save_path=save_path,
                run_id=run_id,
                mode="offline",
                run_timestamp=run_timestamp,
            )
            self._write_final_results(
                save_path=save_path,
                run_id=run_id,
                telemetry_metadata=telemetry_metadata,
                results=results,
                run_state=run_state,
            )

        try:
            if test_samples and not self._stage_is_complete(run_state, "baseline-eval"):
                run_state["current_stage"] = "baseline-eval"
                persist_state_and_results()
                print(f"\n{'=' * 60}")
                print("INITIAL TEST (before training)")
                print(f"{'=' * 60}\n")
                initial_test_results = self._run_test(
                    test_samples=test_samples,
                    data_processor=data_processor,
                    playbook=self.playbook,
                    config=config,
                    log_dir=log_dir,
                    save_path=save_path,
                    prefix="initial",
                )
                results["initial_test_results"] = initial_test_results
                run_state["last_completed_stage"] = "baseline-eval"
                run_state["current_stage"] = "baseline-eval"
                persist_state_and_results()
                if config.get("stop_after_stage") == "baseline-eval":
                    run_state["status"] = STATUS_CHECKPOINTED
                    persist_state_and_results()
                    run_state, _ = finish_session(
                        save_path,
                        run_state,
                        session,
                        stage_exited="baseline-eval",
                        status=STATUS_CHECKPOINTED,
                    )
                    persist_state_and_results()
                    return results

            if not self._stage_is_complete(run_state, "train"):
                run_state["current_stage"] = "train"
                persist_state_and_results()
                print(f"\n{'=' * 60}")
                print("STARTING OFFLINE TRAINING")
                print(f"{'=' * 60}\n")
                training_outcome = self._offline_train(
                    train_samples=train_samples,
                    val_samples=val_samples,
                    data_processor=data_processor,
                    config=config,
                    save_path=save_path,
                    usage_log_path=usage_log_path,
                    playbook_dir=playbook_dir,
                    log_dir=log_dir,
                    resume_checkpoint=checkpoint,
                    checkpoint_enabled=bool(config.get("checkpoint_enabled")),
                    stop_after_step=config.get("stop_after_step"),
                )
                results["training_results"] = training_outcome["training_results"]
                persist_state_and_results()
                if training_outcome.get("stopped_early"):
                    run_state["status"] = STATUS_CHECKPOINTED
                    run_state["current_stage"] = "train"
                    persist_state_and_results()
                    run_state, _ = finish_session(
                        save_path,
                        run_state,
                        session,
                        stage_exited="train",
                        status=STATUS_CHECKPOINTED,
                    )
                    persist_state_and_results()
                    return results
                run_state["last_completed_stage"] = "train"
                persist_state_and_results()
                if config.get("stop_after_stage") == "train":
                    run_state["status"] = STATUS_CHECKPOINTED
                    persist_state_and_results()
                    run_state, _ = finish_session(
                        save_path,
                        run_state,
                        session,
                        stage_exited="train",
                        status=STATUS_CHECKPOINTED,
                    )
                    persist_state_and_results()
                    return results

            if test_samples and not self._stage_is_complete(run_state, "final-eval"):
                run_state["current_stage"] = "final-eval"
                persist_state_and_results()
                print(f"\n{'=' * 60}")
                print("FINAL TEST (with best playbook)")
                print(f"{'=' * 60}\n")
                final_test_results = self._run_test(
                    test_samples=test_samples,
                    data_processor=data_processor,
                    playbook=self.best_playbook,
                    config=config,
                    log_dir=log_dir,
                    save_path=save_path,
                    prefix="final",
                )
                results["final_test_results"] = final_test_results
                run_state["last_completed_stage"] = "final-eval"

            run_state["status"] = STATUS_COMPLETED
            persist_state_and_results()
            run_state, _ = finish_session(
                save_path,
                run_state,
                session,
                stage_exited=run_state.get("last_completed_stage"),
                status=STATUS_COMPLETED,
            )
            persist_state_and_results()

            print(f"\n{'=' * 60}")
            print("RUN COMPLETE")
            print(f"{'=' * 60}")
            if "training_results" in results:
                print(
                    f"Best Validation Accuracy: {results['training_results']['best_validation_accuracy']:.3f}"
                )
            if "initial_test_results" in results:
                print(f"Initial Test Accuracy: {results['initial_test_results']['accuracy']:.3f}")
            if "final_test_results" in results:
                print(f"Final Test Accuracy: {results['final_test_results']['accuracy']:.3f}")
            print(f"Results saved to: {save_path}")
            print(f"Run ID: {run_id}")
            print(f"{'=' * 60}\n")
            return results
        except Exception as exc:
            run_state["status"] = STATUS_FAILED
            run_state["failure_reason"] = str(exc)
            persist_state_and_results()
            run_state, _ = finish_session(
                save_path,
                run_state,
                session,
                stage_exited=run_state.get("current_stage"),
                status=STATUS_FAILED,
            )
            persist_state_and_results()
            raise

    def _run_test(
        self,
        test_samples: List[Dict[str, Any]],
        data_processor,
        playbook: str,
        config: Dict[str, Any],
        log_dir: str,
        save_path: str,
        prefix: str = "test",
    ) -> Dict[str, Any]:
        """
        Run testing

        Args:
            test_samples: List of test samples
            data_processor: Data processor instance for the task
            playbook: Playbook to use for testing
            config: Configuration dictionary
            log_dir: Directory for detailed logs
            save_path: Path to save results
            prefix: Prefix for saved files (e.g., 'initial', 'final', 'test')

        Returns:
            Dictionary with test results
        """
        if self.task_type == "appworld":
            adapter = self._get_appworld_adapter(data_processor, config, log_dir)
            test_results, test_error_log = adapter.run_test(
                samples=test_samples,
                playbook=playbook,
                prefix=prefix,
            )

            test_results_path = os.path.join(save_path, f"{prefix}_test_results.json")
            with open(test_results_path, "w") as f:
                json.dump(
                    {
                        "test_results": test_results,
                        "error_log": test_error_log,
                    },
                    f,
                    indent=2,
                )

            return test_results

        config_params = self._extract_config_params(config)
        use_json_mode = config_params["use_json_mode"]
        test_workers = config_params["test_workers"]

        test_results, test_error_log = evaluate_test_set(
            data_processor,
            self.generator,
            playbook,
            test_samples,
            self.max_tokens,
            log_dir,
            max_workers=test_workers,
            use_json_mode=use_json_mode,
        )

        # Save test results
        test_results_path = os.path.join(save_path, f"{prefix}_test_results.json")
        with open(test_results_path, "w") as f:
            json.dump(
                {
                    "test_results": test_results,
                    "error_log": test_error_log,
                },
                f,
                indent=2,
            )

        return test_results

    def _train_single_sample(
        self,
        task_dict: Dict[str, Any],
        data_processor,
        step_id: str,
        epoch: int,
        step: int,
        usage_log_path: str,
        log_dir: str,
        config_params: Dict[str, Any],
        total_samples: int,
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Train on a single sample with reflection and curation.

        Args:
            task_dict: Sample dictionary with question, context, target
            data_processor: Data processor for evaluation
            step_id: Identifier string for this step (e.g., "train_e_1_s_10" or "online_train_w_1_s_5")
            epoch: Current epoch number
            step: Current step number
            usage_log_path: Path for bullet usage logging
            log_dir: Path for logging directory
            config_params: Configuration parameters dictionary
            total_samples: Total number of samples in dataset

        Returns:
            Tuple of (pre_train_answer, post_train_answer, tracking_dict)
        """
        if self.task_type == "appworld":
            adapter = self._get_appworld_adapter(data_processor, config_params, log_dir)
            return adapter.train_single_sample(
                task_dict=task_dict,
                step_id=step_id,
                usage_log_path=usage_log_path,
                config_params=config_params,
                step=step,
                epoch=epoch,
                total_samples=total_samples,
            )

        # Extract configuration
        max_num_rounds = config_params["max_num_rounds"]
        curator_frequency = config_params["curator_frequency"]
        token_budget = config_params["token_budget"]
        use_json_mode = config_params["use_json_mode"]
        no_ground_truth = config_params["no_ground_truth"]

        # Extract sample data
        question = task_dict.get("question", "")
        context = task_dict.get("context", "")
        target = task_dict.get("target", "")

        # STEP 1: Initial generation (pre-train)
        print("Generating initial answer...")
        gen_response, bullet_ids, call_info = self._invoke_agent(
            "generator",
            {
                "question": question,
                "context": context,
                "step_id": step_id,
                "phase": "gen_initial",
            },
            lambda: self.generator.generate(
                question=question,
                playbook=self.playbook,
                context=context,
                reflection="(empty)",
                use_json_mode=use_json_mode,
                call_id=f"{step_id}_gen_initial",
                log_dir=log_dir,
            ),
        )

        # Extract answer and check correctness
        initial_generation_failed = self._provider_call_failed(call_info)
        if initial_generation_failed:
            final_answer = "NO_VISIBLE_MODEL_OUTPUT"
            gen_response = "Generator failed: no visible model output"
        else:
            final_answer = extract_answer(gen_response)
        is_correct = data_processor.answer_is_correct(final_answer, target)
        pre_train_answer = final_answer

        print(f"Correct: {is_correct}")

        # Log bullet usage
        log_bullet_usage(
            usage_log_path,
            epoch,
            step,
            task_dict,
            bullet_ids,
            playbook=self.playbook,
            is_correct=is_correct,
        )

        # Track pre-train result
        tracking_dict = {
            "pre_train_result": {
                "final_answer": final_answer,
                "is_correct": is_correct,
                "playbook_num_tokens": count_tokens(self.playbook),
                "playbook_length": len(self.playbook),
            }
        }

        reflection_content = "(empty)"
        skip_curator_for_sample = False

        # STEP 2: Reflection and regeneration
        if not is_correct:
            # For incorrect answers - iterate reflection rounds
            for round_num in range(max_num_rounds):
                print(f"Reflection round {round_num + 1}/{max_num_rounds}")

                # Get bullets for reflector
                playbook_bullets = extract_playbook_bullets(self.playbook, bullet_ids)

                # Reflect on error
                reflection_content, bullet_tags, reflect_call_info = self._invoke_agent(
                    "reflector",
                    {
                        "question": question,
                        "step_id": step_id,
                        "round": round_num,
                        "phase": "reflect_error",
                    },
                    lambda: self.reflector.reflect(
                        question=question,
                        reasoning_trace=gen_response,
                        predicted_answer=final_answer,
                        ground_truth=target if not no_ground_truth else None,
                        environment_feedback="Predicted answer does not match ground truth",
                        bullets_used=playbook_bullets,
                        use_ground_truth=not no_ground_truth,
                        use_json_mode=use_json_mode,
                        call_id=f"{step_id}_round_{round_num}",
                        log_dir=log_dir,
                    ),
                )
                reflector_failed = self._provider_call_failed(reflect_call_info)

                # Update bullet counts
                if bullet_tags and not reflector_failed:
                    self.playbook = update_bullet_counts(self.playbook, bullet_tags)
                if reflector_failed:
                    reflection_content = "REFLECTION_FAILED_NO_VISIBLE_OUTPUT"
                    skip_curator_for_sample = True
                    break

                # Regenerate with reflection
                gen_response, bullet_ids, regen_call_info = self._invoke_agent(
                    "generator",
                    {
                        "question": question,
                        "context": context,
                        "step_id": step_id,
                        "round": round_num,
                        "phase": "post_reflect_regen",
                    },
                    lambda: self.generator.generate(
                        question=question,
                        playbook=self.playbook,
                        context=context,
                        reflection=reflection_content,
                        use_json_mode=use_json_mode,
                        call_id=f"{step_id}_post_reflect_round_{round_num}",
                        log_dir=log_dir,
                    ),
                )

                if self._provider_call_failed(regen_call_info):
                    final_answer = "NO_VISIBLE_MODEL_OUTPUT"
                else:
                    final_answer = extract_answer(gen_response)

                if data_processor.answer_is_correct(final_answer, target):
                    print(f"Corrected after reflection round {round_num + 1}!")
                    is_correct = True
                    break

        else:
            # For correct answers - still run reflector to tag helpful bullets
            playbook_bullets = extract_playbook_bullets(self.playbook, bullet_ids)

            reflection_content, bullet_tags, reflect_call_info = self._invoke_agent(
                "reflector",
                {
                    "question": question,
                    "step_id": step_id,
                    "phase": "reflect_correct",
                },
                lambda: self.reflector.reflect(
                    question=question,
                    reasoning_trace=gen_response,
                    predicted_answer=final_answer,
                    ground_truth=target if not no_ground_truth else None,
                    environment_feedback="Predicted answer matches ground truth",
                    bullets_used=playbook_bullets,
                    use_ground_truth=not no_ground_truth,
                    use_json_mode=use_json_mode,
                    call_id=f"{step_id}_reflect_on_correct",
                    log_dir=log_dir,
                ),
            )
            reflector_failed = self._provider_call_failed(reflect_call_info)

            # Update bullet counts
            if bullet_tags and not reflector_failed:
                self.playbook = update_bullet_counts(self.playbook, bullet_tags)
            if reflector_failed:
                reflection_content = "REFLECTION_FAILED_NO_VISIBLE_OUTPUT"
                skip_curator_for_sample = True

            # Log with reflection
            log_bullet_usage(
                usage_log_path,
                epoch,
                step,
                task_dict,
                bullet_ids,
                playbook=self.playbook,
                reflection_content=reflection_content,
                is_correct=is_correct,
            )

        # STEP 3: Curator - Periodically update playbook
        if step % curator_frequency == 0 and not skip_curator_for_sample:
            print(f"\n--- Running Curator at step {step} ---")

            stats = get_playbook_stats(self.playbook)

            self.playbook, self.next_global_id, operations, _ = self._invoke_agent(
                "curator",
                {
                    "step_id": step_id,
                    "step": step,
                    "phase": "curate",
                },
                lambda: self.curator.curate(
                    current_playbook=self.playbook,
                    recent_reflection=reflection_content,
                    question_context=context,
                    current_step=step,
                    total_samples=total_samples,
                    token_budget=token_budget,
                    playbook_stats=stats,
                    use_ground_truth=not no_ground_truth,
                    use_json_mode=use_json_mode,
                    call_id=step_id,
                    log_dir=log_dir,
                    next_global_id=self.next_global_id,
                ),
            )

            # Run bulletpoint analyzer if enabled
            if self.use_bulletpoint_analyzer and self.bulletpoint_analyzer:
                print(
                    f"  Running BulletpointAnalyzer (threshold={self.bulletpoint_analyzer_threshold})..."
                )
                self.playbook = self.bulletpoint_analyzer.analyze(
                    playbook=self.playbook,
                    threshold=self.bulletpoint_analyzer_threshold,
                    merge=True,
                )

        # STEP 4: Post-curator generation
        gen_response, _, post_call_info = self._invoke_agent(
            "generator",
            {
                "question": question,
                "context": context,
                "step_id": step_id,
                "phase": "post_curate",
            },
            lambda: self.generator.generate(
                question=question,
                playbook=self.playbook,
                context=context,
                reflection="(empty)",
                use_json_mode=use_json_mode,
                call_id=f"{step_id}_post_curate",
                log_dir=log_dir,
            ),
        )

        if self._provider_call_failed(post_call_info):
            final_answer = "NO_VISIBLE_MODEL_OUTPUT"
        else:
            final_answer = extract_answer(gen_response)
        post_train_answer = final_answer

        post_train_is_correct = data_processor.answer_is_correct(final_answer, target)
        tracking_dict["post_train_result"] = {
            "final_answer": final_answer,
            "is_correct": post_train_is_correct,
            "playbook_num_tokens": count_tokens(self.playbook),
            "playbook_length": len(self.playbook),
        }

        return pre_train_answer, post_train_answer, tracking_dict

    def _offline_train(
        self,
        train_samples: List[Dict[str, Any]],
        val_samples: List[Dict[str, Any]],
        data_processor,
        config: Dict[str, Any],
        save_path: str,
        usage_log_path: str,
        playbook_dir: str,
        log_dir: str,
        resume_checkpoint: Dict[str, Any] | None = None,
        checkpoint_enabled: bool = False,
        stop_after_step: int | None = None,
    ) -> Dict[str, Any]:
        """
        Run offline training

        Args:
            train_samples: List of training samples
            val_samples: List of validation samples
            data_processor: Data processor instance for the task
            config: Configuration dictionary
            save_path: Path to save results
            usage_log_path: Path for bullet usage logging
            playbook_dir: Directory for intermediate playbooks
            log_dir: Directory for detailed logs

        Returns:
            Dictionary with training results
        """
        # Extract configuration using helper
        config_params = self._extract_config_params(config)
        num_epochs = config_params["num_epochs"]
        eval_steps = config_params["eval_steps"]
        save_steps = config_params["save_steps"]
        test_workers = config_params["test_workers"]
        use_json_mode = config_params["use_json_mode"]
        curator_frequency = config_params["curator_frequency"]

        # Initialize tracking
        results = list((resume_checkpoint or {}).get("results") or [])
        pre_train_post_train_results = list(
            (resume_checkpoint or {}).get("pre_train_post_train_results") or []
        )
        error_logs = list((resume_checkpoint or {}).get("error_logs") or [])
        best_accuracy = float((resume_checkpoint or {}).get("best_accuracy") or 0.0)
        self.best_playbook = self.best_playbook if resume_checkpoint else self.playbook
        start_epoch = int((resume_checkpoint or {}).get("epoch") or 1)
        start_step = int((resume_checkpoint or {}).get("next_step") or 1)
        start_global_step = int((resume_checkpoint or {}).get("global_step") or 0)
        epoch_answers_pre_train = list((resume_checkpoint or {}).get("epoch_answers_pre_train") or [])
        epoch_targets_pre_train = list((resume_checkpoint or {}).get("epoch_targets_pre_train") or [])
        epoch_answers_post_train = list((resume_checkpoint or {}).get("epoch_answers_post_train") or [])
        epoch_targets_post_train = list((resume_checkpoint or {}).get("epoch_targets_post_train") or [])

        def save_training_artifacts() -> None:
            results_path = os.path.join(save_path, "train_results.json")
            with open(results_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "best_accuracy": best_accuracy,
                        "results": results,
                    },
                    f,
                    indent=2,
                )

            error_logs_path = os.path.join(save_path, "val_results.json")
            with open(error_logs_path, "w", encoding="utf-8") as f:
                json.dump(error_logs, f, indent=2)

            pre_train_post_train_results_path = os.path.join(
                save_path, "pre_train_post_train_results.json"
            )
            with open(pre_train_post_train_results_path, "w", encoding="utf-8") as f:
                json.dump(pre_train_post_train_results, f, indent=2)

            final_playbook_path = os.path.join(save_path, "final_playbook.txt")
            with open(final_playbook_path, "w", encoding="utf-8") as f:
                f.write(self.playbook)

            best_playbook_path = os.path.join(save_path, "best_playbook.txt")
            with open(best_playbook_path, "w", encoding="utf-8") as f:
                f.write(self.best_playbook)

        def checkpoint(next_epoch: int, next_step_value: int, global_step: int) -> None:
            payload = {
                "epoch": next_epoch,
                "next_step": next_step_value,
                "global_step": global_step,
                "best_accuracy": best_accuracy,
                "next_global_bullet_id": self.next_global_id,
                "current_playbook": self.playbook,
                "best_playbook": self.best_playbook,
                "results": results,
                "error_logs": error_logs,
                "pre_train_post_train_results": pre_train_post_train_results,
                "epoch_answers_pre_train": epoch_answers_pre_train,
                "epoch_targets_pre_train": epoch_targets_pre_train,
                "epoch_answers_post_train": epoch_answers_post_train,
                "epoch_targets_post_train": epoch_targets_post_train,
            }
            self._persist_training_checkpoint_files(save_path, payload)

        print(f"Total epochs: {num_epochs}")
        print(f"Train samples per epoch: {len(train_samples)}")
        print(f"Val samples: {len(val_samples)}")
        print(f"Curator frequency: every {curator_frequency} steps")
        print(f"Evaluation frequency: every {eval_steps} steps\n")

        # Training loop
        for epoch in range(start_epoch, num_epochs + 1):
            print(f"\n{'=' * 60}")
            print(f"EPOCH {epoch}/{num_epochs}")
            print(f"{'=' * 60}")

            if epoch != start_epoch:
                epoch_answers_pre_train = []
                epoch_targets_pre_train = []
                epoch_answers_post_train = []
                epoch_targets_post_train = []

            for step, task_dict in enumerate(train_samples, start=1):
                if epoch == start_epoch and step < start_step:
                    continue
                print(f"\n--- Step {step}/{len(train_samples)} ---")
                current_global_step = ((epoch - 1) * len(train_samples)) + step

                target = task_dict.get("target", "")

                # Use helper method for training single sample
                pre_train_answer, post_train_answer, tracking_dict = (
                    self._train_single_sample(
                        task_dict=task_dict,
                        data_processor=data_processor,
                        step_id=f"train_e_{epoch}_s_{step}",
                        epoch=epoch,
                        step=step,
                        usage_log_path=usage_log_path,
                        log_dir=log_dir,
                        config_params=config_params,
                        total_samples=len(train_samples),
                    )
                )

                # Collect answers for accuracy calculation
                epoch_answers_pre_train.append(pre_train_answer)
                epoch_targets_pre_train.append(target)
                epoch_answers_post_train.append(post_train_answer)
                epoch_targets_post_train.append(target)

                # Track pre-train and post-train results
                pre_train_post_train_result = {
                    "epoch": epoch,
                    "step": step,
                    "target": target,
                    **tracking_dict,
                }
                pre_train_post_train_results.append(pre_train_post_train_result)

                # Save intermediate playbook
                if step % save_steps == 0:
                    intermediate_path = os.path.join(
                        playbook_dir, f"epoch_{epoch}_step_{step}_playbook.txt"
                    )
                    with open(intermediate_path, "w") as f:
                        f.write(self.playbook)
                    if checkpoint_enabled:
                        checkpoint(epoch, step + 1, current_global_step)

                # Periodic evaluation
                if step % eval_steps == 0:
                    print(f"\n{'=' * 40}")
                    print(f"EVALUATION AT EPOCH {epoch}, STEP {step}")
                    print(f"{'=' * 40}")

                    # Compute training accuracies
                    pre_train_accuracy = data_processor.evaluate_accuracy(
                        epoch_answers_pre_train, epoch_targets_pre_train
                    )
                    post_train_accuracy = data_processor.evaluate_accuracy(
                        epoch_answers_post_train, epoch_targets_post_train
                    )

                    # Validation evaluation
                    val_results = {}
                    val_error_log = {"errors": []}
                    if val_samples:
                        if self.task_type == "appworld":
                            adapter = self._get_appworld_adapter(
                                data_processor=data_processor,
                                config=config,
                                log_dir=log_dir,
                            )
                            val_results, val_error_log = adapter.run_test(
                                samples=val_samples,
                                playbook=self.playbook,
                                prefix=f"val_e{epoch}_s{step}",
                            )
                        else:
                            val_results, val_error_log = evaluate_test_set(
                                data_processor,
                                self.generator,
                                self.playbook,
                                val_samples,
                                self.max_tokens,
                                log_dir,
                                max_workers=test_workers,
                                use_json_mode=use_json_mode,
                            )

                    result = {
                        "epoch": epoch,
                        "step": step,
                        "train_result": {
                            "pre_train_accuracy": pre_train_accuracy,
                            "post_train_accuracy": post_train_accuracy,
                        },
                        "val_result": val_results,
                        "playbook_num_tokens": count_tokens(self.playbook),
                        "playbook_length": len(self.playbook),
                        "playbook_stats": get_playbook_stats(self.playbook),
                    }
                    results.append(result)
                    error_logs.append(
                        {
                            "epoch": epoch,
                            "step": step,
                            "val_results": val_results,
                            "error_log": val_error_log,
                        }
                    )

                    # Track best playbook
                    if val_results:
                        acc = val_results["accuracy"]
                        if acc > best_accuracy:
                            best_accuracy = acc
                            self.best_playbook = self.playbook
                            print(f"🎉 New best accuracy: {best_accuracy:.3f}")

                    save_training_artifacts()
                    if checkpoint_enabled:
                        checkpoint(epoch, step + 1, current_global_step)

                if stop_after_step is not None and current_global_step >= int(stop_after_step):
                    save_training_artifacts()
                    checkpoint(epoch, step + 1, current_global_step)
                    return {
                        "training_results": {"best_validation_accuracy": best_accuracy},
                        "stopped_early": True,
                    }

            # End of epoch - save final playbook
            epoch_playbook_path = os.path.join(
                playbook_dir, f"epoch_{epoch}_final_playbook.txt"
            )
            with open(epoch_playbook_path, "w") as f:
                f.write(self.playbook)
            if checkpoint_enabled:
                checkpoint(epoch + 1, 1, max(start_global_step, epoch * len(train_samples)))

        save_training_artifacts()

        print(f"\n{'=' * 60}")
        print(f"OFFLINE TRAINING COMPLETE")
        print(f"{'=' * 60}")
        print(f"Best Validation Accuracy: {best_accuracy:.3f}")
        print(f"{'=' * 60}\n")

        return {
            "training_results": {"best_validation_accuracy": best_accuracy},
            "stopped_early": False,
        }

    def test(
        self,
        test_samples: List[Dict[str, Any]],
        data_processor,
        playbook,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run testing with the playbook (backward compatibility wrapper).

        Args:
            test_samples: List of test samples
            data_processor: Data processor instance for the task
            playbook: Playbook to be used for generator
            config: Configuration dictionary

        Returns:
            Dictionary with test results
        """
        # Temporarily set the playbook
        old_playbook = self.playbook
        self.playbook = playbook

        # Use the run method
        results = self.run(
            mode="eval_only",
            test_samples=test_samples,
            data_processor=data_processor,
            config=config,
        )

        # Restore old playbook
        self.playbook = old_playbook

        # Return in the old format for backward compatibility
        return {
            "test_results": results["test_results"],
            "error_log": results.get("test_error_log", {}),
            "playbook": playbook,
        }

    def _online_train_and_test(
        self,
        test_samples: List[Dict[str, Any]],
        data_processor,
        config: Dict[str, Any],
        save_path: str,
        usage_log_path: str,
        playbook_dir: str,
        log_dir: str,
    ) -> Dict[str, Any]:
        """
        Run online training and testing

        Args:
            test_samples: List of samples to train and test on
            data_processor: Data processor instance for the task
            config: Configuration dictionary
            save_path: Path to save results
            usage_log_path: Path for bullet usage logging
            playbook_dir: Directory for intermediate playbooks
            log_dir: Directory for detailed logs

        Returns:
            Dictionary with training results, test results, and final playbook
        """
        if self.task_type == "appworld":
            adapter = self._get_appworld_adapter(
                data_processor=data_processor,
                config=config,
                log_dir=log_dir,
            )
            config_params = self._extract_config_params(config)
            save_steps = config_params["save_steps"]
            online_eval_frequency = config.get("online_eval_frequency", 100)

            train_results = []
            pre_train_post_train_results = []
            all_test_errors = []
            window_test_results = []
            correct_count = 0.0
            correct_count_sample_based = 0
            total_count = 0
            global_step = 0
            num_windows = (
                len(test_samples) + online_eval_frequency - 1
            ) // online_eval_frequency

            for window_idx in range(num_windows):
                start_idx = window_idx * online_eval_frequency
                end_idx = min(
                    (window_idx + 1) * online_eval_frequency, len(test_samples)
                )
                window_samples = test_samples[start_idx:end_idx]

                window_test_results_dict, window_test_error_log = adapter.run_test(
                    samples=window_samples,
                    playbook=self.playbook,
                    prefix=f"online_window_{window_idx + 1}",
                )

                window_accuracy = float(window_test_results_dict["accuracy"])
                window_correct = int(window_test_results_dict["correct"])
                window_total = int(window_test_results_dict["total"])
                correct_count_sample_based += window_correct
                correct_count += window_accuracy * window_total
                total_count += window_total

                for error in window_test_error_log.get("errors", []):
                    all_test_errors.append(
                        {
                            "window": window_idx + 1,
                            "global_index": start_idx + int(error.get("index", 0)),
                            "prediction": error.get("prediction"),
                            "ground_truth": error.get("ground_truth"),
                            "error": error.get("error"),
                        }
                    )

                window_test_results.append(
                    {
                        "window": window_idx + 1,
                        "start_idx": start_idx,
                        "end_idx": end_idx,
                        "window_accuracy": window_accuracy,
                        "window_correct": window_correct,
                        "window_total": window_total,
                    }
                )

                epoch_answers_pre_train = []
                epoch_targets_pre_train = []
                epoch_answers_post_train = []
                epoch_targets_post_train = []

                for local_step, task_dict in enumerate(window_samples, start=1):
                    global_step += 1
                    target = task_dict.get("target", "")

                    pre_train_answer, post_train_answer, tracking_dict = (
                        adapter.train_single_sample(
                            task_dict=task_dict,
                            step_id=f"online_train_s_{global_step}",
                            usage_log_path=usage_log_path,
                            config_params=config_params,
                            step=global_step,
                            epoch=1,
                            total_samples=len(test_samples),
                        )
                    )

                    epoch_answers_pre_train.append(pre_train_answer)
                    epoch_targets_pre_train.append(target)
                    epoch_answers_post_train.append(post_train_answer)
                    epoch_targets_post_train.append(target)

                    pre_train_post_train_results.append(
                        {
                            "window": window_idx + 1,
                            "global_step": global_step,
                            "target": target,
                            **tracking_dict,
                        }
                    )

                    if global_step % save_steps == 0:
                        intermediate_path = os.path.join(
                            playbook_dir, f"step_{global_step}_playbook.txt"
                        )
                        with open(intermediate_path, "w") as f:
                            f.write(self.playbook)

                pre_train_accuracy = data_processor.evaluate_accuracy(
                    epoch_answers_pre_train, epoch_targets_pre_train
                )
                post_train_accuracy = data_processor.evaluate_accuracy(
                    epoch_answers_post_train, epoch_targets_post_train
                )
                cumulative_test_accuracy = (
                    correct_count / total_count if total_count else 0.0
                )

                train_results.append(
                    {
                        "window": window_idx + 1,
                        "global_step": global_step,
                        "train_result": {
                            "pre_train_accuracy": pre_train_accuracy,
                            "post_train_accuracy": post_train_accuracy,
                        },
                        "cumulative_test_accuracy": cumulative_test_accuracy,
                        "playbook_num_tokens": count_tokens(self.playbook),
                        "playbook_length": len(self.playbook),
                        "playbook_stats": get_playbook_stats(self.playbook),
                    }
                )

            final_test_accuracy = correct_count / total_count if total_count else 0.0
            test_results = {
                "accuracy": final_test_accuracy,
                "correct": correct_count_sample_based,
                "total": total_count,
                "window_results": window_test_results,
            }
            test_error_log = {
                "accuracy": final_test_accuracy,
                "errors": all_test_errors,
            }

            with open(os.path.join(save_path, "test_results.json"), "w") as f:
                json.dump(
                    {
                        "test_accuracy": final_test_accuracy,
                        "test_results": test_results,
                        "test_error_log": test_error_log,
                    },
                    f,
                    indent=2,
                )
            with open(os.path.join(save_path, "train_results.json"), "w") as f:
                json.dump({"train_results": train_results}, f, indent=2)
            with open(
                os.path.join(save_path, "pre_train_post_train_results.json"), "w"
            ) as f:
                json.dump(pre_train_post_train_results, f, indent=2)
            with open(os.path.join(save_path, "final_playbook.txt"), "w") as f:
                f.write(self.playbook)

            return {
                "accuracy": final_test_accuracy,
                "correct": correct_count_sample_based,
                "total": total_count,
            }

        # Extract configuration using helper
        config_params = self._extract_config_params(config)
        num_epochs = config_params["num_epochs"]

        # Validate configuration
        if num_epochs != 1:
            raise ValueError(
                f"online_train_and_test requires num_epochs=1, got {num_epochs}"
            )

        # Extract additional parameters
        curator_frequency = config_params["curator_frequency"]
        task_name = config_params["task_name"]
        save_steps = config_params["save_steps"]
        use_json_mode = config_params["use_json_mode"]
        test_workers = config_params["test_workers"]
        online_eval_frequency = config.get(
            "online_eval_frequency", 100
        )  # Get from config

        # Initialize tracking
        train_results = []
        pre_train_post_train_results = []

        # Test tracking - accumulate across all windows
        correct_count_sample_based = 0
        correct_count = 0
        total_count = 0
        all_test_errors = []
        window_test_results = []
        print(f"Total samples: {len(test_samples)}")
        print(f"Window size: {online_eval_frequency}")
        print(
            f"Number of windows: {(len(test_samples) + online_eval_frequency - 1) // online_eval_frequency}"
        )
        print(f"Curator frequency: every {curator_frequency} steps")

        # Split samples into windows
        num_windows = (
            len(test_samples) + online_eval_frequency - 1
        ) // online_eval_frequency

        epoch = 1  # Always 1 epoch
        global_step = 0

        for window_idx in range(num_windows):
            start_idx = window_idx * online_eval_frequency
            end_idx = min((window_idx + 1) * online_eval_frequency, len(test_samples))
            window_samples = test_samples[start_idx:end_idx]

            print(f"\n{'=' * 60}")
            print(f"WINDOW {window_idx + 1}/{num_windows}")
            print(f"Samples {start_idx} to {end_idx - 1}")
            print(f"{'=' * 60}")

            # =================================================================
            # STEP 1: TEST on window with current playbook (before training)
            # =================================================================
            print(f"\n--- Testing window {window_idx + 1} with current playbook ---")

            # Use evaluate_test_set for parallel evaluation
            window_test_results_dict, window_test_error_log = evaluate_test_set(
                data_processor,
                self.generator,
                self.playbook,
                window_samples,
                self.max_tokens,
                log_dir,
                max_workers=test_workers,
                use_json_mode=use_json_mode,
            )

            # Extract results
            window_accuracy = window_test_results_dict["accuracy"]
            window_correct = window_test_results_dict["correct"]
            window_total = window_test_results_dict["total"]
            correct_count_sample_based += window_correct
            correct_count += window_accuracy * window_total
            total_count += window_total

            # Add errors with window and global index information
            for error in window_test_error_log["errors"]:
                all_test_errors.append(
                    {
                        "window": window_idx + 1,
                        "global_index": start_idx + error["index"],
                        "prediction": error["prediction"],
                        "ground_truth": error["ground_truth"],
                    }
                )

            window_test_results.append(
                {
                    "window": window_idx + 1,
                    "start_idx": start_idx,
                    "end_idx": end_idx,
                    "window_accuracy": window_accuracy,
                    "window_correct": window_correct,
                    "window_total": window_total,
                }
            )

            # Calculate cumulative test accuracy so far
            cumulative_test_accuracy = correct_count / total_count

            print(f"Window {window_idx + 1} test accuracy: {window_accuracy:.3f}")
            print(
                f"Cumulative test accuracy so far: {cumulative_test_accuracy:.3f} "
                f"({total_count} samples)"
            )

            # =================================================================
            # STEP 2: TRAIN on window (same as offline_train)
            # =================================================================
            print(f"\n--- Training on window {window_idx + 1} ---")

            epoch_answers_pre_train = []
            epoch_targets_pre_train = []
            epoch_answers_post_train = []
            epoch_targets_post_train = []

            for local_step, task_dict in enumerate(window_samples):
                global_step += 1
                local_step += 1

                print(
                    f"\n--- Window {window_idx + 1}, Step {local_step}/{len(window_samples)} "
                    f"(Global step {global_step}) ---"
                )

                target = task_dict.get("target", "")

                # Use helper method for training single sample
                pre_train_answer, post_train_answer, tracking_dict = (
                    self._train_single_sample(
                        task_dict=task_dict,
                        data_processor=data_processor,
                        step_id=f"online_train_s_{global_step}",
                        epoch=epoch,
                        step=global_step,
                        usage_log_path=usage_log_path,
                        log_dir=log_dir,
                        config_params=config_params,
                        total_samples=len(test_samples),
                    )
                )

                # Collect answers for accuracy calculation
                epoch_answers_pre_train.append(pre_train_answer)
                epoch_targets_pre_train.append(target)
                epoch_answers_post_train.append(post_train_answer)
                epoch_targets_post_train.append(target)

                # Track pre-train and post-train results
                pre_train_post_train_result = {
                    "window": window_idx + 1,
                    "global_step": global_step,
                    "target": target,
                    **tracking_dict,
                }
                pre_train_post_train_results.append(pre_train_post_train_result)

                # Save intermediate playbook
                if global_step % save_steps == 0:
                    intermediate_path = os.path.join(
                        playbook_dir, f"step_{global_step}_playbook.txt"
                    )
                    with open(intermediate_path, "w") as f:
                        f.write(self.playbook)

            # End of window - compute training accuracies for this window
            pre_train_accuracy = data_processor.evaluate_accuracy(
                epoch_answers_pre_train, epoch_targets_pre_train
            )
            post_train_accuracy = data_processor.evaluate_accuracy(
                epoch_answers_post_train, epoch_targets_post_train
            )

            window_train_result = {
                "window": window_idx + 1,
                "global_step": global_step,
                "train_result": {
                    "pre_train_accuracy": pre_train_accuracy,
                    "post_train_accuracy": post_train_accuracy,
                },
                "cumulative_test_accuracy": cumulative_test_accuracy,
                "playbook_num_tokens": count_tokens(self.playbook),
                "playbook_length": len(self.playbook),
                "playbook_stats": get_playbook_stats(self.playbook),
            }
            train_results.append(window_train_result)

            print(f"\nWindow {window_idx + 1} training complete:")
            print(f"  Pre-train accuracy: {pre_train_accuracy:.3f}")
            print(f"  Post-train accuracy: {post_train_accuracy:.3f}")

            # Save window playbook
            window_playbook_path = os.path.join(
                playbook_dir, f"window_{window_idx + 1}_final_playbook.txt"
            )
            with open(window_playbook_path, "w") as f:
                f.write(self.playbook)

        # All windows complete
        print(f"\n{'=' * 60}")
        print(f"ONLINE TRAIN AND TEST COMPLETE")
        print(f"{'=' * 60}")

        # Calculate final cumulative test accuracy
        assert total_count == len(test_samples)
        final_test_accuracy = correct_count / total_count

        test_results = {
            "accuracy": final_test_accuracy,
            "correct": correct_count_sample_based,
            "total": total_count,
            "window_results": window_test_results,
        }

        test_error_log = {"accuracy": final_test_accuracy, "errors": all_test_errors}

        # Save test results
        test_results_path = os.path.join(save_path, "test_results.json")
        with open(test_results_path, "w") as f:
            json.dump(
                {
                    "test_accuracy": final_test_accuracy,
                    "test_results": test_results,
                    "test_error_log": test_error_log,
                },
                f,
                indent=2,
            )

        # Save training results (per window)
        train_results_path = os.path.join(save_path, "train_results.json")
        with open(train_results_path, "w") as f:
            json.dump({"train_results": train_results}, f, indent=2)

        # Save pre-train/post-train results
        pre_train_post_train_results_path = os.path.join(
            save_path, "pre_train_post_train_results.json"
        )
        with open(pre_train_post_train_results_path, "w") as f:
            json.dump(pre_train_post_train_results, f, indent=2)

        # Save final playbook
        final_playbook_path = os.path.join(save_path, f"final_playbook.txt")
        with open(final_playbook_path, "w") as f:
            f.write(self.playbook)

        print(f"\n{'=' * 60}")
        print(f"ONLINE TRAINING AND TESTING COMPLETE")
        print(f"{'=' * 60}")
        print(f"Final Test Accuracy: {final_test_accuracy:.3f}")
        print(f"{'=' * 60}\n")

        return {
            "accuracy": final_test_accuracy,
            "correct": correct_count_sample_based,
            "total": total_count,
        }
