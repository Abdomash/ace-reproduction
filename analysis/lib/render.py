from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CommandResult:
    title: str
    rows: list[dict[str, Any]]
    data: Any
    text: str | None = None


def _group_rows_by_benchmark(rows: list[dict[str, Any]]) -> list[tuple[str | None, list[dict[str, Any]]]]:
    if not rows:
        return [(None, rows)]
    if "benchmark" not in rows[0]:
        return [(None, rows)]
    grouped: dict[str | None, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.get("benchmark"), []).append(row)
    ordered_keys = sorted(grouped, key=lambda value: "" if value is None else str(value))
    return [(key, grouped[key]) for key in ordered_keys]


def _format_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def render_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No rows."
    headers = list(rows[0].keys())
    widths = {header: len(header) for header in headers}
    rendered_rows = []
    for row in rows:
        rendered = {header: _format_cell(row.get(header)) for header in headers}
        rendered_rows.append(rendered)
        for header, value in rendered.items():
            widths[header] = max(widths[header], len(value))
    header_line = "  ".join(header.ljust(widths[header]) for header in headers)
    separator = "  ".join("-" * widths[header] for header in headers)
    body = [
        "  ".join(rendered[header].ljust(widths[header]) for header in headers)
        for rendered in rendered_rows
    ]
    return "\n".join([header_line, separator, *body])


def render_markdown(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No rows."
    headers = list(rows[0].keys())
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_format_cell(row.get(header)) for header in headers) + " |")
    return "\n".join(lines)


def render_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _format_cell(value) for key, value in row.items()})
    return output.getvalue().rstrip("\n")


def render_result(result: CommandResult, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(result.data, indent=2, sort_keys=True)
    if fmt == "csv":
        return render_csv(result.rows)
    if fmt == "md":
        if result.text:
            return result.text
        parts = []
        for benchmark, rows in _group_rows_by_benchmark(result.rows):
            if benchmark is not None and len(_group_rows_by_benchmark(result.rows)) > 1:
                parts.append(f"### {benchmark}")
            parts.append(render_markdown(rows))
        return "\n\n".join(part for part in parts if part)
    if result.text:
        return result.text
    groups = _group_rows_by_benchmark(result.rows)
    if len(groups) == 1:
        return render_table(result.rows)
    parts = []
    for benchmark, rows in groups:
        if benchmark is not None:
            parts.append(f"[{benchmark}]")
        parts.append(render_table(rows))
    return "\n\n".join(parts)


def write_output(path: Path, rendered: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered + ("" if rendered.endswith("\n") else "\n"), encoding="utf-8")
