from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .backends import appworld as appworld_backend
from .backends import finer as finer_backend
from .backends.common import APPWORLD_ROOT, RESULTS_ROOT, ensure_api_key
from .campaigns import Campaign, load_campaign
from .runinfo import RunnerRun, discover_runner_runs
from .tiering import (
    TierSpec,
    apply_tier_overrides,
    parse_key_value_overrides,
    tier_config_id_from_roles,
)


def _sample_label(sample: dict[str, Any]) -> str:
    return str(sample.get("label") or sample.get("sample_id") or "sample")


def _config_label(config: dict[str, Any]) -> str:
    return str(config.get("label") or config.get("config_id") or "config")


def _resolved_models_for_config(
    tier_specs: dict[str, TierSpec],
    config_entry: dict[str, Any],
) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    for role in ("generator", "reflector", "curator"):
        tier_name = str(config_entry[f"{role}_tier"])
        spec = tier_specs[tier_name]
        mapping[role] = {
            "tier": tier_name,
            "provider": spec.provider,
            "model": spec.model,
            "label": spec.label,
        }
    return mapping


def _config_slug(sample_id: str, config_id: str, tier_specs: dict[str, TierSpec]) -> str:
    return (
        f"{sample_id}__{config_id}__cheap-{tier_specs['cheap'].slug_label}"
        f"__exp-{tier_specs['expensive'].slug_label}"
    )


def _run_metadata(
    campaign: Campaign,
    sample: dict[str, Any],
    config_id: str,
    tier_specs: dict[str, TierSpec],
    resolved_models: dict[str, dict[str, str]],
) -> dict[str, Any]:
    return {
        "campaign_id": campaign.campaign_id,
        "sample_id": sample["sample_id"],
        "sample_kind": sample.get("sample_kind", "representative"),
        "config_id": config_id,
        "tier_models": {
            name: {
                "provider": spec.provider,
                "model": spec.model,
                "label": spec.label,
            }
            for name, spec in tier_specs.items()
        },
        "resolved_models": resolved_models,
        "sample_manifest_path": str(campaign.root / "samples" / f"{sample['sample_id']}.json"),
    }


def _human_config_name(sample: dict[str, Any], config_entry: dict[str, Any], tier_specs: dict[str, TierSpec]) -> str:
    return (
        f"{_sample_label(sample)} / {_config_label(config_entry)} / "
        f"cheap={tier_specs['cheap'].label} expensive={tier_specs['expensive'].label}"
    )


def _resolve_benchmark_samples(campaign: Campaign, sample_ids: list[str], benchmark: str | None) -> list[dict[str, Any]]:
    requested = []
    for sample_id in sample_ids:
        if sample_id not in campaign.samples:
            raise SystemExit(f"Unknown sample id: {sample_id}")
        sample = campaign.samples[sample_id]
        if benchmark and sample.get("benchmark") != benchmark:
            continue
        requested.append(sample)
    if benchmark and not requested:
        raise SystemExit(f"No requested samples match benchmark `{benchmark}`.")
    return requested


def _launch_finer(
    *,
    campaign: Campaign,
    sample: dict[str, Any],
    config_id: str,
    config_entry: dict[str, Any],
    tier_specs: dict[str, TierSpec],
    args,
) -> int:
    resolved = _resolved_models_for_config(tier_specs, config_entry)
    config_slug = _config_slug(sample["sample_id"], config_id, tier_specs)
    save_path = finer_backend.config_dir(config_slug=config_slug)
    run_metadata = _run_metadata(campaign, sample, config_id, tier_specs, resolved)
    config_name = _human_config_name(sample, config_entry, tier_specs)
    sample_manifest_path = campaign.root / "samples" / f"{sample['sample_id']}.json"
    command = finer_backend.build_command(
        task_name="finer",
        mode="offline",
        save_path=save_path,
        benchmark="ace-finer",
        run_type="subset",
        config_slug=config_slug,
        config_name=config_name,
        seed=args.seed,
        api_provider=resolved["generator"]["provider"],
        generator_provider=resolved["generator"]["provider"],
        reflector_provider=resolved["reflector"]["provider"],
        curator_provider=resolved["curator"]["provider"],
        generator_model=resolved["generator"]["model"],
        reflector_model=resolved["reflector"]["model"],
        curator_model=resolved["curator"]["model"],
        sample_config_path=Path("eval/finance/data/sample_config.json"),
        sample_manifest_path=sample_manifest_path,
        eval_steps=args.eval_steps,
        test_workers=args.test_workers,
        max_tokens=args.max_tokens,
        telemetry=args.telemetry,
        telemetry_interval=args.telemetry_interval,
        checkpoint_enabled=args.checkpoint_enabled,
        stop_after_stage=args.stop_after_stage,
        stop_after_step=args.stop_after_step,
        run_metadata=run_metadata,
    )
    return finer_backend.launch(command, dry_run=args.dry_run)


def _appworld_stage_manifests(campaign: Campaign, sample: dict[str, Any]) -> tuple[list[str], dict[str, Path]]:
    manifest_path = campaign.root / "samples" / f"{sample['sample_id']}.json"
    eval_split = str(sample["eval_split"])
    if eval_split == "test_normal":
        return ["adapt", "eval-normal"], {"eval-normal": manifest_path}
    if eval_split == "test_challenge":
        return ["adapt", "eval-challenge"], {"eval-challenge": manifest_path}
    raise SystemExit(f"Unsupported AppWorld eval split in sample manifest: {eval_split}")


def _launch_appworld(
    *,
    campaign: Campaign,
    sample: dict[str, Any],
    config_id: str,
    config_entry: dict[str, Any],
    tier_specs: dict[str, TierSpec],
    args,
) -> int:
    resolved = _resolved_models_for_config(tier_specs, config_entry)
    config_slug = _config_slug(sample["sample_id"], config_id, tier_specs)
    save_path = appworld_backend.config_dir(config_slug=config_slug)
    run_metadata = _run_metadata(campaign, sample, config_id, tier_specs, resolved)
    config_name = _human_config_name(sample, config_entry, tier_specs)
    enabled_stages, manifest_paths = _appworld_stage_manifests(campaign, sample)
    command = appworld_backend.build_full_eval_command(
        save_path=save_path,
        config_name=config_name,
        seed=args.seed,
        generator_provider=resolved["generator"]["provider"],
        generator_model=resolved["generator"]["model"],
        reflector_provider=resolved["reflector"]["provider"],
        reflector_model=resolved["reflector"]["model"],
        curator_provider=resolved["curator"]["provider"],
        curator_model=resolved["curator"]["model"],
        appworld_root=APPWORLD_ROOT,
        max_steps=args.appworld_max_steps,
        max_tokens=args.max_tokens,
        telemetry=args.telemetry,
        telemetry_interval=args.telemetry_interval,
        checkpoint_enabled=args.checkpoint_enabled,
        stop_after_stage=args.stop_after_stage,
        stop_after_task=args.stop_after_task,
        checkpoint_every_task=args.checkpoint_every_task,
        test_workers=args.test_workers,
        enabled_stages=enabled_stages,
        task_manifest_paths=manifest_paths,
        run_metadata=run_metadata,
    )
    return appworld_backend.launch(command, dry_run=args.dry_run)


def launch_command(args) -> int:
    campaign = load_campaign(args.campaign)
    if not args.sample:
        raise SystemExit("Specify at least one --sample.")
    if not args.config:
        raise SystemExit("Specify at least one --config.")
    tier_specs = apply_tier_overrides(
        campaign.tier_specs,
        model_overrides=parse_key_value_overrides(args.tier),
        provider_overrides=parse_key_value_overrides(args.tier_provider),
    )
    for spec in tier_specs.values():
        if not args.dry_run:
            ensure_api_key(spec.provider)
    samples = _resolve_benchmark_samples(campaign, args.sample, args.benchmark)
    exit_code = 0
    for sample in samples:
        for config_id in args.config:
            if config_id not in campaign.configs:
                raise SystemExit(f"Unknown config id: {config_id}")
            config_entry = campaign.configs[config_id]
            if sample["benchmark"] == "finer":
                code = _launch_finer(
                    campaign=campaign,
                    sample=sample,
                    config_id=config_id,
                    config_entry=config_entry,
                    tier_specs=tier_specs,
                    args=args,
                )
            else:
                code = _launch_appworld(
                    campaign=campaign,
                    sample=sample,
                    config_id=config_id,
                    config_entry=config_entry,
                    tier_specs=tier_specs,
                    args=args,
                )
            if code != 0:
                exit_code = code
                if not args.keep_going:
                    return exit_code
    return exit_code


def _render_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "(none)"
    headers = list(rows[0].keys())
    widths = {header: len(header) for header in headers}
    for row in rows:
        for header in headers:
            widths[header] = max(widths[header], len(str(row.get(header, "-"))))
    lines = [
        "  " + "  ".join(header.ljust(widths[header]) for header in headers),
        "  " + "  ".join("-" * widths[header] for header in headers),
    ]
    for row in rows:
        lines.append(
            "  " + "  ".join(str(row.get(header, "-")).ljust(widths[header]) for header in headers)
        )
    return "\n".join(lines)


def samples_command(args) -> int:
    campaign = load_campaign(args.campaign)
    rows = []
    for sample_id in sorted(campaign.samples):
        sample = campaign.samples[sample_id]
        rows.append(
            {
                "sample_id": sample_id,
                "benchmark": sample.get("benchmark"),
                "kind": sample.get("sample_kind"),
                "label": sample.get("label"),
                "size": sample.get("size_summary"),
            }
        )
    print(_render_rows(rows))
    return 0


def configs_command(args) -> int:
    campaign = load_campaign(args.campaign)
    tier_specs = apply_tier_overrides(
        campaign.tier_specs,
        model_overrides=parse_key_value_overrides(args.tier),
        provider_overrides=parse_key_value_overrides(args.tier_provider),
    )
    rows = []
    for config_id in sorted(campaign.configs):
        config_entry = campaign.configs[config_id]
        rows.append(
            {
                "config_id": config_id,
                "label": config_entry.get("label"),
                "generator": config_entry.get("generator_tier"),
                "reflector": config_entry.get("reflector_tier"),
                "curator": config_entry.get("curator_tier"),
                "cheap_model": tier_specs["cheap"].model,
                "expensive_model": tier_specs["expensive"].model,
            }
        )
    print(_render_rows(rows))
    return 0


def list_command(args) -> int:
    rows = []
    for run in discover_runner_runs():
        if args.campaign and run.campaign_id != args.campaign:
            continue
        if args.benchmark and run.benchmark != args.benchmark:
            continue
        rows.append(
            {
                "benchmark": run.benchmark,
                "sample_id": run.sample_id or "-",
                "config_id": run.config_id or "-",
                "config_slug": run.config_slug or "-",
                "run_leaf": run.run_leaf,
                "status": run.status or "-",
            }
        )
    print(_render_rows(rows))
    return 0


def _select_resume_run(args) -> RunnerRun:
    candidates = []
    for run in discover_runner_runs():
        if args.benchmark and run.benchmark != args.benchmark:
            continue
        if args.sample and run.sample_id != args.sample:
            continue
        if args.config and run.config_id != args.config:
            continue
        candidates.append(run)
    if not candidates:
        raise SystemExit("No matching runs found to resume.")
    if args.latest:
        candidates.sort(key=lambda item: (item.timestamp or "", item.run_leaf))
        return candidates[-1]
    if len(candidates) != 1:
        raise SystemExit("Multiple runs matched; add --latest or narrow the filters.")
    return candidates[0]


def resume_command(args) -> int:
    run = _select_resume_run(args)
    metadata = run.run_metadata
    if not metadata.get("sample_id") or not metadata.get("config_id"):
        raise SystemExit("Matched run does not have runner sample/config metadata; cannot reconstruct resume command.")
    campaign = load_campaign(args.campaign)
    sample = campaign.samples[metadata["sample_id"]]
    config_entry = campaign.configs[metadata["config_id"]]
    tier_specs = campaign.tier_specs
    resolved_models = metadata.get("resolved_models") or _resolved_models_for_config(tier_specs, config_entry)

    config_slug = run.config_slug or _config_slug(sample["sample_id"], metadata["config_id"], tier_specs)
    config_name = metadata.get("config_name") or _human_config_name(sample, config_entry, tier_specs)
    run_metadata = _run_metadata(campaign, sample, metadata["config_id"], tier_specs, resolved_models)
    resume_seed = args.seed if args.seed is not None else run.seed
    if resume_seed is None:
        raise SystemExit("Unable to determine the original run seed for resume; pass --seed explicitly.")
    if run.benchmark == "finer":
        command = finer_backend.build_command(
            task_name="finer",
            mode="offline",
            save_path=finer_backend.config_dir(config_slug=config_slug),
            benchmark="ace-finer",
            run_type="subset",
            config_slug=config_slug,
            config_name=config_name,
            seed=resume_seed,
            api_provider=resolved_models["generator"]["provider"],
            generator_provider=resolved_models["generator"]["provider"],
            reflector_provider=resolved_models["reflector"]["provider"],
            curator_provider=resolved_models["curator"]["provider"],
            generator_model=resolved_models["generator"]["model"],
            reflector_model=resolved_models["reflector"]["model"],
            curator_model=resolved_models["curator"]["model"],
            sample_config_path=Path("eval/finance/data/sample_config.json"),
            sample_manifest_path=Path(str(metadata["sample_manifest_path"])),
            eval_steps=args.eval_steps,
            test_workers=args.test_workers,
            max_tokens=args.max_tokens,
            telemetry=args.telemetry,
            telemetry_interval=args.telemetry_interval,
            resume_from=run.path,
            checkpoint_enabled=args.checkpoint_enabled,
            stop_after_stage=args.stop_after_stage,
            stop_after_step=args.stop_after_step,
            run_metadata=run_metadata,
        )
        return finer_backend.launch(command, dry_run=args.dry_run)

    enabled_stages, manifest_paths = _appworld_stage_manifests(campaign, sample)
    command = appworld_backend.build_full_eval_command(
        save_path=appworld_backend.config_dir(config_slug=config_slug),
        config_name=config_name,
        seed=resume_seed,
        generator_provider=resolved_models["generator"]["provider"],
        generator_model=resolved_models["generator"]["model"],
        reflector_provider=resolved_models["reflector"]["provider"],
        reflector_model=resolved_models["reflector"]["model"],
        curator_provider=resolved_models["curator"]["provider"],
        curator_model=resolved_models["curator"]["model"],
        appworld_root=APPWORLD_ROOT,
        max_steps=args.appworld_max_steps,
        max_tokens=args.max_tokens,
        telemetry=args.telemetry,
        telemetry_interval=args.telemetry_interval,
        resume_from=run.path,
        checkpoint_enabled=args.checkpoint_enabled,
        stop_after_stage=args.stop_after_stage,
        stop_after_task=args.stop_after_task,
        checkpoint_every_task=args.checkpoint_every_task,
        test_workers=args.test_workers,
        enabled_stages=enabled_stages,
        task_manifest_paths=manifest_paths,
        run_metadata=run_metadata,
    )
    return appworld_backend.launch(command, dry_run=args.dry_run)


def legacy_run_experiments_command(args) -> int:
    preset = args.preset
    if preset == "finer_subset":
        sample_id = "finer_repr_a"
        config_id = "all_cheap"
        if "deepseek" in args.generator_model.lower() and args.generator_model == args.reflector_model == args.curator_model:
            config_id = "all_expensive"
        elif args.reflector_model != args.generator_model and args.generator_model == args.curator_model:
            config_id = "expensive_reflector"
        elif args.generator_model != args.reflector_model and args.reflector_model == args.curator_model:
            config_id = "expensive_generator"
        elif args.curator_model != args.generator_model and args.generator_model == args.reflector_model:
            config_id = "expensive_curator"
        generator_provider = args.generator_provider or args.provider
        reflector_provider = args.reflector_provider or args.provider
        curator_provider = args.curator_provider or args.provider
        cheap_model = args.generator_model
        cheap_provider = generator_provider
        expensive_model = args.generator_model
        expensive_provider = generator_provider
        if config_id == "expensive_reflector":
            expensive_model = args.reflector_model
            expensive_provider = reflector_provider
        elif config_id == "expensive_generator":
            cheap_model = args.reflector_model
            cheap_provider = reflector_provider
            expensive_model = args.generator_model
            expensive_provider = generator_provider
        elif config_id == "expensive_curator":
            expensive_model = args.curator_model
            expensive_provider = curator_provider
        launch_args = argparse.Namespace(
            campaign="ace_repr_v1",
            sample=[sample_id],
            config=[config_id],
            benchmark="finer",
            seed=args.seed,
            tier=[f"cheap={cheap_model}", f"expensive={expensive_model}"],
            tier_provider=[f"cheap={cheap_provider}", f"expensive={expensive_provider}"],
            dry_run=args.dry_run,
            eval_steps=args.eval_steps,
            test_workers=args.test_workers,
            max_tokens=args.max_tokens,
            telemetry=args.telemetry,
            telemetry_interval=args.telemetry_interval,
            checkpoint_enabled=args.checkpoint_enabled,
            stop_after_stage=args.stop_after_stage,
            stop_after_step=args.stop_after_step,
            appworld_max_steps=args.appworld_max_steps,
            stop_after_task=args.stop_after_task,
            checkpoint_every_task=args.checkpoint_every_task,
            keep_going=False,
        )
        return launch_command(launch_args)
    raise SystemExit(
        "Legacy compatibility currently supports the new representative campaign through `python -m runner`.\n"
        "Use `python -m runner launch ...` for new work or keep the old shell runner only for unchanged historical presets."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m runner", description="Unified experiment runner.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common_launch_options(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--campaign", default="ace_repr_v1")
        subparser.add_argument("--sample", action="append")
        subparser.add_argument("--config", action="append")
        subparser.add_argument("--benchmark", choices=("finer", "appworld"))
        subparser.add_argument("--seed", type=int, default=42)
        subparser.add_argument("--tier", action="append", default=[])
        subparser.add_argument("--tier-provider", action="append", default=[])
        subparser.add_argument("--dry-run", action="store_true")
        subparser.add_argument("--eval-steps", type=int, default=100)
        subparser.add_argument("--test-workers", type=int, default=1)
        subparser.add_argument("--max-tokens", type=int, default=4096)
        subparser.add_argument("--telemetry", type=int, default=1)
        subparser.add_argument("--telemetry-interval", type=float, default=None)
        subparser.add_argument("--checkpoint-enabled", action="store_true")
        subparser.add_argument("--stop-after-stage", default=None)
        subparser.add_argument("--stop-after-step", type=int, default=None)
        subparser.add_argument("--appworld-max-steps", type=int, default=30)
        subparser.add_argument("--stop-after-task", type=int, default=None)
        subparser.add_argument("--checkpoint-every-task", type=int, default=1)
        subparser.add_argument("--keep-going", action="store_true")

    launch = subparsers.add_parser("launch", help="Launch representative campaign runs.")
    add_common_launch_options(launch)
    launch.set_defaults(handler=launch_command)

    resume = subparsers.add_parser("resume", help="Resume a representative campaign run.")
    resume.add_argument("--campaign", default="ace_repr_v1")
    resume.add_argument("--benchmark", choices=("finer", "appworld"))
    resume.add_argument("--sample")
    resume.add_argument("--config")
    resume.add_argument("--latest", action="store_true")
    resume.add_argument("--seed", type=int, default=None)
    resume.add_argument("--dry-run", action="store_true")
    resume.add_argument("--eval-steps", type=int, default=100)
    resume.add_argument("--test-workers", type=int, default=1)
    resume.add_argument("--max-tokens", type=int, default=4096)
    resume.add_argument("--telemetry", type=int, default=1)
    resume.add_argument("--telemetry-interval", type=float, default=None)
    resume.add_argument("--checkpoint-enabled", action="store_true")
    resume.add_argument("--stop-after-stage", default=None)
    resume.add_argument("--stop-after-step", type=int, default=None)
    resume.add_argument("--appworld-max-steps", type=int, default=30)
    resume.add_argument("--stop-after-task", type=int, default=None)
    resume.add_argument("--checkpoint-every-task", type=int, default=1)
    resume.set_defaults(handler=resume_command)

    list_parser = subparsers.add_parser("list", help="List existing runner-managed runs.")
    list_parser.add_argument("--campaign", default=None)
    list_parser.add_argument("--benchmark", choices=("finer", "appworld"))
    list_parser.set_defaults(handler=list_command)

    samples = subparsers.add_parser("samples", help="List campaign sample manifests.")
    samples.add_argument("--campaign", default="ace_repr_v1")
    samples.set_defaults(handler=samples_command)

    configs = subparsers.add_parser("configs", help="List campaign config definitions.")
    configs.add_argument("--campaign", default="ace_repr_v1")
    configs.add_argument("--tier", action="append", default=[])
    configs.add_argument("--tier-provider", action="append", default=[])
    configs.set_defaults(handler=configs_command)

    legacy = subparsers.add_parser("legacy-run-experiments", help=argparse.SUPPRESS)
    legacy.add_argument("preset")
    legacy.add_argument("--provider", default="openrouter")
    legacy.add_argument("--generator-provider", default=None)
    legacy.add_argument("--reflector-provider", default=None)
    legacy.add_argument("--curator-provider", default=None)
    legacy.add_argument("--generator", dest="generator_model", default="openai/gpt-oss-120b")
    legacy.add_argument("--reflector", dest="reflector_model", default="openai/gpt-oss-120b")
    legacy.add_argument("--curator", dest="curator_model", default="openai/gpt-oss-120b")
    legacy.add_argument("--results-root", default=str(RESULTS_ROOT))
    legacy.add_argument("--run-type", default="")
    legacy.add_argument("--config-slug", default="default")
    legacy.add_argument("--save-path", default="")
    legacy.add_argument("--config-name", default="default")
    legacy.add_argument("--seed", type=int, default=42)
    legacy.add_argument("--mode", default="offline")
    legacy.add_argument("--eval-steps", type=int, default=100)
    legacy.add_argument("--test-workers", type=int, default=20)
    legacy.add_argument("--max-tokens", type=int, default=4096)
    legacy.add_argument("--telemetry", type=int, default=1)
    legacy.add_argument("--telemetry-interval", type=float, default=None)
    legacy.add_argument("--appworld-root", default=str(APPWORLD_ROOT))
    legacy.add_argument("--appworld-max-steps", type=int, default=30)
    legacy.add_argument("--resume-from", default=None)
    legacy.add_argument("--checkpoint-enabled", action="store_true")
    legacy.add_argument("--stop-after-stage", default=None)
    legacy.add_argument("--stop-after-step", type=int, default=None)
    legacy.add_argument("--stop-after-task", type=int, default=None)
    legacy.add_argument("--checkpoint-every-task", type=int, default=1)
    legacy.add_argument("--dry-run", action="store_true")
    legacy.set_defaults(handler=legacy_run_experiments_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args))
