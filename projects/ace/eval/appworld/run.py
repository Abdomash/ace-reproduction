import argparse
import json
import os

from .data_processor import DataProcessor, load_data

from ace import ACE
from utils import SUPPORTED_API_PROVIDERS


def parse_args():
    parser = argparse.ArgumentParser(description="ACE System - AppWorld")

    parser.add_argument("--task_name", type=str, required=True)
    parser.add_argument("--initial_playbook_path", type=str, default=None)
    parser.add_argument(
        "--mode",
        type=str,
        default="offline",
        choices=["offline", "online", "eval_only"],
    )

    parser.add_argument(
        "--api_provider",
        type=str,
        default="sambanova",
        choices=SUPPORTED_API_PROVIDERS,
    )
    parser.add_argument(
        "--generator_provider",
        type=str,
        default=None,
        choices=SUPPORTED_API_PROVIDERS,
    )
    parser.add_argument(
        "--reflector_provider",
        type=str,
        default=None,
        choices=SUPPORTED_API_PROVIDERS,
    )
    parser.add_argument(
        "--curator_provider",
        type=str,
        default=None,
        choices=SUPPORTED_API_PROVIDERS,
    )
    parser.add_argument("--generator_model", type=str, default="DeepSeek-V3.1")
    parser.add_argument("--reflector_model", type=str, default="DeepSeek-V3.1")
    parser.add_argument("--curator_model", type=str, default="DeepSeek-V3.1")

    parser.add_argument("--num_epochs", type=int, default=1)
    parser.add_argument("--max_num_rounds", type=int, default=3)
    parser.add_argument("--curator_frequency", type=int, default=1)
    parser.add_argument("--eval_steps", type=int, default=100)
    parser.add_argument("--online_eval_frequency", type=int, default=15)
    parser.add_argument("--save_steps", type=int, default=50)

    parser.add_argument("--max_tokens", type=int, default=4096)
    parser.add_argument("--playbook_token_budget", type=int, default=80000)
    parser.add_argument("--test_workers", type=int, default=20)

    parser.add_argument("--json_mode", action="store_true")
    parser.add_argument("--no_ground_truth", action="store_true")

    parser.add_argument("--use_bulletpoint_analyzer", action="store_true")
    parser.add_argument("--bulletpoint_analyzer_threshold", type=float, default=0.90)

    parser.add_argument("--save_path", type=str, required=True)

    parser.add_argument("--telemetry_enabled", action="store_true")
    parser.add_argument(
        "--telemetry_metrics_interval_seconds", type=float, default=None
    )

    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--config_name", type=str, default="default")
    parser.add_argument("--run_id", type=str, default=None)
    parser.add_argument(
        "--sample_config_path",
        type=str,
        default="./eval/appworld/data/sample_config.json",
    )

    parser.add_argument(
        "--dataset_name",
        type=str,
        default="train",
        choices=["train", "dev", "test_normal", "test_challenge"],
    )
    parser.add_argument("--max_agent_steps", type=int, default=30)
    parser.add_argument("--appworld_root", type=str, default=None)
    parser.add_argument("--max_retries", type=int, default=5)
    parser.add_argument("--ignore_multiple_calls", action="store_true")
    parser.add_argument("--max_prompt_length", type=int, default=None)

    return parser.parse_args()


def preprocess_data(task_name, config, mode):
    processor = DataProcessor(task_name=task_name)

    dataset_name = str(config.get("dataset_name", "train"))

    def resolve_eval_split_path() -> str:
        if dataset_name == "dev":
            return config.get("dev_data") or config.get("val_data")
        if dataset_name == "test_normal":
            return config.get("test_normal_data")
        if dataset_name == "test_challenge":
            return config.get("test_challenge_data")
        if dataset_name == "train":
            return config.get("train_data")
        raise ValueError(f"Unsupported dataset_name: {dataset_name}")

    if mode in ["online", "eval_only"]:
        train_samples = None
        val_samples = None

        test_path = resolve_eval_split_path()
        if test_path:
            test_samples = load_data(test_path)
            test_samples = processor.process_task_data(test_samples)
        else:
            raise ValueError(f"{mode} mode requires test data in config.")
    else:
        train_samples = load_data(config["train_data"])
        val_samples = load_data(config["val_data"])
        train_samples = processor.process_task_data(train_samples)
        val_samples = processor.process_task_data(val_samples)

        test_path = config.get("test_normal_data")
        if test_path:
            test_samples = load_data(test_path)
            test_samples = processor.process_task_data(test_samples)
        else:
            test_samples = []

    return train_samples, val_samples, test_samples, processor


def load_initial_playbook(path):
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def main():
    args = parse_args()

    with open(args.sample_config_path, "r", encoding="utf-8") as f:
        task_config = json.load(f)

    if args.task_name not in task_config:
        raise ValueError(
            f"Unknown task: {args.task_name}. Available: {list(task_config.keys())}"
        )

    train_samples, val_samples, test_samples, data_processor = preprocess_data(
        args.task_name,
        {**task_config[args.task_name], "dataset_name": args.dataset_name},
        args.mode,
    )

    initial_playbook = load_initial_playbook(args.initial_playbook_path)

    ace_system = ACE(
        api_provider=args.api_provider,
        generator_model=args.generator_model,
        reflector_model=args.reflector_model,
        curator_model=args.curator_model,
        generator_provider=args.generator_provider,
        reflector_provider=args.reflector_provider,
        curator_provider=args.curator_provider,
        max_tokens=args.max_tokens,
        initial_playbook=initial_playbook,
        use_bulletpoint_analyzer=args.use_bulletpoint_analyzer,
        bulletpoint_analyzer_threshold=args.bulletpoint_analyzer_threshold,
        task_type="appworld",
    )

    config = {
        "num_epochs": args.num_epochs,
        "max_num_rounds": args.max_num_rounds,
        "curator_frequency": args.curator_frequency,
        "eval_steps": args.eval_steps,
        "online_eval_frequency": args.online_eval_frequency,
        "save_steps": args.save_steps,
        "playbook_token_budget": args.playbook_token_budget,
        "task_name": args.task_name,
        "mode": args.mode,
        "json_mode": args.json_mode,
        "no_ground_truth": args.no_ground_truth,
        "save_dir": args.save_path,
        "test_workers": args.test_workers,
        "initial_playbook_path": args.initial_playbook_path,
        "use_bulletpoint_analyzer": args.use_bulletpoint_analyzer,
        "bulletpoint_analyzer_threshold": args.bulletpoint_analyzer_threshold,
        "api_provider": args.api_provider,
        "generator_provider": args.generator_provider or args.api_provider,
        "reflector_provider": args.reflector_provider or args.api_provider,
        "curator_provider": args.curator_provider or args.api_provider,
        "generator_model": args.generator_model,
        "reflector_model": args.reflector_model,
        "curator_model": args.curator_model,
        "dataset_name": args.dataset_name,
        "max_agent_steps": args.max_agent_steps,
        "appworld_root": args.appworld_root,
        "max_retries": args.max_retries,
        "ignore_multiple_calls": args.ignore_multiple_calls,
        "max_prompt_length": args.max_prompt_length,
    }

    config["telemetry_enabled"] = args.telemetry_enabled
    if args.telemetry_metrics_interval_seconds is not None:
        config["telemetry_metrics_interval_seconds"] = (
            args.telemetry_metrics_interval_seconds
        )
    config["seed"] = args.seed
    config["config_name"] = args.config_name
    if args.run_id:
        config["run_id"] = args.run_id

    results = ace_system.run(
        mode=args.mode,
        train_samples=train_samples,
        val_samples=val_samples,
        test_samples=test_samples,
        data_processor=data_processor,
        config=config,
    )

    print(f"Final results: {results}")


if __name__ == "__main__":
    main()
