from __future__ import annotations

import os
import sys
import importlib
from pathlib import Path
from typing import Any, Dict, Optional


_MAESTRO_IMPORTED = False
_MAESTRO_IMPORT_ERROR: Optional[str] = None

setup_jsonl_tracing = None
PsutilMetricsRecorder = None
invoke_agent_span = None
record_invoke_agent_output = None


def _repo_root_from_here() -> Path:
    return Path(__file__).resolve().parent.parent


def _try_import_maestro() -> bool:
    global _MAESTRO_IMPORTED
    global _MAESTRO_IMPORT_ERROR
    global setup_jsonl_tracing
    global PsutilMetricsRecorder
    global invoke_agent_span
    global record_invoke_agent_output

    if _MAESTRO_IMPORTED:
        return True

    try:
        from maestro.telemetry_helpers.langgraph_otel import (  # type: ignore
            PsutilMetricsRecorder as _PsutilMetricsRecorder,
            invoke_agent_span as _invoke_agent_span,
            record_invoke_agent_output as _record_invoke_agent_output,
            setup_jsonl_tracing as _setup_jsonl_tracing,
        )
    except Exception as first_exc:
        maestro_src = _repo_root_from_here() / "maestro" / "src"
        if maestro_src.exists() and str(maestro_src) not in sys.path:
            sys.path.insert(0, str(maestro_src))

        loaded_maestro = sys.modules.get("maestro")
        if loaded_maestro is not None:
            loaded_file = getattr(loaded_maestro, "__file__", "") or ""
            if not loaded_file.startswith(str(maestro_src)):
                for module_name in list(sys.modules.keys()):
                    if module_name == "maestro" or module_name.startswith("maestro."):
                        sys.modules.pop(module_name, None)

        importlib.invalidate_caches()

        try:
            from maestro.telemetry_helpers.langgraph_otel import (  # type: ignore
                PsutilMetricsRecorder as _PsutilMetricsRecorder,
                invoke_agent_span as _invoke_agent_span,
                record_invoke_agent_output as _record_invoke_agent_output,
                setup_jsonl_tracing as _setup_jsonl_tracing,
            )
        except Exception as second_exc:
            _MAESTRO_IMPORT_ERROR = f"initial import error: {first_exc}; fallback import error: {second_exc}"
            return False

    setup_jsonl_tracing = _setup_jsonl_tracing
    PsutilMetricsRecorder = _PsutilMetricsRecorder
    invoke_agent_span = _invoke_agent_span
    record_invoke_agent_output = _record_invoke_agent_output
    _MAESTRO_IMPORTED = True
    return True


def telemetry_default_interval_seconds(
    task_name: str, config: Optional[Dict[str, Any]]
) -> float:
    if config and "telemetry_metrics_interval_seconds" in config:
        return float(config["telemetry_metrics_interval_seconds"])
    return 5.0 if (task_name or "").lower() == "finer" else 15.0


def start_telemetry(
    *,
    config: Dict[str, Any],
    save_path: str,
    task_name: str,
    mode: str,
    run_id: str,
) -> Dict[str, Any]:
    telemetry_enabled = bool(config.get("telemetry_enabled", False))
    runtime: Dict[str, Any] = {
        "enabled": telemetry_enabled,
        "tracer": None,
        "provider": None,
        "trace_path": None,
        "metrics_path": None,
        "metrics_recorder": None,
        "error": None,
    }

    if not telemetry_enabled:
        return runtime

    if not _try_import_maestro():
        runtime["enabled"] = False
        runtime["error"] = (
            f"Failed to import MAESTRO telemetry helpers: {_MAESTRO_IMPORT_ERROR}"
        )
        return runtime

    telemetry_dir = Path(save_path) / "telemetry"
    telemetry_dir.mkdir(parents=True, exist_ok=True)
    metrics_interval = telemetry_default_interval_seconds(task_name, config)

    tracer, trace_path, provider = setup_jsonl_tracing(
        app_name="ace",
        service_name="ace",
        service_version="1.0.0",
        log_dir=telemetry_dir,
        run_id=run_id,
        environment=os.getenv("DEPLOYMENT_ENVIRONMENT", "local"),
        set_global_provider=False,
    )

    metrics_recorder = PsutilMetricsRecorder(
        service_name="ace",
        service_version="1.0.0",
        run_id=run_id,
        output_dir=telemetry_dir,
        environment=os.getenv("DEPLOYMENT_ENVIRONMENT", "local"),
        interval_seconds=metrics_interval,
    )
    metrics_recorder.start()

    runtime.update(
        {
            "tracer": tracer,
            "provider": provider,
            "trace_path": str(trace_path),
            "metrics_path": str(metrics_recorder.output_path),
            "metrics_recorder": metrics_recorder,
            "metrics_interval_seconds": metrics_interval,
            "task_name": task_name,
            "mode": mode,
        }
    )
    return runtime


def stop_telemetry(runtime: Optional[Dict[str, Any]]) -> None:
    if not runtime:
        return
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


def get_invoke_helpers():
    if not _MAESTRO_IMPORTED:
        _try_import_maestro()
    return invoke_agent_span, record_invoke_agent_output


def telemetry_runtime_metadata(runtime: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not runtime:
        return {"enabled": False}
    if not runtime.get("enabled"):
        return {
            "enabled": False,
            "error": runtime.get("error"),
        }
    return {
        "enabled": True,
        "trace_path": runtime.get("trace_path"),
        "metrics_path": runtime.get("metrics_path"),
        "metrics_interval_seconds": runtime.get("metrics_interval_seconds"),
        "task_name": runtime.get("task_name"),
        "mode": runtime.get("mode"),
    }
