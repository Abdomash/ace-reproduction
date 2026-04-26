from __future__ import annotations

from ..lib import appworld, discovery, finer
from ..lib.common import format_timestamp
from ..lib.render import CommandResult
from ..lib.selectors import selectors_from_args
from ..lib.telemetry import pairwise_call_graph_similarity


def _has_explicit_selection(selectors) -> bool:
    return any(
        (
            selectors.target,
            selectors.run,
            selectors.config,
            selectors.campaign,
            selectors.benchmark,
            selectors.run_type,
            selectors.seed is not None,
        )
    )


def get_runs(args, *, require_selection: bool = True, allow_mixed_benchmarks: bool = False):
    selectors = selectors_from_args(args)
    if require_selection and not _has_explicit_selection(selectors):
        raise SystemExit(
            "Choose which results you want to inspect first. Try `python -m analysis list` to browse, "
            "then run `python -m analysis --run ...`, `--config ...`, or `--campaign ...`. "
            "The report command does not run against the entire `results/` tree by default."
        )
    runs = discovery.select_runs(selectors)
    if not runs:
        target = selectors.target or selectors.run or selectors.config or selectors.campaign
        message = "No runs matched the requested selectors."
        if target:
            message += (
                f" Target `{target}` can be a run folder, a config slug/path, "
                f"or a campaign/results directory."
            )
        raise SystemExit(message)
    benchmarks = sorted({run.benchmark for run in runs})
    if len(benchmarks) > 1 and not allow_mixed_benchmarks:
        raise SystemExit(
            "Mixed-benchmark comparisons are not allowed. Narrow the selection with `--benchmark`."
        )
    return runs


def summarize_run(run):
    if run.benchmark == "finer":
        return finer.summarize_run(run)
    return appworld.summarize_run(run)


def run_rows(runs):
    return [
        {
            "benchmark": run.benchmark,
            "run_type": run.run_type,
            "config_slug": run.config_slug,
            "config_path": run.config_selector,
            "run_leaf": run.run_leaf,
            "run_path": run.repo_relative_path,
            "campaign_path": run.campaign_selector,
            "seed": run.seed,
            "timestamp": run.timestamp,
            "timestamp_display": format_timestamp(run.timestamp),
            "mode": run.mode,
            "status": run.status,
            "checkpointing_enabled": run.checkpointing_enabled,
            "has_checkpoints": run.has_checkpoints,
            "resume_count": run.resume_count,
            "current_stage": run.current_stage,
            "last_completed_stage": run.last_completed_stage,
            "active_runtime_seconds": run.active_runtime_seconds,
            "path": run.repo_relative_path,
        }
        for run in runs
    ]


def build_command_result(title: str, rows: list[dict], data: dict, text: str | None = None):
    return CommandResult(title=title, rows=rows, data=data, text=text)


def pct(value) -> str:
    if value is None:
        return "-"
    numeric = float(value)
    if abs(numeric) <= 1.0:
        numeric *= 100
    return f"{numeric:.2f}%"


def pct_delta(value) -> str:
    if value is None:
        return "-"
    numeric = float(value)
    if abs(numeric) <= 1.0:
        numeric *= 100
    return f"{numeric:+.2f}pp"


def money(value) -> str:
    if value is None:
        return "-"
    return f"${float(value):.6f}"


def bytes_human(value) -> str:
    if value is None:
        return "-"
    numeric = float(value)
    units = ["B", "KB", "MB", "GB", "TB"]
    unit = units[0]
    for unit in units:
        if abs(numeric) < 1024 or unit == units[-1]:
            break
        numeric /= 1024.0
    return f"{numeric:.2f}{unit}"


def metric_value(value, unit: str | None) -> str:
    if value is None:
        return "-"
    if unit == "%":
        return f"{float(value):.2f}%"
    return str(value)


def scalar(value) -> str:
    if value is None:
        return "-"
    return str(value)


def count_pair(numerator, denominator) -> str:
    if numerator is None or denominator is None:
        return "-"
    return f"{numerator}/{denominator}"


def rate_delta(numerator_before, denominator_before, numerator_after, denominator_after) -> str:
    if (
        numerator_before is None
        or denominator_before in (None, 0)
        or numerator_after is None
        or denominator_after in (None, 0)
    ):
        return "-"
    before = float(numerator_before) / float(denominator_before)
    after = float(numerator_after) / float(denominator_after)
    return pct_delta(after - before)


def _render_table(rows: list[dict]) -> list[str]:
    if not rows:
        return ["  (none)"]
    headers = list(rows[0].keys())
    widths = {header: len(header) for header in headers}
    rendered_rows = []
    for row in rows:
        rendered = {
            header: ("-" if row.get(header) is None else str(row.get(header, "")))
            for header in headers
        }
        rendered_rows.append(rendered)
        for header, value in rendered.items():
            widths[header] = max(widths[header], len(value))
    lines = [
        "  " + "  ".join(header.ljust(widths[header]) for header in headers),
        "  " + "  ".join("-" * widths[header] for header in headers),
    ]
    lines.extend(
        "  " + "  ".join(rendered[header].ljust(widths[header]) for header in headers)
        for rendered in rendered_rows
    )
    return lines


def _run_label(run) -> str:
    return run.run_leaf


def _models_compact(run, payload: dict) -> str:
    if run.benchmark == "finer":
        models = payload.get("models") or {}
        return " | ".join(
            [
                str(models.get("generator") or "-"),
                str(models.get("reflector") or "-"),
                str(models.get("curator") or "-"),
            ]
        )
    models = payload.get("models") or {}
    if isinstance(models, dict) and models:
        return " | ".join(sorted(models))
    return payload.get("models_display") or "-"


def _metric_stat(telemetry: dict, metric_name: str, field: str):
    return ((telemetry.get("metrics") or {}).get(metric_name) or {}).get(field)


def _metric_unit(telemetry: dict, metric_name: str) -> str | None:
    return ((telemetry.get("metrics") or {}).get(metric_name) or {}).get("unit")


def _primary_metric(run, payload: dict):
    summary = payload["summary"]
    return (
        summary.get("final_tag_accuracy")
        if run.benchmark == "finer"
        else summary.get("task_goal_completion")
    )


def _secondary_metric(run, payload: dict):
    summary = payload["summary"]
    return (
        summary.get("best_validation_accuracy")
        if run.benchmark == "finer"
        else summary.get("scenario_goal_completion")
    )


def _stability_rows(runs) -> list[dict]:
    rows = pairwise_call_graph_similarity(runs)
    rows.sort(key=lambda row: (row["left_run"], row["right_run"]))
    return rows


def _notes_for_single(run, payload: dict) -> list[str]:
    notes: list[str] = []
    telemetry = payload.get("telemetry") or {}
    if run.benchmark == "finer":
        playbooks = payload.get("playbooks") or {}
        if playbooks.get("best_equals_final") is False:
            notes.append("Best and final playbooks differ.")
        if (payload.get("llm_usage") or {}).get("total", {}).get("calls_with_cost") == 0:
            notes.append("Provider cost metadata was missing from LLM logs.")
    notes.append(
        "llm_call_time may exceed actual elapsed_time because "
        "several LLM calls may run in parallel."
    )
    cpu_max = _metric_stat(telemetry, "process.cpu.usage", "max")
    cpu_p95 = _metric_stat(telemetry, "process.cpu.usage", "p95")
    if cpu_max is not None and cpu_p95 is not None and cpu_max > max(cpu_p95 * 20, 100):
        notes.append(
            "CPU max includes extreme telemetry spikes, so p95 is usually the better indicator of sustained CPU load."
        )
    return notes


def render_run_report(run, payload: dict) -> str:
    if run.benchmark == "finer":
        return render_finer_report(run, payload)
    return render_appworld_report(run, payload)


def render_finer_report(run, payload: dict) -> str:
    summary = payload["summary"]
    config = payload.get("config") or {}
    tests = payload.get("tests") or {}
    initial = tests.get("initial") or {}
    final = tests.get("final") or {}
    training = payload.get("training") or {}
    pre_post = payload.get("training_pre_post") or {}
    playbooks = payload.get("playbooks") or {}
    llm_usage = payload.get("llm_usage") or {}
    telemetry = payload.get("telemetry") or {}
    artifacts = payload.get("artifacts") or {}
    costs = payload.get("costs") or {}
    total_cost = costs.get("total") or {}
    tag_changes = payload.get("tag_changes") or {}
    notes = _notes_for_single(run, payload)

    model_lines = [
        f"  generator: {(payload.get('models') or {}).get('generator') or '-'}",
        f"  reflector: {(payload.get('models') or {}).get('reflector') or '-'}",
        f"  curator:   {(payload.get('models') or {}).get('curator') or '-'}",
    ]

    lines = [
        f"# {run.run_leaf}",
        f"Path: {run.repo_relative_path}",
        "",
        "Setup:",
        f"  benchmark:  {run.benchmark}",
        f"  run_type:   {run.run_type or '-'}",
        f"  config:     {run.config_slug or '-'}",
        f"  timestamp:  {format_timestamp(run.timestamp) or run.timestamp or '-'}",
        f"  mode:       {run.mode or '-'}",
        f"  seed:       {run.seed if run.seed is not None else '-'}",
        f"  eval_steps: {config.get('eval_steps') or '-'}",
        f"  provider:   {config.get('api_provider') or '-'}",
        "",
        "Models:",
        *model_lines,
        "",
        "Overall:",
        f"  tag_accuracy:         {pct(summary.get('initial_tag_accuracy'))} -> {pct(summary.get('final_tag_accuracy'))} ({pct_delta(summary.get('tag_accuracy_delta'))})",
        f"  exact_samples:        {count_pair(initial.get('exact_correct'), initial.get('total'))} -> {count_pair(final.get('exact_correct'), final.get('total'))} ({rate_delta(initial.get('exact_correct'), initial.get('total'), final.get('exact_correct'), final.get('total'))})",
        f"  correct_tags:         {count_pair(initial.get('correct_tags'), initial.get('total_tags'))} -> {count_pair(final.get('correct_tags'), final.get('total_tags'))}",
        f"  best_validation:      {pct(summary.get('best_validation_accuracy'))}",
        f"  total_cost:           {money(total_cost.get('cost_usd'))}",
        f"  total_tokens:         {scalar(total_cost.get('total_tokens'))}",
        f"  cached_input_tokens:  {scalar(total_cost.get('cached_input_tokens'))}",
        f"  cached_output_tokens: {scalar(total_cost.get('cached_output_tokens'))}",
        f"  elapsed_time:         {(telemetry.get('trace_wall_time_seconds') or 0):.2f}s",
        "",
        "Accuracy breakdown:",
        *_render_table(
            [
                {
                    "split": "initial",
                    "tag_acc": pct(initial.get("computed_tag_accuracy")),
                    "correct_tags": count_pair(initial.get("correct_tags"), initial.get("total_tags")),
                    "exact": count_pair(initial.get("exact_correct"), initial.get("total")),
                    "no_answer": count_pair(initial.get("no_answer"), initial.get("total")),
                },
                {
                    "split": "final",
                    "tag_acc": pct(final.get("computed_tag_accuracy")),
                    "correct_tags": count_pair(final.get("correct_tags"), final.get("total_tags")),
                    "exact": count_pair(final.get("exact_correct"), final.get("total")),
                    "no_answer": count_pair(final.get("no_answer"), final.get("total")),
                },
            ]
        ),
        "",
        "Tag movement:",
        f"  corrected_tags:    {tag_changes.get('improved_tags', 0)} across {tag_changes.get('improved_samples', 0)} samples",
        f"  miscorrected_tags: {tag_changes.get('regressed_tags', 0)} across {tag_changes.get('regressed_samples', 0)} samples",
        "",
        "Training pre/post:",
        f"  tag_acc: {pct(pre_post.get('pre_tag_accuracy'))} -> {pct(pre_post.get('post_tag_accuracy'))} ({count_pair(pre_post.get('pre_correct_tags'), pre_post.get('total_tags'))} -> {count_pair(pre_post.get('post_correct_tags'), pre_post.get('total_tags'))})",
        f"  exact:   {count_pair(pre_post.get('pre_exact'), pre_post.get('total_samples'))} -> {count_pair(pre_post.get('post_exact'), pre_post.get('total_samples'))}",
    ]
    if training.get("checkpoints"):
        lines.extend(
            [
                "",
                "Validation checkpoints:",
                *_render_table(
                    [
                        {
                            "step": row.get("step"),
                            "val_acc": pct(row.get("val_accuracy")),
                            "exact": count_pair(row.get("val_exact_correct"), row.get("val_total")),
                            "train_pre": pct(row.get("train_pre_accuracy")),
                            "train_post": pct(row.get("train_post_accuracy")),
                            "bullets": row.get("playbook_bullets"),
                            "tokens": row.get("playbook_tokens"),
                        }
                        for row in training.get("checkpoints") or []
                    ]
                ),
            ]
        )
    if costs.get("roles"):
        cost_rows = []
        for role, row in sorted(costs.get("roles", {}).items()):
            cost_rows.append(
                {
                    "role": role,
                    "calls": row.get("calls"),
                    "cost": money(row.get("cost_usd")),
                    "tokens": row.get("total_tokens"),
                    "cached_in": row.get("cached_input_tokens"),
                    "cached_out": row.get("cached_output_tokens"),
                    "avg_time": f"{((llm_usage.get('roles', {}).get(role, {}).get('total_time') or 0.0) / (row.get('calls') or 1)):.2f}s",
                }
            )
        cost_rows.append(
            {
                "role": "total",
                "calls": total_cost.get("calls"),
                "cost": money(total_cost.get("cost_usd")),
                "tokens": total_cost.get("total_tokens"),
                "cached_in": total_cost.get("cached_input_tokens"),
                "cached_out": total_cost.get("cached_output_tokens"),
                "avg_time": f"{((llm_usage.get('total', {}).get('total_time') or 0.0) / (llm_usage.get('total', {}).get('calls') or 1)):.2f}s",
            }
        )
        lines.extend(["", "Cost breakdown:", *_render_table(cost_rows)])
    lines.extend(
        [
            "",
            "Playbooks:",
            *_render_table(
                [
                    {
                        "version": name,
                        "bullets": (playbooks.get(name) or {}).get("bullets"),
                        "chars": (playbooks.get(name) or {}).get("chars"),
                        "helpful_sum": (playbooks.get(name) or {}).get("helpful_sum"),
                        "harmful_sum": (playbooks.get(name) or {}).get("harmful_sum"),
                    }
                    for name in ("best", "final")
                    if playbooks.get(name)
                ]
            ),
            "",
            "Telemetry:",
            f"  cpu_usage:       avg={metric_value(_metric_stat(telemetry, 'process.cpu.usage', 'avg'), _metric_unit(telemetry, 'process.cpu.usage'))} p95={metric_value(_metric_stat(telemetry, 'process.cpu.usage', 'p95'), _metric_unit(telemetry, 'process.cpu.usage'))} max={metric_value(_metric_stat(telemetry, 'process.cpu.usage', 'max'), _metric_unit(telemetry, 'process.cpu.usage'))}",
            f"  memory_usage:    avg={bytes_human(_metric_stat(telemetry, 'process.memory.usage_bytes', 'avg'))} max={bytes_human(_metric_stat(telemetry, 'process.memory.usage_bytes', 'max'))}",
            f"  spans:           {telemetry.get('span_count', 0)} across {telemetry.get('agent_count', 0)} agents",
            f"  elapsed_time:    {(telemetry.get('trace_wall_time_seconds') or 0):.2f}s",
            f"  llm_call_time:   {(telemetry.get('llm_wall_time_seconds') or 0):.2f}s",
            "",
            "Artifacts:",
            f"  bullet_usage:     {artifacts.get('bullet_usage_log_lines')}",
            f"  curator_ops:      {artifacts.get('curator_operations_lines')}",
            f"  curator_failures: {artifacts.get('curator_failures_lines')}",
            f"  trace_samples_collected:  {artifacts.get('trace_lines')}",
            f"  metric_samples_collected: {artifacts.get('metrics_lines')}",
        ]
    )
    if notes:
        lines.extend(["", "Notes:", *[f"  - {note}" for note in notes]])
    return "\n".join(lines)


def render_appworld_report(run, payload: dict) -> str:
    summary = payload["summary"]
    total_cost = (payload.get("costs") or {}).get("total") or {}
    telemetry = payload.get("telemetry") or {}
    models = payload.get("models") or {}
    lines = [
        f"# {run.run_leaf}",
        f"Path: {run.repo_relative_path}",
        "",
        "Setup:",
        f"  benchmark: {run.benchmark}",
        f"  run_type:  {run.run_type or '-'}",
        f"  config:    {run.config_slug or '-'}",
        f"  timestamp: {format_timestamp(run.timestamp) or run.timestamp or '-'}",
        f"  dataset:   {summary.get('dataset') or '-'}",
        "",
        "Models:",
        *([f"  {model}: {count}" for model, count in sorted(models.items())] or ["  -"]),
        "",
        "Overall:",
        f"  task_goal_completion:     {pct(summary.get('task_goal_completion'))}",
        f"  scenario_goal_completion: {pct(summary.get('scenario_goal_completion'))}",
        f"  total_cost:               {money(total_cost.get('cost_usd'))}",
        f"  total_tokens:             {scalar(total_cost.get('total_tokens'))}",
        f"  cached_input_tokens:      {scalar(total_cost.get('cached_input_tokens'))}",
        f"  cached_output_tokens:     {scalar(total_cost.get('cached_output_tokens'))}",
        f"  elapsed_time:             {(telemetry.get('trace_wall_time_seconds') or 0):.2f}s",
        "",
        "Evaluation breakdown:",
        *_render_table(
            [
                {
                    "task_goal": pct(summary.get("task_goal_completion")),
                    "scenario_goal": pct(summary.get("scenario_goal_completion")),
                    "tasks": summary.get("task_count"),
                    "failures": summary.get("failure_count"),
                    "difficulty_1": pct(summary.get("difficulty_1_pass_rate")),
                    "difficulty_2": pct(summary.get("difficulty_2_pass_rate")),
                    "difficulty_3": pct(summary.get("difficulty_3_pass_rate")),
                }
            ]
        ),
        "",
        "Telemetry:",
        f"  cpu_usage:       avg={metric_value(_metric_stat(telemetry, 'process.cpu.usage', 'avg'), _metric_unit(telemetry, 'process.cpu.usage'))} p95={metric_value(_metric_stat(telemetry, 'process.cpu.usage', 'p95'), _metric_unit(telemetry, 'process.cpu.usage'))} max={metric_value(_metric_stat(telemetry, 'process.cpu.usage', 'max'), _metric_unit(telemetry, 'process.cpu.usage'))}",
        f"  memory_usage:    avg={bytes_human(_metric_stat(telemetry, 'process.memory.usage_bytes', 'avg'))} max={bytes_human(_metric_stat(telemetry, 'process.memory.usage_bytes', 'max'))}",
        f"  spans:           {telemetry.get('span_count', 0)} across {telemetry.get('agent_count', 0)} agents",
        f"  elapsed_time:    {(telemetry.get('trace_wall_time_seconds') or 0):.2f}s",
        f"  llm_call_time:   {(telemetry.get('llm_wall_time_seconds') or 0):.2f}s",
    ]
    return "\n".join(lines)


def render_comparison_report(runs, payloads: list[dict]) -> str:
    benchmark = runs[0].benchmark
    lines = [
        f"# Comparison of {len(runs)} {benchmark} runs",
        f"Selection: `{runs[0].campaign_selector}` or matched selectors in the same benchmark.",
    ]
    if benchmark == "finer":
        run_rows = []
        for run, payload in zip(runs, payloads):
            summary = payload["summary"]
            tests = payload.get("tests") or {}
            final = tests.get("final") or {}
            total_cost = (payload.get("costs") or {}).get("total") or {}
            run_rows.append(
                {
                    "run": _run_label(run),
                    "when": format_timestamp(run.timestamp) or run.timestamp or "-",
                    "config": run.config_slug or "-",
                    "generator": (payload.get("models") or {}).get("generator") or "-",
                    "reflector": (payload.get("models") or {}).get("reflector") or "-",
                    "curator": (payload.get("models") or {}).get("curator") or "-",
                    "final_tag_acc": pct(summary.get("final_tag_accuracy")),
                    "delta": pct_delta(summary.get("tag_accuracy_delta")),
                    "exact": count_pair(final.get("exact_correct"), final.get("total")),
                    "best_val": pct(summary.get("best_validation_accuracy")),
                    "cost": money(total_cost.get("cost_usd")),
                    "tokens": total_cost.get("total_tokens") or 0,
                }
            )
        lines.extend(["", "Outcome:", *_render_table(run_rows)])

        lines.extend(["", "Cost breakdown:"])
        cost_rows = []
        role_order = ("generator", "reflector", "curator")
        for run, payload in zip(runs, payloads):
            total_cost = (payload.get("costs") or {}).get("total") or {}
            llm_usage = payload.get("llm_usage") or {}
            row = {
                "run": _run_label(run),
                "total_cost": money(total_cost.get("cost_usd")),
                "total_tokens": scalar(total_cost.get("total_tokens")),
                "cached_in": scalar(total_cost.get("cached_input_tokens")),
                "cached_out": scalar(total_cost.get("cached_output_tokens")),
                "avg_time": f"{((llm_usage.get('total', {}).get('total_time') or 0.0) / (llm_usage.get('total', {}).get('calls') or 1)):.2f}s",
            }
            for role in role_order:
                role_cost = (payload.get("costs") or {}).get("roles", {}).get(role, {}).get("cost_usd")
                row[role] = money(role_cost)
            cost_rows.append(row)
        lines.extend(_render_table(cost_rows))

        lines.extend(["", "Accuracy breakdown:"])
        accuracy_rows = []
        for run, payload in zip(runs, payloads):
            summary = payload["summary"]
            tests = payload.get("tests") or {}
            initial = tests.get("initial") or {}
            final = tests.get("final") or {}
            tag_changes = payload.get("tag_changes") or {}
            accuracy_rows.append(
                {
                    "run": _run_label(run),
                    "initial_tag": pct(summary.get("initial_tag_accuracy")),
                    "final_tag": pct(summary.get("final_tag_accuracy")),
                    "correct_tags": count_pair(final.get("correct_tags"), final.get("total_tags")),
                    "exact": count_pair(final.get("exact_correct"), final.get("total")),
                    "no_answer": count_pair(final.get("no_answer"), final.get("total")),
                    "delta": pct_delta(summary.get("tag_accuracy_delta")),
                    "miscorrected_tags": f"{tag_changes.get('regressed_tags', 0)} (in {tag_changes.get('regressed_samples', 0)} samples)",
                    "corrected_tags": f"{tag_changes.get('improved_tags', 0)} (in {tag_changes.get('improved_samples', 0)} samples)",
                    "initial_exact": count_pair(initial.get("exact_correct"), initial.get("total")),
                }
            )
        lines.extend(_render_table(accuracy_rows))

        train_rows = []
        for run, payload in zip(runs, payloads):
            training = payload.get("training") or {}
            pre_post = payload.get("training_pre_post") or {}
            best = training.get("best_checkpoint") or {}
            train_rows.append(
                {
                    "run": _run_label(run),
                    "train_tag_pre": pct(pre_post.get("pre_tag_accuracy")),
                    "train_tag_post": pct(pre_post.get("post_tag_accuracy")),
                    "best_val": pct(training.get("best_accuracy") or best.get("val_accuracy")),
                    "best_step": best.get("step") or "-",
                    "checkpoint_count": training.get("checkpoint_count") or 0,
                }
            )
        lines.extend(["", "Validation / training:", *_render_table(train_rows)])

        telemetry_rows = []
        for run, payload in zip(runs, payloads):
            telemetry = payload.get("telemetry") or {}
            telemetry_rows.append(
                {
                    "run": _run_label(run),
                    "spans": telemetry.get("span_count", 0),
                    "cpu_avg": metric_value(_metric_stat(telemetry, "process.cpu.usage", "avg"), _metric_unit(telemetry, "process.cpu.usage")),
                    "cpu_p95": metric_value(_metric_stat(telemetry, "process.cpu.usage", "p95"), _metric_unit(telemetry, "process.cpu.usage")),
                    "cpu_max": metric_value(_metric_stat(telemetry, "process.cpu.usage", "max"), _metric_unit(telemetry, "process.cpu.usage")),
                    "mem_avg": bytes_human(_metric_stat(telemetry, "process.memory.usage_bytes", "avg")),
                    "mem_max": bytes_human(_metric_stat(telemetry, "process.memory.usage_bytes", "max")),
                    "elapsed_time": f"{(telemetry.get('trace_wall_time_seconds') or 0):.2f}s",
                    "llm_call_time": f"{(telemetry.get('llm_wall_time_seconds') or 0):.2f}s",
                }
            )
        lines.extend(["", "Telemetry:", *_render_table(telemetry_rows)])

        stability_rows = _stability_rows(runs)
        if stability_rows:
            lines.extend(["", "Stability:"])
            lines.extend(
                _render_table(
                    [
                        {
                            "left_run": row.get("left_run"),
                            "right_run": row.get("right_run"),
                            "label_jaccard": f"{row.get('label_jaccard', 0.0):.3f}",
                            "normalized_lcs": f"{row.get('normalized_lcs', 0.0):.3f}",
                            "left_spans": row.get("left_span_count"),
                            "right_spans": row.get("right_span_count"),
                        }
                        for row in stability_rows
                    ]
                )
            )

        note_lines = []
        for run, payload in zip(runs, payloads):
            playbooks = payload.get("playbooks") or {}
            if playbooks.get("best_equals_final") is False:
                note_lines.append(f"{_run_label(run)}: best and final playbooks differ.")
        if note_lines:
            lines.extend(["", "Notes:", *[f"  - {line}" for line in note_lines]])
        return "\n".join(lines)

    run_rows = []
    for run, payload in zip(runs, payloads):
        summary = payload["summary"]
        total_cost = (payload.get("costs") or {}).get("total") or {}
        telemetry = payload.get("telemetry") or {}
        run_rows.append(
            {
                "run": _run_label(run),
                "when": format_timestamp(run.timestamp) or run.timestamp or "-",
                "config": run.config_slug or "-",
                "models": _models_compact(run, payload),
                "task_goal": pct(summary.get("task_goal_completion")),
                "scenario_goal": pct(summary.get("scenario_goal_completion")),
                "failures": summary.get("failure_count"),
                "cost": money(total_cost.get("cost_usd")),
                "tokens": scalar(total_cost.get("total_tokens")),
                "cached_in": scalar(total_cost.get("cached_input_tokens")),
                "cached_out": scalar(total_cost.get("cached_output_tokens")),
                "cpu_avg": metric_value(_metric_stat(telemetry, "process.cpu.usage", "avg"), _metric_unit(telemetry, "process.cpu.usage")),
                "mem_max": bytes_human(_metric_stat(telemetry, "process.memory.usage_bytes", "max")),
            }
        )
    lines.extend(["", "Outcome:", *_render_table(run_rows)])
    telemetry_rows = _stability_rows(runs)
    if telemetry_rows:
        lines.extend(
            [
                "",
                "Stability:",
                *_render_table(
                    [
                        {
                            "left_run": row.get("left_run"),
                            "right_run": row.get("right_run"),
                            "label_jaccard": f"{row.get('label_jaccard', 0.0):.3f}",
                            "normalized_lcs": f"{row.get('normalized_lcs', 0.0):.3f}",
                        }
                        for row in telemetry_rows
                    ]
                ),
            ]
        )
    return "\n".join(lines)


def report(args):
    runs = get_runs(args)
    payloads = [summarize_run(run) for run in runs]
    text = render_run_report(runs[0], payloads[0]) if len(runs) == 1 else render_comparison_report(runs, payloads)
    rows = run_rows(runs)
    return build_command_result(
        title="Analysis",
        rows=rows,
        data={"count": len(runs), "runs": rows},
        text=text,
    )
