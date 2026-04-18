"""
==============================================================================
llm.py
==============================================================================

This file contains the LLM class for the project.

"""

import json
import os
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


def _is_training_call(call_id: str) -> bool:
    return call_id.startswith("train_") or call_id.startswith("online_train_")


def _is_test_call(call_id: str) -> bool:
    return call_id.startswith("test_") or call_id.startswith("test_eval_")


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        print(f"[LLM] Ignoring invalid integer for {name}: {value!r}")
        return default


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_openrouter_request(api_provider: str) -> bool:
    if api_provider == "minimax":
        return "openrouter.ai" in os.getenv("MINIMAX_BASE_URL", "").lower()
    return False


def _reasoning_max_tokens() -> Optional[int]:
    value = os.getenv(
        "ACE_REASONING_MAX_TOKENS",
        os.getenv("ACE_OPENROUTER_REASONING_MAX_TOKENS", "4096"),
    )
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        print(f"[LLM] Ignoring invalid reasoning token budget: {value!r}")
        return 4096
    if parsed <= 0:
        return None
    return parsed


def _openrouter_reasoning_extra_body(api_provider: str) -> Optional[Dict[str, Any]]:
    if not _is_openrouter_request(api_provider):
        return None

    max_tokens = _reasoning_max_tokens()
    if max_tokens is None:
        return None

    reasoning: Dict[str, Any] = {"max_tokens": max_tokens}

    effort = os.getenv("ACE_REASONING_EFFORT")
    if effort:
        reasoning["effort"] = effort

    if os.getenv("ACE_REASONING_EXCLUDE") is not None:
        reasoning["exclude"] = _env_flag("ACE_REASONING_EXCLUDE")

    return {"reasoning": reasoning}


def _usage_value(usage, field: str, default=0):
    if usage is None:
        return default
    return getattr(usage, field, default)


def _reasoning_token_count(usage) -> int:
    if usage is None:
        return 0
    details = getattr(usage, "completion_tokens_details", None)
    if details is None:
        return 0
    return getattr(details, "reasoning_tokens", 0) or 0


def _jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if hasattr(value, "model_dump"):
        try:
            return _jsonable(value.model_dump())
        except Exception:
            pass
    return str(value)


def _message_reasoning(message) -> Optional[str]:
    for field in ("reasoning", "reasoning_content"):
        value = getattr(message, field, None)
        if isinstance(value, str) and value:
            return value
    return None


def timed_llm_call(
    client,
    api_provider,
    model,
    prompt,
    role,
    call_id,
    max_tokens=8192,
    log_dir=None,
    sleep_seconds=15,
    retries_on_timeout=1000,
    attempt=1,
    use_json_mode=False,
):
    """
    Make a timed LLM call with error handling and retry logic.

    EMPTY RESPONSE HANDLING STRATEGY:
    - Training calls (call_id starts with 'train_'): Skip the entire training sample
    - Test calls (call_id starts with 'test_'): Mark as incorrect (return wrong answers)
    - All empty responses are logged to problematic_requests/ for SambaNova support analysis

    For test calls specifically: Returns "INCORRECT_DUE_TO_EMPTY_RESPONSE" repeated 4 times
    (comma-separated) to handle the 4-question format used in financial NER evaluation.

    Args:
        client: API client
        model: Model name to use
        prompt: Text prompt to send
        role: Role for logging (generator, reflector, curator)
        call_id: Unique identifier for this call (format: {train|test}_{role}_{details})
        max_tokens: Maximum tokens to generate
        log_dir: Directory for detailed logging
        sleep_seconds: Base sleep time between retries
        retries_on_timeout: Maximum number of retries for timeouts/rate limits/empty responses
        attempt: Current attempt number (for recursive calls)
        use_json_mode: Whether to use JSON mode for structured output

    Returns:
        tuple: (response_text, call_info_dict)

    Special return values for empty responses:
        - Training: ("INCORRECT_DUE_TO_EMPTY_RESPONSE, INCORRECT_DUE_TO_EMPTY_RESPONSE, ...", call_info)
        - Testing: ("INCORRECT_DUE_TO_EMPTY_RESPONSE, INCORRECT_DUE_TO_EMPTY_RESPONSE, ...", call_info)
    """
    start_time = time.time()
    prompt_time = time.time()

    print(f"[{role.upper()}] Starting call {call_id}...")

    # Check if we're using API key mixer for dynamic key rotation on retries
    using_key_mixer = False

    while True:
        span = None
        reasoning_config = None
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

            reasoning_extra_body = _openrouter_reasoning_extra_body(api_provider)
            if reasoning_extra_body:
                api_params["extra_body"] = reasoning_extra_body
                reasoning_config = reasoning_extra_body.get("reasoning")

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
                if reasoning_config:
                    span_attributes["llm.reasoning.enabled"] = True
                    span_attributes["llm.reasoning.max_tokens"] = int(
                        reasoning_config.get("max_tokens", 0)
                    )
                span = tracer.start_span(
                    "call_llm",
                    attributes=span_attributes,
                )

            call_start = time.time()
            response = active_client.chat.completions.create(**api_params)
            call_end = time.time()

            # Check if response is valid
            if not response or not response.choices or len(response.choices) == 0:
                raise Exception("Empty response from API")

            response_time = time.time()
            total_time = response_time - start_time
            choice = response.choices[0]
            response_content = choice.message.content
            response_reasoning = _message_reasoning(choice.message)
            response_reasoning_details = _jsonable(
                getattr(choice.message, "reasoning_details", None)
            )
            finish_reason = getattr(choice, "finish_reason", None)
            native_finish_reason = getattr(choice, "native_finish_reason", None)

            if response_content is None:
                reasoning_chars = (
                    len(response_reasoning)
                    if isinstance(response_reasoning, str)
                    else 0
                )
                usage = getattr(response, "usage", None)
                raise Exception(
                    "API returned None content "
                    f"(finish_reason={finish_reason}, "
                    f"native_finish_reason={native_finish_reason}, "
                    f"completion_tokens={_usage_value(usage, 'completion_tokens', 0)}, "
                    f"reasoning_tokens={_reasoning_token_count(usage)}, "
                    f"reasoning_chars={reasoning_chars})"
                )
            if response_content == "":
                usage = getattr(response, "usage", None)
                raise Exception(
                    "API returned empty content "
                    f"(finish_reason={finish_reason}, "
                    f"completion_tokens={_usage_value(usage, 'completion_tokens', 0)}, "
                    f"reasoning_tokens={_reasoning_token_count(usage)})"
                )

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

            call_info = {
                "role": role,
                "call_id": call_id,
                "model": model,
                "prompt": prompt,
                "response": response_content,
                "reasoning": response_reasoning,
                "reasoning_details": response_reasoning_details,
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
                "reasoning_enabled": bool(reasoning_config),
                "reasoning_max_tokens": (
                    reasoning_config.get("max_tokens") if reasoning_config else None
                ),
            }

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
            is_empty_response = (
                "empty response" in str(e).lower()
                or "api returned none content" in str(e).lower()
                or "api returned empty content" in str(e).lower()
            )
            is_malformed_response = (
                isinstance(e, json.JSONDecodeError)
                or "jsondecodeerror" in type(e).__name__.lower()
                or "expecting value" in str(e).lower()
            )

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

            # Debug empty response issues
            if is_empty_response or is_malformed_response:
                debug_label = (
                    "Empty response"
                    if is_empty_response
                    else "Malformed API response"
                )
                print(f"\n🚨 DEBUG: {debug_label} detected for {call_id}")
                print(f"📝 Exception type: {type(e).__name__}")
                print(f"📝 Exception message: {str(e)}")
                print(f"📝 Using JSON mode: {use_json_mode}")
                print(f"📝 Model: {model}")
                print(f"📝 Prompt length: {len(prompt)}")
                print(f"📝 Prompt preview (first 500 chars):")
                print(f"    {prompt[:500]}...")
                print(f"📝 Full exception details: {repr(e)}")
                if hasattr(e, "response"):
                    print(f"📝 Raw response object: {e.response}")
                    if hasattr(e.response, "text"):
                        print(f"📝 Raw response text: {e.response.text}")
                    if hasattr(e.response, "content"):
                        print(f"📝 Raw response content: {e.response.content}")
                print("-" * 60)
                if not is_empty_response:
                    print(
                        f"[{role.upper()}] {debug_label} will be treated as "
                        "retryable provider/transport failure"
                    )

                # Log the problematic request once per failed attempt.
                log_problematic_request(
                    call_id,
                    prompt,
                    model,
                    api_params,
                    e,
                    log_dir,
                    using_key_mixer,
                    client if using_key_mixer else None,
                )

            retryable_error = (
                is_timeout
                or is_rate_limit
                or is_server_error
                or is_empty_response
                or is_malformed_response
            )
            max_attempts_for_error = retries_on_timeout
            if is_empty_response:
                max_attempts_for_error = min(
                    retries_on_timeout, _env_int("ACE_EMPTY_RESPONSE_MAX_ATTEMPTS", 3)
                )
            elif is_malformed_response:
                max_attempts_for_error = min(
                    retries_on_timeout,
                    _env_int("ACE_MALFORMED_RESPONSE_MAX_ATTEMPTS", 3),
                )

            # Retry transient provider failures before turning them into task errors.
            if retryable_error and attempt < max_attempts_for_error:
                attempt += 1
                if is_rate_limit:
                    error_type = "rate limited"
                    base_sleep = sleep_seconds * 2
                elif is_server_error:
                    error_type = "server error (500+)"
                    base_sleep = sleep_seconds * 1.5
                elif is_malformed_response:
                    error_type = "returned malformed API JSON"
                    base_sleep = sleep_seconds
                elif is_empty_response:
                    error_type = "returned empty response"
                    base_sleep = sleep_seconds
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
                    f"({attempt}/{max_attempts_for_error})..."
                )
                time.sleep(sleep_time)
                continue

            # For empty responses, we handle differently based on context
            if is_empty_response:
                # Check if this is a training or test call to decide behavior
                if _is_training_call(call_id):
                    # In training: Mark as incorrect answer (same as testing)
                    print(
                        f"[{role.upper()}] 🚨 Empty response in training - marking as INCORRECT for {call_id}"
                    )
                    error_time = time.time()
                    call_info = {
                        "role": role,
                        "call_id": call_id,
                        "model": model,
                        "prompt": prompt,
                        "error": "TRAINING_INCORRECT: " + str(e),
                        "total_time": error_time - start_time,
                        "prompt_length": len(prompt),
                        "response_length": 0,
                        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3],
                        "datetime": datetime.now().isoformat(),
                        "training_marked_incorrect_due_to_empty_response": True,
                        "reasoning_enabled": bool(reasoning_config),
                        "reasoning_max_tokens": (
                            reasoning_config.get("max_tokens")
                            if reasoning_config
                            else None
                        ),
                    }
                    if log_dir:
                        log_llm_call(log_dir, call_info)

                    _set_span_error(span, str(e))

                    # Return a response that will be marked as incorrect
                    # For the 4-question format, we return 4 wrong answers
                    incorrect_response = "INCORRECT_DUE_TO_EMPTY_RESPONSE, INCORRECT_DUE_TO_EMPTY_RESPONSE, INCORRECT_DUE_TO_EMPTY_RESPONSE, INCORRECT_DUE_TO_EMPTY_RESPONSE"
                    return incorrect_response, call_info

                elif _is_test_call(call_id):
                    # In testing: Treat as incorrect answer
                    print(
                        f"[{role.upper()}] 🚨 Empty response in testing - marking as INCORRECT for {call_id}"
                    )
                    error_time = time.time()
                    call_info = {
                        "role": role,
                        "call_id": call_id,
                        "model": model,
                        "prompt": prompt,
                        "error": "TEST_INCORRECT: " + str(e),
                        "total_time": error_time - start_time,
                        "prompt_length": len(prompt),
                        "response_length": 0,
                        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3],
                        "datetime": datetime.now().isoformat(),
                        "test_marked_incorrect_due_to_empty_response": True,
                        "reasoning_enabled": bool(reasoning_config),
                        "reasoning_max_tokens": (
                            reasoning_config.get("max_tokens")
                            if reasoning_config
                            else None
                        ),
                    }
                    if log_dir:
                        log_llm_call(log_dir, call_info)

                    _set_span_error(span, str(e))

                    # Return a response that will be marked as incorrect
                    # For the 4-question format, we return 4 wrong answers
                    incorrect_response = "INCORRECT_DUE_TO_EMPTY_RESPONSE, INCORRECT_DUE_TO_EMPTY_RESPONSE, INCORRECT_DUE_TO_EMPTY_RESPONSE, INCORRECT_DUE_TO_EMPTY_RESPONSE"
                    return incorrect_response, call_info

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
                "reasoning_enabled": bool(reasoning_config),
                "reasoning_max_tokens": (
                    reasoning_config.get("max_tokens") if reasoning_config else None
                ),
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
