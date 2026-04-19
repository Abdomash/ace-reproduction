#!/usr/bin/env python3
import os
import re
import json
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

import openai
import tiktoken
from dotenv import load_dotenv
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load environment variables from .env file
load_dotenv()


SUPPORTED_API_PROVIDERS = ("sambanova", "together", "openai", "openrouter")
OPENROUTER_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


def _reject_deprecated_provider(api_provider: str) -> None:
    if api_provider == "minimax":
        raise ValueError(
            "api_provider='minimax' is deprecated. Use api_provider='openrouter' "
            "with model 'minimax/minimax-m2.7'."
        )


def sanitized_base_url_label(base_url: str) -> str:
    """Return a non-secret base URL label for run metadata."""
    parts = urlsplit(base_url)
    hostname = parts.hostname or ""
    netloc = hostname
    if parts.port:
        netloc = f"{netloc}:{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path.rstrip("/"), "", ""))


def _provider_settings(api_provider: str) -> Dict[str, Any]:
    _reject_deprecated_provider(api_provider)
    if api_provider == "sambanova":
        base_url = "https://api.sambanova.ai/v1"
        api_key = os.getenv("SAMBANOVA_API_KEY", "")
        if not api_key:
            raise ValueError("SambaNova api key not found in environment variables")
        default_headers = None
    elif api_provider == "together":
        base_url = "https://api.together.xyz/v1"
        api_key = os.getenv("TOGETHER_API_KEY", "")
        if not api_key:
            raise ValueError("Together api key not found in environment variables")
        default_headers = None
    elif api_provider == "openai":
        base_url = "https://api.openai.com/v1"
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OpenAI api key not found in environment variables")
        default_headers = None
    elif api_provider == "openrouter":
        base_url = os.getenv("OPENROUTER_BASE_URL", OPENROUTER_DEFAULT_BASE_URL)
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            raise ValueError("OpenRouter api key not found in OPENROUTER_API_KEY")
        default_headers = {}
        http_referer = os.getenv("OPENROUTER_HTTP_REFERER")
        app_title = os.getenv("OPENROUTER_APP_TITLE")
        if http_referer:
            default_headers["HTTP-Referer"] = http_referer
        if app_title:
            default_headers["X-Title"] = app_title
    else:
        raise ValueError(
            (
                f"Invalid api_provider name: {api_provider}. "
                f"Must be one of {SUPPORTED_API_PROVIDERS}"
            )
        )
    return {
        "api_provider": api_provider,
        "api_key": api_key,
        "base_url": base_url,
        "base_url_label": sanitized_base_url_label(base_url),
        "default_headers": default_headers,
    }


def provider_metadata(api_provider: str) -> Dict[str, Any]:
    """Return provider metadata safe to write to run artifacts."""
    settings = _provider_settings(api_provider)
    return {
        "api_provider": settings["api_provider"],
        "base_url_label": settings["base_url_label"],
        "default_header_names": sorted((settings.get("default_headers") or {}).keys()),
    }


def initialize_client(api_provider: str):
    """Initialize one OpenAI-compatible client for the selected provider."""
    settings = _provider_settings(api_provider)
    kwargs = {
        "api_key": settings["api_key"],
        "base_url": settings["base_url"],
    }
    if settings.get("default_headers"):
        kwargs["default_headers"] = settings["default_headers"]
    return openai.OpenAI(**kwargs)


def initialize_clients(
    api_provider,
    generator_provider=None,
    reflector_provider=None,
    curator_provider=None,
):
    """Initialize separate clients for generator, reflector, and curator."""
    generator_provider = generator_provider or api_provider
    reflector_provider = reflector_provider or api_provider
    curator_provider = curator_provider or api_provider

    generator_client = initialize_client(generator_provider)
    reflector_client = initialize_client(reflector_provider)
    curator_client = initialize_client(curator_provider)

    print(
        "Using API providers: "
        f"generator={generator_provider}, "
        f"reflector={reflector_provider}, curator={curator_provider}"
    )
    return generator_client, reflector_client, curator_client


def pricing_snapshot(models: Dict[str, str]) -> Dict[str, Any]:
    """Record the pricing basis without hard-coding volatile provider prices."""
    return {
        "source": (
            "OpenRouter/OpenAI-compatible response usage and cost metadata when "
            "available; no hard-coded final prices."
        ),
        "source_date": os.getenv("ACE_PRICING_SOURCE_DATE", datetime.now().date().isoformat()),
        "models": {
            role: {
                "model": model,
                "input_usd_per_million_tokens": None,
                "output_usd_per_million_tokens": None,
            }
            for role, model in models.items()
        },
    }


def get_section_slug(section_name):
    """Convert section name to slug format (3-5 chars)"""
    # Common section mappings - updated to match original sections
    slug_map = {
        "financial_strategies_and_insights": "fin",
        "formulas_and_calculations": "calc",
        "code_snippets_and_templates": "code",
        "common_mistakes_to_avoid": "err",
        "problem_solving_heuristics": "prob",
        "context_clues_and_indicators": "ctx",
        "strategies_and_hard_rules": "str",
        "apis_to_use_for_specific_information": "api",
        "useful_code_snippets_and_templates": "code",
        "common_mistakes_and_correct_strategies": "mis",
        "problem_solving_heuristics_and_workflows": "heur",
        "verification_checklist": "veri",
        "troubleshooting_and_pitfalls": "trou",
        "others": "misc",
        "meta_strategies": "meta",
    }

    # Clean and convert to snake_case
    clean_name = section_name.lower().strip().replace(" ", "_").replace("&", "and")

    if clean_name in slug_map:
        return slug_map[clean_name]

    # Generate slug from first letters
    words = clean_name.split("_")
    if len(words) == 1:
        return words[0][:4]
    else:
        return "".join(w[0] for w in words[:5])


def extract_boxed_content(text):
    """Helper function to extract content from \\boxed{} format"""
    pattern = r"\\boxed\{"
    match = re.search(pattern, text)
    if not match:
        return None

    start = match.end() - 1  # Position of opening brace
    brace_count = 0
    i = start

    while i < len(text):
        if text[i] == "{":
            brace_count += 1
        elif text[i] == "}":
            brace_count -= 1
            if brace_count == 0:
                return text[start + 1 : i]  # Content between braces
        i += 1
    return None


def extract_answer(response):
    """Extract final answer from model response"""
    if response in {
        "NO_VISIBLE_MODEL_OUTPUT",
        "REFLECTION_FAILED_NO_VISIBLE_OUTPUT",
    }:
        return response

    try:
        # First try JSON parsing
        parsed = json.loads(response)
        answer = str(parsed.get("final_answer", "No final answer found"))
        return answer

    except (json.JSONDecodeError, KeyError, AttributeError):
        # JSON parsing failed, use fallback logic
        matches = re.findall(r"Finish\[(.*?)\]", response)
        if matches:
            answer = matches[-1]
            return answer

        # Try to get final answer from JSON style response with regex matching
        # Try double quotes first
        matches = re.findall(r'"final_answer"\s*:\s*"([^"]*)"', response)
        if matches:
            answer = matches[-1]
            return answer

        # Try single quotes
        matches = re.findall(r"'final_answer'\s*:\s*'([^']*)'", response)
        if matches:
            answer = matches[-1]
            return answer

        # Handle JSON format without quotes (for simple expressions)
        matches = re.findall(r'[\'"]final_answer[\'"]\s*:\s*([^,}]+)', response)
        if matches:
            answer = matches[-1].strip()
            # Clean up trailing characters
            answer = re.sub(r"[,}]*$", "", answer)
            return answer

        # Fallback for "The final answer is: X" pattern with boxed
        final_answer_pattern = r"[Tt]he final answer is:?\s*\$?\\boxed\{"
        match = re.search(final_answer_pattern, response)
        if match:
            # Extract boxed content starting from this match
            remaining_text = response[match.start() :]
            boxed_content = extract_boxed_content(remaining_text)
            if boxed_content:
                return boxed_content

        # More general pattern for "final answer is X"
        matches = re.findall(r"[Tt]he final answer is:?\s*([^\n.]+)", response)
        if matches:
            answer = matches[-1].strip()
            # Clean up common formatting
            answer = re.sub(r"^\$?\\boxed\{([^}]+)\}\$?$", r"\1", answer)
            answer = answer.replace("$", "").strip()
            if answer:
                return answer

        return "No final answer found"


enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(prompt: str) -> int:
    return len(enc.encode(prompt))


def evaluate_single_test_sample(args_tuple, data_processor) -> Tuple[Dict, str]:
    """
    Evaluate a single test sample - task-agnostic implementation.

    Args:
        args_tuple: Tuple of (index, task_dict, generator, playbook, max_tokens, log_dir, use_json_mode)
        data_processor: DataProcessor instance with answer_is_correct method
    """
    (i, task_dict, generator, playbook, max_tokens, log_dir, use_json_mode) = args_tuple
    target = task_dict.get("target", "")
    try:
        context = task_dict["context"]
        question = task_dict["question"]

        gen_response, bullet_ids, call_info = generator.generate(
            question=question,
            playbook=playbook,
            context=context,
            reflection="(empty)",
            use_json_mode=use_json_mode,
            call_id=f"test_eval_{i}",
            log_dir=log_dir,
        )

        final_answer = extract_answer(gen_response)
        is_correct = data_processor.answer_is_correct(final_answer, target)

        return {
            "index": i,
            "final_answer": final_answer,
            "target": target,
            "is_correct": is_correct,
            "success": True,
            "error_type": (
                call_info.get("error_type") if isinstance(call_info, dict) else None
            ),
            "error": call_info.get("error") if isinstance(call_info, dict) else None,
        }, None

    except Exception as e:
        return {
            "index": i,
            "final_answer": "NO_VISIBLE_MODEL_OUTPUT",
            "target": target,
            "is_correct": False,
            "success": True,
            "error_type": "provider_call_exception",
            "error": f"{type(e).__name__}: {str(e)}",
        }, f"Error evaluating sample {i}: {type(e).__name__}: {str(e)}"


def evaluate_test_set(
    data_processor,
    generator,
    playbook,
    test_samples,
    max_tokens=4096,
    log_dir=None,
    max_workers=20,
    use_json_mode=False,
) -> Tuple[Dict, Dict]:
    """
    Parallel evaluation of test set - task-agnostic implementation.

    Args:
        data_processor: DataProcessor instance with answer_is_correct and evaluate_accuracy methods
        generator: Generator instance
        playbook: Current playbook string
        test_samples: List of test samples
        max_tokens: Max tokens for generation
        log_dir: Directory for logs
        max_workers: Number of parallel workers
        use_json_mode: Whether to use JSON mode

    Returns:
        Tuple of (results_dict, error_logs_dict)
    """
    print(f"\n{'=' * 40}")
    print(f"EVALUATING TEST SET - {len(test_samples)} samples, {max_workers} workers")
    print(f"{'=' * 40}")

    args_list = [
        (i, sample, generator, playbook, max_tokens, log_dir, use_json_mode)
        for i, sample in enumerate(test_samples)
    ]

    results = {
        "correct": 0,
        "total": 0,
        "no_answer": 0,
        "answers": [],
        "targets": [],
        "errors": [],
    }

    # Use a wrapper to pass data_processor to the evaluation function
    def eval_wrapper(args_tuple):
        return evaluate_single_test_sample(args_tuple, data_processor)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_args = {
            executor.submit(eval_wrapper, args): args for args in args_list
        }

        for i, future in enumerate(as_completed(future_to_args), 1):
            result, error = future.result()

            if error:
                print(error)

            if result and result["success"]:
                results["correct"] += 1 if result["is_correct"] else 0
                results["total"] += 1
                results["answers"].append(result["final_answer"])
                results["targets"].append(result["target"])

                if not result["is_correct"]:
                    results["errors"].append(
                        {
                            "index": result["index"],
                            "prediction": result["final_answer"],
                            "ground_truth": result["target"],
                            "error_type": result.get("error_type"),
                            "error": result.get("error") or error,
                        }
                    )

                if result["final_answer"] in {
                    "No final answer found",
                    "NO_VISIBLE_MODEL_OUTPUT",
                }:
                    results["no_answer"] += 1

            if i % 50 == 0:
                curr_acc = (
                    results["correct"] / results["total"] if results["total"] > 0 else 0
                )
                print(f"Progress: {i}/{len(args_list)}, Accuracy: {curr_acc:.3f}")

    if results["answers"] and results["targets"]:
        accuracy = data_processor.evaluate_accuracy(
            results["answers"], results["targets"]
        )

        final_results = {
            "accuracy": accuracy,
            "correct": results["correct"],
            "total": results["total"],
            "no_answer": results["no_answer"],
        }

        error_logs = {"accuracy": accuracy, "errors": results["errors"]}

        print(
            f"\n📊 Final Accuracy: {accuracy:.3f} ({results['correct']}/{results['total']})"
        )
    else:
        final_results = {
            "accuracy": 0.0,
            "correct": 0,
            "total": 0,
            "no_answer": results["no_answer"],
        }
        error_logs = {"accuracy": 0.0, "errors": results["errors"]}
        print(f"\n📊 No valid results!")

    return final_results, error_logs
