from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class SelectorSet:
    benchmark: str | None
    run_type: str | None
    config: str | None
    run: str | None
    campaign: str | None
    target: str | None
    target_kind: str
    seed: int | None
    latest: bool


def add_selector_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "target",
        nargs="?",
        help=(
            "Optional selector target. Interpreted as a run folder, a config folder/slug, "
            "or a broader campaign/results folder."
        ),
    )
    parser.add_argument("--benchmark", choices=("finer", "appworld"))
    parser.add_argument("--run-type", choices=("subset", "full"))
    parser.add_argument("--config", help="Config slug or config directory path.")
    parser.add_argument("--run", help="Concrete run leaf or run directory path.")
    parser.add_argument(
        "--campaign",
        help="Campaign directory under results/, usually a benchmark or run-type subtree.",
    )
    parser.add_argument(
        "--target-kind",
        choices=("auto", "run", "config", "campaign"),
        default="auto",
        help="Interpret the positional target explicitly instead of auto-detecting it.",
    )
    parser.add_argument("--seed", type=int)
    parser.add_argument("--latest", action="store_true")


def add_output_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=("table", "md", "json", "csv"), default="table")
    parser.add_argument("--out")


def selectors_from_args(args) -> SelectorSet:
    explicit_target = args.run or args.config or getattr(args, "campaign", None) or args.target
    if args.run:
        target_kind = "run"
    elif args.config:
        target_kind = "config"
    elif getattr(args, "campaign", None):
        target_kind = "campaign"
    else:
        target_kind = args.target_kind
    return SelectorSet(
        benchmark=args.benchmark,
        run_type=args.run_type,
        config=args.config,
        run=args.run,
        campaign=getattr(args, "campaign", None),
        target=explicit_target,
        target_kind=target_kind,
        seed=args.seed,
        latest=bool(args.latest),
    )
