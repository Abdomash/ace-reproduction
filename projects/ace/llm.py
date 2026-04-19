"""
==============================================================================
llm.py
==============================================================================

This file contains the LLM class for the project.

"""

import json
import time
import random
from datetime import datetime
from typing import Any, Dict, Optional
import openai
from logger import log_llm_call, log_problematic_request

try:
    from opentelemetry.trace import Status, StatusCode
except Exception:
    Status = None
    StatusCode = None


_TELEMETRY_RUNTIME: Optional[Dict[str, Any]] = None


def set_telemetry_runtime(runtime: Optional[Dict[str, Any]]) -> None:
    global _TELEMETRY_RUNTIME
    _TELEMETRY_RUNTIME = runtime


def _current_tracer():
    if not _TELEMETRY_RUNTIME:
        return None
    return _TELEMETRY_RUNTIME.get("tracer")


def _set_span_error(span, error_text: str) -> None:
    if span is None:
        return
    try:
        span.set_attribute("error", True)
        span.set_attribute("error.message", error_text)
        if Status is not None and StatusCode is not None:
            span.set_status(Status(StatusCode.ERROR, error_text))
    except Exception:
        pass


NO_VISIBLE_MODEL_OUTPUT = "NO_VISIBLE_MODEL_OUTPUT"
REFLECTION_FAILED_NO_VISIBLE_OUTPUT = "REFLECTION_FAILED_NO_VISIBLE_OUTPUT"


def _usage_value(usage, field: str, default=0):
    if usage is None:
        return default
    if isinstance(usage, dict):
        return usage.get(field, default)
    return getattr(usage, field, default)


def _reasoning_token_count(usage) -> int:
    if usage is None:
        return 0
    details = _field_value(usage, "completion_tokens_details")
    if details is None:
        return 0
    return _field_value(details, "reasoning_tokens", 0) or 0


def _message_reasoning(message) -> Optional[str]:
    for field in ("reasoning", "reasoning_content"):
        value = getattr(message, field, None)
        if isinstance(value, str) and value:
            return value
    return None


def _response_usage_counts(response) -> Dict[str, int]:
    usage = getattr(response, "usage", None) if response is not None else None
    prompt_tokens = _usage_value(usage, "prompt_tokens", 0)
    completion_tokens = _usage_value(usage, "completion_tokens", 0)
    total_tokens = _usage_value(usage, "total_tokens", None)
    if total_tokens is None:
        total_tokens = prompt_tokens + completion_tokens
    return {
        "prompt_num_tokens": prompt_tokens,
        "response_num_tokens": completion_tokens,
        "total_num_tokens": total_tokens,
        "reasoning_num_tokens": _reasoning_token_count(usage),
    }


def _field_value(obj, field: str, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(field, default)
    return getattr(obj, field, default)


def _response_cost_usd(response) -> Optional[float]:
    """Extract provider-supplied cost metadata when present."""
    usage = _field_value(response, "usage")
    candidates = [
        _field_value(response, "cost"),
        _field_value(response, "cost_usd"),
        _field_value(usage, "cost"),
        _field_value(usage, "cost_usd"),
        _field_value(usage, "total_cost"),
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            return float(candidate)
        except (TypeError, ValueError):
            continue
    return None


def _failure_response_text(role: str) -> str:
    if role == "reflector":
        return REFLECTION_FAILED_NO_VISIBLE_OUTPUT
    return NO_VISIBLE_MODEL_OUTPUT


def _exception_response_text(exc: Exception) -> Optional[str]:
    response = getattr(exc, "response", None)
    if response is None:
        return None
    text = getattr(response, "text", None)
    if text:
        return str(text)
    content = getattr(response, "content", None)
    if content:
        try:
            return content.decode("utf-8", errors="replace")
        except AttributeError:
            return str(content)
    return None


def _is_malformed_provider_json(exc: Exception) -> bool:
    error_text = f"{type(exc).__name__}: {exc}".lower()
    return (
        isinstance(exc, json.JSONDecodeError)
        or "jsondecodeerror" in error_text
        or "expecting value" in error_text
        or "invalid json" in error_text
    )


def _build_failure_call_info(
    *,
    error_type: str,
    role: str,
    call_id: str,
    model: str,
    prompt: str,
    start_time: float,
    prompt_time: float,
    use_json_mode: bool,
    response=None,
    choice=None,
    exception: Optional[Exception] = None,
    message: str = "",
) -> Dict[str, Any]:
    now = datetime.now()
    finish_reason = getattr(choice, "finish_reason", None) if choice is not None else None
    native_finish_reason = (
        getattr(choice, "native_finish_reason", None) if choice is not None else None
    )
    provider_reasoning = None
    if choice is not None and getattr(choice, "message", None) is not None:
        provider_reasoning = _message_reasoning(choice.message)

    call_info = {
        "role": role,
        "call_id": call_id,
        "model": model,
        "prompt": prompt,
        "response": _failure_response_text(role),
        "error": message,
        "error_type": error_type,
        "finish_reason": finish_reason,
        "native_finish_reason": native_finish_reason,
        "prompt_time": prompt_time - start_time,
        "response_time": now.timestamp() - prompt_time,
        "total_time": now.timestamp() - start_time,
        "prompt_length": len(prompt),
        "response_length": 0,
        "provider_reasoning_length": (
            len(provider_reasoning) if isinstance(provider_reasoning, str) else 0
        ),
        "json_mode": bool(use_json_mode),
        "timestamp": now.strftime("%Y%m%d_%H%M%S_%f")[:-3],
        "datetime": now.isoformat(),
    }
    call_info.update(_response_usage_counts(response))
    cost_usd = _response_cost_usd(response)
    if cost_usd is not None:
        call_info["cost_usd"] = cost_usd

    if exception is not None:
        call_info["exception_type"] = type(exception).__name__
        call_info["exception_message"] = str(exception)
        call_info["exception_repr"] = repr(exception)
        raw_response = _exception_response_text(exception)
        if raw_response is not None:
            call_info["raw_response_body"] = raw_response

    return call_info


def _log_provider_failure(
    *,
    log_dir: Optional[str],
    call_info: Dict[str, Any],
    call_id: str,
    prompt: str,
    model: str,
    api_params: Dict[str, Any],
    exception: Exception,
    using_key_mixer: bool,
    key_mixer,
) -> None:
    if log_dir:
        log_llm_call(log_dir, call_info)
    log_problematic_request(
        call_id,
        prompt,
        model,
        api_params,
        exception,
        log_dir,
        using_key_mixer,
        key_mixer,
        failure_record=call_info,
    )


def timed_llm_call(
    client,
    api_provider,
    model,
    prompt,
    role,
    call_id,
    max_tokens=4096,
    log_dir=None,
    sleep_seconds=15,
    retries_on_timeout=1000,
    attempt=1,
    use_json_mode=False,
):
    """
    Make a timed LLM call with logging and narrow provider failure handling.

    Args:
        client: API client
        model: Model name to use
        prompt: Text prompt to send
        role: Role for logging (generator, reflector, curator)
        call_id: Unique identifier for this call (format: {train|test}_{role}_{details})
        max_tokens: Maximum tokens to generate
        log_dir: Directory for detailed logging
        sleep_seconds: Base sleep time between retries
        retries_on_timeout: Maximum number of retries for timeouts/rate limits/server errors
        attempt: Current attempt number (for recursive calls)
        use_json_mode: Whether to use JSON mode for structured output

    Returns:
        tuple: (response_text, call_info_dict)
    """
    start_time = time.time()
    prompt_time = time.time()

    print(f"[{role.upper()}] Starting call {call_id}...")

    # Check if we're using API key mixer for dynamic key rotation on retries
    using_key_mixer = False

    while True:
        span = None
        api_params = {}
        try:
            # Get client
            active_client = client

            # Prepare API call parameters
            if api_provider == "openai":
                max_tokens_key = "max_completion_tokens"
            else:
                max_tokens_key = "max_tokens"

            api_params = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                max_tokens_key: max_tokens,
            }

            # Add JSON mode if requested
            if use_json_mode:
                api_params["response_format"] = {"type": "json_object"}

            tracer = _current_tracer()
            if tracer is not None:
                span_attributes = {
                    "agent.name": role,
                    "gen_ai.operation.name": "call_llm",
                    "gen_ai.system": api_provider,
                    "gen_ai.request.model": model,
                    "ace.call_id": call_id,
                    "communication.is_in_process_call": False,
                    "llm.attempt": attempt,
                }
                span = tracer.start_span(
                    "call_llm",
                    attributes=span_attributes,
                )

            call_start = time.time()
            response = active_client.chat.completions.create(**api_params)
            call_end = time.time()

            # Check if response is valid
            if not response or not getattr(response, "choices", None):
                failure_message = "Provider returned no response object or choices"
                failure_exception = RuntimeError(failure_message)
                call_info = _build_failure_call_info(
                    error_type="empty_provider_response",
                    role=role,
                    call_id=call_id,
                    model=model,
                    prompt=prompt,
                    start_time=start_time,
                    prompt_time=prompt_time,
                    use_json_mode=use_json_mode,
                    response=response,
                    message=failure_message,
                )
                print(f"[{role.upper()}] {failure_message} for {call_id}")
                _set_span_error(span, failure_message)
                _log_provider_failure(
                    log_dir=log_dir,
                    call_info=call_info,
                    call_id=call_id,
                    prompt=prompt,
                    model=model,
                    api_params=api_params,
                    exception=failure_exception,
                    using_key_mixer=using_key_mixer,
                    key_mixer=client if using_key_mixer else None,
                )
                return _failure_response_text(role), call_info

            response_time = time.time()
            total_time = response_time - start_time
            choice = response.choices[0]
            response_content = choice.message.content
            response_reasoning = _message_reasoning(choice.message)
            response_reasoning_details_present = (
                getattr(choice.message, "reasoning_details", None) is not None
            )
            finish_reason = getattr(choice, "finish_reason", None)
            native_finish_reason = getattr(choice, "native_finish_reason", None)

            if response_content is None or response_content == "":
                failure_message = (
                    "Provider returned no visible message content"
                    if response_content is None
                    else "Provider returned empty visible message content"
                )
                failure_exception = RuntimeError(failure_message)
                call_info = _build_failure_call_info(
                    error_type="empty_provider_response",
                    role=role,
                    call_id=call_id,
                    model=model,
                    prompt=prompt,
                    start_time=start_time,
                    prompt_time=prompt_time,
                    use_json_mode=use_json_mode,
                    response=response,
                    choice=choice,
                    message=failure_message,
                )
                print(f"[{role.upper()}] {failure_message} for {call_id}")
                _set_span_error(span, failure_message)
                _log_provider_failure(
                    log_dir=log_dir,
                    call_info=call_info,
                    call_id=call_id,
                    prompt=prompt,
                    model=model,
                    api_params=api_params,
                    exception=failure_exception,
                    using_key_mixer=using_key_mixer,
                    key_mixer=client if using_key_mixer else None,
                )
                return _failure_response_text(role), call_info

            prompt_tokens = (
                getattr(response.usage, "prompt_tokens", 0)
                if getattr(response, "usage", None)
                else 0
            )
            completion_tokens = (
                getattr(response.usage, "completion_tokens", 0)
                if getattr(response, "usage", None)
                else 0
            )
            total_tokens = (
                getattr(response.usage, "total_tokens", None)
                if getattr(response, "usage", None)
                else None
            )
            if total_tokens is None:
                total_tokens = prompt_tokens + completion_tokens
            reasoning_tokens = _reasoning_token_count(getattr(response, "usage", None))
            cost_usd = _response_cost_usd(response)

            input_bytes = len(prompt.encode("utf-8"))
            output_bytes = len(response_content.encode("utf-8"))
            reasoning_bytes = (
                len(response_reasoning.encode("utf-8")) if response_reasoning else 0
            )

            if span is not None:
                span.set_attribute("gen_ai.usage.input_tokens", int(prompt_tokens))
                span.set_attribute("gen_ai.usage.output_tokens", int(completion_tokens))
                span.set_attribute("gen_ai.usage.reasoning_tokens", int(reasoning_tokens))
                span.set_attribute("gen_ai.usage.total_tokens", int(total_tokens))
                if finish_reason is not None:
                    span.set_attribute("gen_ai.response.finish_reason", str(finish_reason))
                    span.set_attribute("llm.response.finish_reason", str(finish_reason))
                if native_finish_reason is not None:
                    span.set_attribute(
                        "llm.response.native_finish_reason",
                        str(native_finish_reason),
                    )
                span.set_attribute(
                    "communication.input_message_size_bytes", int(input_bytes)
                )
                span.set_attribute(
                    "communication.visible_output_message_size_bytes",
                    int(output_bytes),
                )
                span.set_attribute(
                    "communication.output_message_size_bytes", int(output_bytes)
                )
                span.set_attribute(
                    "communication.output_reasoning_size_bytes",
                    int(reasoning_bytes),
                )
                span.set_attribute(
                    "communication.total_message_size_bytes",
                    int(input_bytes + output_bytes + reasoning_bytes),
                )
                span.set_attribute(
                    "llm.call_time_seconds", float(call_end - call_start)
                )
                if cost_usd is not None:
                    span.set_attribute("llm.cost_usd", float(cost_usd))

            call_info = {
                "role": role,
                "call_id": call_id,
                "model": model,
                "prompt": prompt,
                "response": response_content,
                "finish_reason": finish_reason,
                "native_finish_reason": native_finish_reason,
                "prompt_time": prompt_time - start_time,
                "response_time": response_time - prompt_time,
                "total_time": total_time,
                "call_time": call_end - call_start,
                "prompt_length": len(prompt),
                "response_length": len(response_content),
                "reasoning_length": len(response_reasoning) if response_reasoning else 0,
                "prompt_num_tokens": prompt_tokens,
                "response_num_tokens": completion_tokens,
                "reasoning_num_tokens": reasoning_tokens,
                "total_num_tokens": total_tokens,
                "provider_reasoning_length": (
                    len(response_reasoning) if response_reasoning else 0
                ),
                "provider_reasoning_details_present": response_reasoning_details_present,
            }
            if cost_usd is not None:
                call_info["cost_usd"] = cost_usd

            print(f"[{role.upper()}] Call {call_id} completed in {total_time:.2f}s")

            if log_dir:
                log_llm_call(log_dir, call_info)

            return response_content, call_info

        except Exception as e:
            # Check for both timeout and rate limit errors
            is_timeout = any(
                k in str(e).lower() for k in ["timeout", "timed out", "connection"]
            )
            is_rate_limit = any(
                k in str(e).lower()
                for k in ["rate limit", "429", "rate_limit_exceeded"]
            )
            is_malformed_response = _is_malformed_provider_json(e)

            # Check for server errors (500, 502, 503, etc.) that should be retried
            is_server_error = False
            if hasattr(e, "response"):
                try:
                    status_code = getattr(e.response, "status_code", None)
                    if status_code and status_code >= 500:
                        is_server_error = True
                        print(
                            f"[{role.upper()}] Server error detected: HTTP {status_code}"
                        )
                except:
                    pass

            # Also check for 500 errors in the error message itself
            if any(
                k in str(e).lower()
                for k in [
                    "500 internal server error",
                    "internal server error",
                    "502 bad gateway",
                    "503 service unavailable",
                ]
            ):
                is_server_error = True
                print(
                    f"[{role.upper()}] Server error detected in message: {str(e)[:100]}..."
                )

            # Also check for specific OpenAI exceptions
            if hasattr(openai, "RateLimitError") and isinstance(
                e, openai.RateLimitError
            ):
                is_rate_limit = True

            # Check for OpenAI InternalServerError
            if hasattr(openai, "InternalServerError") and isinstance(
                e, openai.InternalServerError
            ):
                is_server_error = True
                print(f"[{role.upper()}] OpenAI InternalServerError detected")

            if is_malformed_response:
                print(f"\n[LLM] Malformed provider JSON detected for {call_id}")
                print(f"[LLM] Exception type: {type(e).__name__}")
                print(f"[LLM] Exception message: {str(e)}")
                print(f"[LLM] JSON mode: {use_json_mode}")
                print(f"[LLM] Model: {model}")
                print(f"[LLM] Prompt length: {len(prompt)}")
                call_info = _build_failure_call_info(
                    error_type="malformed_provider_json",
                    role=role,
                    call_id=call_id,
                    model=model,
                    prompt=prompt,
                    start_time=start_time,
                    prompt_time=prompt_time,
                    use_json_mode=use_json_mode,
                    exception=e,
                    message=str(e),
                )
                _set_span_error(span, str(e))
                _log_provider_failure(
                    log_dir=log_dir,
                    call_info=call_info,
                    call_id=call_id,
                    prompt=prompt,
                    model=model,
                    api_params=api_params,
                    exception=e,
                    using_key_mixer=using_key_mixer,
                    key_mixer=client if using_key_mixer else None,
                )
                return _failure_response_text(role), call_info

            retryable_error = (
                is_timeout
                or is_rate_limit
                or is_server_error
            )

            # Retry transient provider failures before turning them into task errors.
            if retryable_error and attempt < retries_on_timeout:
                attempt += 1
                if is_rate_limit:
                    error_type = "rate limited"
                    base_sleep = sleep_seconds * 2
                elif is_server_error:
                    error_type = "server error (500+)"
                    base_sleep = sleep_seconds * 1.5
                else:
                    error_type = "timed out"
                    base_sleep = sleep_seconds
                jitter = random.uniform(0.5, 1.5)
                sleep_time = base_sleep * jitter
                if span is not None:
                    _set_span_error(span, str(e))
                    try:
                        span.add_event(
                            "retry_scheduled",
                            attributes={
                                "llm.retry.attempt": attempt,
                                "llm.retry.reason": error_type,
                                "llm.retry.sleep_seconds": float(sleep_time),
                            },
                        )
                    except Exception:
                        pass
                print(
                    f"[{role.upper()}] Call {call_id} {error_type}, sleeping "
                    f"{sleep_time:.1f}s then retrying "
                    f"({attempt}/{retries_on_timeout})..."
                )
                time.sleep(sleep_time)
                continue

            error_time = time.time()
            call_info = {
                "role": role,
                "call_id": call_id,
                "model": model,
                "prompt": prompt,
                "error": str(e),
                "total_time": error_time - start_time,
                "prompt_length": len(prompt),
                "attempt": attempt,
            }

            print(
                f"[{role.upper()}] Call {call_id} failed after {error_time - start_time:.2f}s: {e}"
            )

            _set_span_error(span, str(e))

            if log_dir:
                log_llm_call(log_dir, call_info)

            raise e
        finally:
            if span is not None:
                try:
                    span.end()
                except Exception:
                    pass
