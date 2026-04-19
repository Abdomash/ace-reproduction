from __future__ import annotations

import json
import os
import re
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from appworld.common.path_store import path_store


def _make_real_time_helpers() -> dict:
    try:
        from freezegun.api import (
            real_time_ns as _real_time_ns,
            real_perf_counter as _real_perf_counter,
        )

        return {"time_ns": _real_time_ns, "perf_counter": _real_perf_counter}
    except ImportError:
        pass
    _helpers: dict = {}
    _helpers["time_ns"] = time.time_ns
    _helpers["perf_counter"] = time.perf_counter
    return _helpers


_REAL_TIME: dict = _make_real_time_helpers()


def _real_time_ns() -> int:
    return _REAL_TIME["time_ns"]()


def _real_perf_counter() -> float:
    return _REAL_TIME["perf_counter"]()


_RUNTIME: dict[str, Any] = {
    "enabled": False,
    "tracer": None,
    "provider": None,
    "metrics_recorder": None,
    "trace_path": None,
    "metrics_path": None,
    "error": None,
}
_MAESTRO_IMPORTED = False

setup_jsonl_tracing = None
PsutilMetricsRecorder = None
estimate_message_bytes = None
Status = None
StatusCode = None


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _repo_root_candidates() -> list[Path]:
    here = Path(__file__).resolve()
    candidates = []
    for parent in here.parents:
        candidates.append(parent)
        if parent.name == "ace-appworld":
            candidates.append(parent.parent)
    return candidates


def _try_import_maestro() -> bool:
    global _MAESTRO_IMPORTED
    global setup_jsonl_tracing
    global PsutilMetricsRecorder
    global estimate_message_bytes
    global Status
    global StatusCode

    if _MAESTRO_IMPORTED:
        return True

    for candidate in _repo_root_candidates():
        maestro_src = candidate / "maestro" / "src"
        if maestro_src.exists() and str(maestro_src) not in sys.path:
            sys.path.insert(0, str(maestro_src))

    try:
        from maestro.telemetry_helpers.langgraph_otel import (  # type: ignore
            PsutilMetricsRecorder as _PsutilMetricsRecorder,
            estimate_message_bytes as _estimate_message_bytes,
            setup_jsonl_tracing as _setup_jsonl_tracing,
        )
        from opentelemetry.trace import Status as _Status
        from opentelemetry.trace import StatusCode as _StatusCode
    except Exception as exc:
        _RUNTIME["error"] = str(exc)
        return False

    setup_jsonl_tracing = _setup_jsonl_tracing
    PsutilMetricsRecorder = _PsutilMetricsRecorder
    estimate_message_bytes = _estimate_message_bytes
    Status = _Status
    StatusCode = _StatusCode
    _MAESTRO_IMPORTED = True
    return True


def _safe_run_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned or "appworld"


def telemetry_enabled_by_default() -> bool:
    return _env_flag(
        "APPWORLD_MAESTRO_TELEMETRY",
        _env_flag("MAESTRO_TELEMETRY_ENABLED", True),
    )


def start_telemetry(
    *,
    experiment_name: str,
    runner_type: str,
    run_type: str | None,
    dataset_name: str | None,
    task_id: str | None,
    num_processes: int,
    process_index: int,
) -> dict[str, Any]:
    """Start MAESTRO JSONL tracing/metrics for an AppWorld ACE run."""

    if not telemetry_enabled_by_default():
        _RUNTIME.update({"enabled": False, "error": None})
        return _RUNTIME

    if not _try_import_maestro():
        _RUNTIME["enabled"] = False
        return _RUNTIME

    run_label = experiment_name
    if task_id:
        run_label += f"_{task_id}"
    if num_processes and num_processes > 1:
        run_label += f"_p{process_index}_of_{num_processes}"
    run_id = _safe_run_id(run_label)

    telemetry_dir = Path(path_store.experiment_outputs) / experiment_name / "telemetry"
    telemetry_dir.mkdir(parents=True, exist_ok=True)
    interval = float(os.getenv("APPWORLD_MAESTRO_METRICS_INTERVAL_SECONDS", "15"))

    tracer, trace_path, provider = setup_jsonl_tracing(
        app_name="ace-appworld",
        service_name="ace-appworld",
        service_version="1.0.0",
        log_dir=telemetry_dir,
        run_id=run_id,
        environment=os.getenv("DEPLOYMENT_ENVIRONMENT", "local"),
        set_global_provider=False,
    )
    metrics_recorder = PsutilMetricsRecorder(
        service_name="ace-appworld",
        service_version="1.0.0",
        run_id=run_id,
        output_dir=telemetry_dir,
        environment=os.getenv("DEPLOYMENT_ENVIRONMENT", "local"),
        interval_seconds=interval,
    )
    metrics_recorder.start()

    _RUNTIME.update(
        {
            "enabled": True,
            "tracer": tracer,
            "provider": provider,
            "metrics_recorder": metrics_recorder,
            "trace_path": str(trace_path),
            "metrics_path": str(metrics_recorder.output_path),
            "run_id": run_id,
            "experiment_name": experiment_name,
            "runner_type": runner_type,
            "run_type": run_type,
            "dataset_name": dataset_name,
            "task_id": task_id,
            "num_processes": num_processes,
            "process_index": process_index,
            "metrics_interval_seconds": interval,
            "error": None,
        }
    )
    metadata_path = telemetry_dir / f"metadata_{run_id}.json"
    metadata_path.write_text(
        json.dumps(
            {
                k: v
                for k, v in _RUNTIME.items()
                if k not in {"tracer", "provider", "metrics_recorder"}
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return _RUNTIME


def stop_telemetry(runtime: dict[str, Any] | None = None) -> None:
    runtime = runtime or _RUNTIME
    recorder = runtime.get("metrics_recorder")
    if recorder is not None:
        try:
            recorder.stop()
        except Exception:
            pass
    provider = runtime.get("provider")
    if provider is not None:
        try:
            provider.shutdown()
        except Exception:
            pass


def current_runtime() -> dict[str, Any]:
    return _RUNTIME


def _message_bytes(value: Any) -> int:
    if estimate_message_bytes is not None:
        try:
            return int(estimate_message_bytes(value))
        except Exception:
            return 0
    try:
        return len(str(value).encode("utf-8"))
    except Exception:
        return 0


@contextmanager
def telemetry_span(
    span_name: str,
    *,
    agent_name: str,
    operation_name: str,
    payload: Any | None = None,
    attributes: dict[str, Any] | None = None,
    in_process_call: bool = True,
) -> Iterator[Any]:
    tracer = _RUNTIME.get("tracer")
    wall_start = _real_perf_counter()
    if not _RUNTIME.get("enabled") or tracer is None:
        try:
            yield None
        finally:
            pass
        return

    span_attributes = {
        "agent.name": agent_name,
        "gen_ai.operation.name": operation_name,
    }
    if attributes:
        span_attributes.update(attributes)

    with tracer.start_as_current_span(
        span_name, start_time=_real_time_ns(), end_on_exit=False, attributes=span_attributes
    ) as span:
        span.set_attribute("communication.is_in_process_call", in_process_call)
        input_bytes = 0
        if payload is not None:
            input_bytes = _message_bytes(payload)
            span.set_attribute("communication.input_message_size_bytes", input_bytes)
            span.set_attribute("communication.total_message_size_bytes", input_bytes)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            if Status is not None and StatusCode is not None:
                span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.set_attribute("agent.failure.category", "system")
            span.set_attribute("agent.failure.reason", str(exc))
            raise
        finally:
            wall_seconds = _real_perf_counter() - wall_start
            span.set_attribute("wall_time_seconds", wall_seconds)
            span.set_attribute("duration.wall_time_seconds", wall_seconds)
            span.end(end_time=_real_time_ns())


def record_span_output(span: Any, output: Any) -> None:
    if span is None:
        return
    input_bytes = int(span.attributes.get("communication.input_message_size_bytes", 0))
    output_bytes = _message_bytes(output)
    span.set_attribute("communication.output_message_size_bytes", output_bytes)
    span.set_attribute("communication.total_message_size_bytes", input_bytes + output_bytes)


def record_llm_response(span: Any, arguments: dict[str, Any], response: dict[str, Any]) -> None:
    if span is None:
        return
    usage = response.get("usage") if isinstance(response, dict) else None
    if isinstance(usage, dict):
        prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        details = usage.get("completion_tokens_details") or {}
        reasoning_tokens = int(
            details.get("reasoning_tokens")
            or usage.get("reasoning_tokens")
            or usage.get("internal_reasoning_tokens")
            or 0
        )
        total_tokens = usage.get("total_tokens")
        if total_tokens is None:
            total_tokens = prompt_tokens + completion_tokens
        span.set_attribute("gen_ai.usage.input_tokens", prompt_tokens)
        span.set_attribute("gen_ai.usage.output_tokens", completion_tokens)
        span.set_attribute("gen_ai.usage.reasoning_tokens", reasoning_tokens)
        span.set_attribute("gen_ai.usage.total_tokens", int(total_tokens))
    if "prompt_num_tokens" in response:
        span.set_attribute("gen_ai.usage.input_tokens", int(response.get("prompt_num_tokens") or 0))
        span.set_attribute(
            "gen_ai.usage.output_tokens", int(response.get("response_num_tokens") or 0)
        )
        span.set_attribute(
            "gen_ai.usage.reasoning_tokens", int(response.get("reasoning_num_tokens") or 0)
        )
        span.set_attribute("gen_ai.usage.total_tokens", int(response.get("total_num_tokens") or 0))
    if "cost_usd" in response:
        span.set_attribute("llm.cost_usd", float(response.get("cost_usd") or 0.0))
        span.set_attribute("llm.cost.usd", float(response.get("cost_usd") or 0.0))
    elif "cost" in response:
        span.set_attribute("llm.cost.usd", float(response.get("cost") or 0.0))
    if "cost_source" in response:
        span.set_attribute("llm.cost_source", str(response.get("cost_source")))
    if "wall_time_seconds" in response:
        span.set_attribute("llm.call_time_seconds", float(response.get("wall_time_seconds") or 0.0))
        span.set_attribute("llm.wall_time_seconds", float(response.get("wall_time_seconds") or 0.0))
    if "model" in arguments:
        span.set_attribute("gen_ai.request.model", str(arguments["model"]))
    record_span_output(span, response)
