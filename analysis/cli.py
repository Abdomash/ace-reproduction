from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .commands import list as list_command
from .commands.shared import report
from .lib.render import render_result, write_output
from .lib.selectors import add_output_arguments, add_selector_arguments


TARGET_NAMING_HELP = """\
Target naming model:

run:
  One concrete run folder.
  Example: offline_seed-42_20260421_025609

config:
  One config/model directory containing one or more runs.
  Example: openrouter-mixed-strong-generator-deepseek

campaign:
  Any broader results/ subtree containing runs.
  Example: results/ace-finer/subset/openrouter-gpt-oss-120b

Examples:
  python -m analysis list --benchmark finer
  python -m analysis --run offline_seed-42_20260421_025609
  python -m analysis --config openrouter-gpt-oss-120b --benchmark finer
  python -m analysis results/ace-finer/subset/openrouter-gpt-oss-120b
"""


def _base_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m analysis",
        description=description,
        epilog=TARGET_NAMING_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_selector_arguments(parser)
    add_output_arguments(parser)
    return parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    subparsers = parser.add_subparsers(dest="command")

    list_parser = subparsers.add_parser(
        "list",
        help="Discover runs under results/.",
        description="Discover runs under results/.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_selector_arguments(list_parser)
    add_output_arguments(list_parser)
    list_parser.set_defaults(handler=list_command.run)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    argv = [*argv]
    if argv and argv[0] == "list":
        parser = build_parser()
        args = parser.parse_args(argv)
    else:
        parser = _base_parser("Terminal-first analysis report over results/.")
        args = parser.parse_args(argv)
        args.handler = report
    result = args.handler(args)
    rendered = render_result(result, args.format)
    if args.out:
        write_output(Path(args.out), rendered)
    print(rendered)
    return 0
