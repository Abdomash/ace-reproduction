# ACE x MAESTRO Reproduction and Experiment Plan

## Scope and Intent

This document defines the full implementation and experiment plan for reproducing and extending ACE under MAESTRO-style observability, based on the proposal in `new-proposal-template.tex` and review of the `projects/ace/` and `projects/maestro/` codebases.

Per instruction, this is a planning artifact only. No implementation work is started in this phase.


## Confirmed Decisions

- MiniMax integration will assume an OpenAI-compatible API.
  - Provider key: `MINIMAX_API_KEY`
  - Optional endpoint override: `MINIMAX_BASE_URL`
- API routing strategy (adopted):
  - Smoke and pilot runs may use local Ollama endpoint with `gpt-oss:20b`.
  - Full MiniMax conditions use OpenAI-compatible MiniMax/OpenRouter endpoint.
- Run naming convention (adopted):
  - `ace_<task>_<mode>_<config>_<seed>_<timestamp>`
- Metrics collection interval (adopted):
  - FiNER runs: `5s`
  - AppWorld runs: `15s`
- Execution environment policy (adopted):
  - Submit all reproducibility runs via Slurm from `mcmgt01`.
  - Use batch jobs (`sbatch`) for smoke, pilot, and full experiment runs.
  - Use `normal` QoS (no `spot` for baseline reproduction).
  - Interactive jobs are debug-only and out-of-scope for benchmark reporting.
- Scope decision for current implementation cycle (adopted):
  - Focus on FiNER only.
  - Defer AppWorld execution and analysis until submodule/environment readiness is resolved.


## Objectives

1. Reproduce ACE methodology on a different LLM backbone (MiniMax-M2.5) for FiNER and AppWorld.
2. Integrate MAESTRO-compatible OpenTelemetry traces/metrics into ACE execution.
3. Evaluate mixed-model assignment with stronger Reflector and cheaper Generator/Curator.
4. Produce reproducible accuracy/resource/cost analyses including call-graph stability.

Note:
- For this implementation cycle, objectives are executed on FiNER only; AppWorld is deferred.


## Codebase Findings That Shape the Plan

### ACE findings

- Main orchestration and training/testing loops are in `projects/ace/ace/ace.py`.
- LLM call funnel is `timed_llm_call` in `projects/ace/llm.py`.
- Provider initialization is centralized in `projects/ace/utils.py` (`initialize_clients`).
- Finance experiment entrypoint and argument surface are in `projects/ace/eval/finance/run.py`.
- Mind2Web runner has a similar argument/config structure in `projects/ace/eval/mind2web/run.py`.
- Existing outputs already include rich artifacts (`run_config.json`, test/train results, logs, playbooks), which can be extended with telemetry metadata paths.

### MAESTRO findings

- Reusable OTEL helpers already exist in `projects/maestro/src/maestro/telemetry_helpers/langgraph_otel/__init__.py`.
  - `setup_jsonl_tracing`
  - `PsutilMetricsRecorder`
  - OTEL attribute conventions and helper functions
- Metric helpers and templates exist and align with proposal needs:
  - `projects/maestro/src/maestro/telemetry_helpers/template/otel_span_template_for_human_reading.json`
  - `projects/maestro/src/maestro/telemetry_helpers/template/otel_metrics_template_for_human_reading.json`
- Post-processing/plotting utilities exist in `projects/maestro/tools/` and `projects/maestro/plot/`.

### Environment findings and blocker

- `projects/ace-appworld/` is empty in the current checkout.
- `.gitmodules` indicates AppWorld is a submodule, so AppWorld reproduction is blocked until submodule sync/init and environment setup are completed.


## Execution Environment and Scheduler Policy

## Runtime topology

- Launch and submission point: Slurm head node `mcmgt01`.
- Experiment mode for reproducibility: `sbatch` batch jobs.
- Interactive `srun` sessions are allowed for development/debug only and should not be used for reported benchmark numbers.

## QoS and preemption policy

- Baseline policy: `--qos=normal`.
- Do not use `spot` for FiNER baseline matrix.
- No preemption/checkpointing logic is required for baseline reproduction runs under this policy.

## Resource policy

- Request one GPU per run unless a specific experiment requires more.
- Do not request exclusive node access unless required by workload behavior.
- Start with weakest sufficient GPU type and scale up only when justified by runtime or memory constraints.
- Set explicit `--time`, `--cpus-per-task`, and `--mem` in every sbatch script.

## Harness occupancy guidance

- Smoke and development checks may run on shared capacity.
- Pilot and full FiNER matrix runs should use stable scheduled allocations (batch) to reduce timing/resource noise.
- If queue contention materially impacts schedule predictability, request a reservation window.

## Operational monitoring policy

- During pilot runs, inspect `jobstats` to validate requested CPU/memory/GPU sizing.
- Track job state and failures via `sacct`/`srecent` and record failure reasons per matrix cell.
- Ensure jobs remain compliant with cluster utilization policies to avoid auto-termination.


## Experimental Design

## Datasets and modes

- FiNER:
  - Offline adaptation
  - Online adaptation
  - Eval-only sanity checks as needed

Current scope:
- AppWorld modes are deferred and excluded from this implementation cycle.

## Model configurations

For each task/mode, run the following matrix:

1. `all_minimax`
   - Generator: MiniMax-M2.5
   - Reflector: MiniMax-M2.5
   - Curator: MiniMax-M2.5
2. `all_gptoss20b`
   - Generator: GPT-oss-20b
   - Reflector: GPT-oss-20b
   - Curator: GPT-oss-20b
3. `mixed_reflector_strong`
   - Generator: GPT-oss-20b
   - Reflector: MiniMax-M2.5
   - Curator: GPT-oss-20b

## Repeats and seeds

- Minimum recommended repeats per config: 3 seeds.
- Seed list example: `[42, 43, 44]`.
- All output paths and metadata should carry seed and run_id for traceability.


## Metrics and Evaluation Targets

## Accuracy

- FiNER: exact/equivalent correctness based on ACE finance data processor logic.
- AppWorld: TGC and SGC as supported by AppWorld evaluation flow.

## System-level telemetry

- Per-run and per-agent latency (span durations).
- Token usage:
  - `gen_ai.usage.input_tokens`
  - `gen_ai.usage.output_tokens`
  - `gen_ai.usage.total_tokens`
- Communication size proxies:
  - `communication.input_message_size_bytes`
  - `communication.output_message_size_bytes`
  - `communication.total_message_size_bytes`
- Process resource time series:
  - `process.cpu.usage`
  - `process.memory.usage_bytes`

## Cost

- Token-based cost estimation via pricing map:
  - MiniMax pricing from proposal assumptions
  - GPT-oss-20b local/cluster accounting policy (if no API price, track infra proxy separately)

## Stability / call-graph

- Jaccard similarity of tool/call sets across repeated runs.
- LCS similarity for sequence/order consistency across runs.


## Telemetry Integration Plan (Design)

## Integration points

1. Run lifecycle in `ACE.run()`:
   - Create run_id and telemetry output dirs.
   - Start tracing and metrics recorder at run start.
   - Stop/flush on completion and on exceptions.
2. Agent-level orchestration spans in `projects/ace/ace/ace.py`:
   - Generator/Reflector/Curator invocation spans (`invoke_agent`).
3. LLM call-level spans in `projects/ace/llm.py`:
   - `call_llm` span per API call with usage, model, latency, comm bytes.
4. Persist telemetry paths in run metadata:
   - Add trace and metrics log paths to config/results artifacts.

## Attribute conventions

Use MAESTRO-compatible names and payload structure:

- `gen_ai.operation.name`: one of `invoke_agent`, `call_llm`, `execute_tool` (if applicable later)
- `agent.name`
- `gen_ai.system`
- `gen_ai.request.model`
- usage and communication fields listed above
- status fields on failures/timeouts

## Error and retry behavior in telemetry

- Preserve ACE retry/empty-response behavior as-is.
- Record retries as span events/attributes where possible.
- Mark failures with OTEL error status and category attributes when available.


## Provider and Configuration Plan

## MiniMax provider support

- Extend provider switch in `projects/ace/utils.py` with `minimax` option.
- Instantiate OpenAI-compatible client with:
  - `api_key = MINIMAX_API_KEY`
  - `base_url = MINIMAX_BASE_URL` if set, else default MiniMax-compatible URL
- Keep existing provider paths unchanged.

## CLI updates

- Extend `--api_provider` choices in:
  - `projects/ace/eval/finance/run.py`
  - `projects/ace/eval/mind2web/run.py`
- Keep per-agent model args unchanged to support mixed-model runs.

## API routing policy

- `all_gptoss20b`:
  - Use local Ollama/OpenAI-compatible endpoint for smoke and pilot runs.
- `all_minimax` and `mixed_reflector_strong` with MiniMax reflector:
  - Use OpenAI-compatible MiniMax/OpenRouter endpoint with `MINIMAX_API_KEY`.
- Persist provider and endpoint label in run metadata for reproducibility.


## Execution and Artifact Layout

## Run naming

- Canonical run_id:
  - `ace_<task>_<mode>_<config>_<seed>_<timestamp>`

## Directory structure (proposed)

```text
results/
  ace_finer_offline_all_minimax_42_YYYYMMDD_HHMMSS/
    run_config.json
    final_results.json
    train_results.json
    val_results.json
    initial_test_results.json
    final_test_results.json
    final_playbook.txt
    best_playbook.txt
    detailed_llm_logs/
    telemetry/
      run_<run_id>.otel.jsonl
      plan-and-execute_<run_id>.metrics.jsonl   # name may be ACE-specific
    analysis/
      summary.json
```

Notes:
- Existing ACE output conventions stay intact.
- New telemetry files are nested under a dedicated `telemetry/` folder per run.


## Experiment Phases and Work Breakdown

## Phase 0: Readiness and dependency checks

- Verify `maestro` telemetry helper importability from ACE environment.
- Confirm package/environment strategy (editable install or `PYTHONPATH`) for cross-repo imports.
- Confirm API env vars and secret management strategy.
- Validate Slurm execution path from `mcmgt01` with one minimal `sbatch` dry run.
- Confirm `normal` QoS job submission template and baseline resource defaults.

Deliverable:
- Readiness checklist with pass/fail status and resolved blockers.

## Phase 1: Telemetry scaffolding in ACE

- Add optional telemetry config surface in ACE runtime config.
- Add run-level telemetry lifecycle management.
- Add run-level metadata persistence for telemetry log paths.

Deliverable:
- One smoke run producing valid ACE outputs plus telemetry files.

## Phase 2: Agent and call instrumentation

- Add `invoke_agent` spans around Generator/Reflector/Curator invocations.
- Add `call_llm` spans in `timed_llm_call` with usage/bytes/status.
- Validate emitted schema against MAESTRO templates.

Deliverable:
- Schema-validated trace sample with expected span hierarchy.

## Phase 3: MiniMax provider integration

- Add `minimax` provider path.
- Update CLI choices.
- Validate connectivity with small test calls.

Deliverable:
- Passing smoke run using MiniMax provider.

## Phase 4: FiNER full experiment batch

- Execute matrix (3 configs x modes x seeds).
- Ensure all runs include telemetry and standard ACE outputs.
- Run all matrix jobs via Slurm batch on `normal` QoS.

Deliverable:
- Complete FiNER run set ready for analysis.

## Phase 5: FiNER analysis and reporting artifacts

- Aggregate per-run metrics: accuracy, latency, tokens, cost.
- Generate CPU/memory time series and role-level breakdowns.
- Compute call-graph stability (Jaccard/LCS).

Deliverable:
- FiNER analysis package (tables + plots + interpretation notes).

## Phase 6: Final synthesis (FiNER-focused in this cycle)

- Compare FiNER trends and tradeoffs across model-role configurations.
- Produce final reproducibility report artifacts for write-up.

Deliverable:
- Final FiNER figures, summary tables, and narrative-ready findings.


## Validation and Quality Gates

## Telemetry validation

- Trace JSONL lines parse cleanly.
- Required fields present for core spans.
- Metrics JSONL has regular cadence at configured interval.
- Span durations and token counts are non-negative and plausible.

## Experiment quality

- No missing run metadata (config/model/provider/seed/run_id).
- All matrix cells have complete outputs or documented failure reasons.
- Re-runs are deterministic where expected (seeded), with variance reported where stochastic.


## Cost Accounting Plan

- Use trace token attributes for token totals per role and per run.
- Apply provider-model pricing map to estimate API cost.
- Report:
  - total cost
  - cost per correct sample
  - cost vs accuracy frontier
- For local GPT-oss-20b runs, report separately if API price is not applicable.


## Per-Agent CPU/Memory Attribution Method

Because CPU/memory are process-level samples, per-agent attribution will be derived via temporal overlap:

1. Collect metric samples `(timestamp, cpu, rss)`.
2. Collect agent spans with `(agent, start_time, end_time)`.
3. Attribute each metric sample to active span(s) at that timestamp.
4. Aggregate attributed samples by agent (mean, median, p95, area-under-curve approximations).

This method will be documented as an approximation and reported alongside assumptions.


## Risks and Mitigations

1. AppWorld submodule missing/uninitialized.
   - Mitigation: make AppWorld Phase 6 conditional on submodule readiness; proceed with FiNER first.
2. Cross-repo dependency/import friction (ACE importing MAESTRO helper modules).
   - Mitigation: define explicit environment strategy early (editable install or PYTHONPATH).
3. Provider API inconsistencies under OpenAI-compatible endpoints.
   - Mitigation: include provider-specific fallback for token key differences and error handling.
4. Long runtime/cost for full matrix.
   - Mitigation: staged rollout (smoke -> pilot -> full), with go/no-go checks at each stage.
5. Telemetry overhead affecting measured latency.
   - Mitigation: measure baseline overhead with telemetry off/on for a subset and report overhead.
6. Slurm queue variability affecting wall-clock predictability.
   - Mitigation: use `normal` QoS, enforce explicit resource requests/time limits, and request reservation if timeline risk emerges.
7. Job interruption from cluster policies or mis-sized requests.
   - Mitigation: pilot with `jobstats`, refine resource requests, and track failure causes in matrix-level run log.


## Milestones

1. ACE + MAESTRO telemetry integration, MiniMax provider, smoke validation.
2. FiNER reproduction with MiniMax + telemetry capture.
3. Stronger-Reflector FiNER experiments and tradeoff analysis.
4. Consolidated FiNER analysis, plots, and final write-up preparation.

Deferred milestone:
- AppWorld setup and reproduction (pending submodule/environment readiness).


## Immediate Next Actions (when implementation starts)

1. Implement telemetry config + lifecycle in `ACE.run()`.
2. Instrument `timed_llm_call` and agent invocation boundaries.
3. Add `minimax` provider and CLI provider choices.
4. Add Slurm sbatch templates for smoke/pilot/full FiNER runs on `normal` QoS.
5. Run FiNER micro-smoke test through Slurm and validate output schemas.
6. Freeze experiment command matrix and launch pilot then full FiNER batch.


## Out-of-Scope for Initial Implementation

- Altering benchmark semantics versus ACE paper setup except where required for observability and mixed-model experiments.
- AppWorld execution and analysis in this cycle, until submodule/environment readiness is resolved.
