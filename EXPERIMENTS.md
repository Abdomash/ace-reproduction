# Experiments Needed to Complete the Project

This file tracks the experiment work needed to finish the ACE reproduction under
MAESTRO observability. It assumes AppWorld setup follows `APPWORLD.md` and that
AppWorld integration is handled through the vendored `ace-appworld/` runner.

## Current Baseline

The current report is based on one local FiNER offline pilot:

- Model setup: GPT-oss-20b for Generator, Reflector, and Curator.
- Split sizes: 60 train, 40 validation, 80 test.
- Seed: 42.
- Telemetry: enabled, 5-second metrics interval.
- Reported result: initial test accuracy `0.14375`, final test accuracy
  `0.15625`, best validation accuracy `0.21875`.

This pilot is useful as an end-to-end observability proof. It is not enough for
the final project because it does not compare model configurations, baselines,
seeds, telemetry overhead, or AppWorld splits. New final experiments should use
GPT-oss-120b through OpenRouter for the cheap-model role and
`minimax/minimax-m2.7` through OpenRouter for the stronger MiniMax role.

## Experiment Matrix

### 1. FiNER Smoke Validation

Goal: verify that the FiNER runner, telemetry, result files, and analysis scripts
work before launching expensive runs.

Run a tiny FiNER slice with telemetry enabled:

- `train`: 5-10 examples
- `val`: 5-10 examples
- `test`: 5-10 examples
- `seed`: 42
- `model`: GPT-oss-120b through OpenRouter

Record:

- final result JSON
- trace JSONL path
- metrics JSONL path
- generated plots
- count of LLM calls by role
- token usage by role

Pass condition:

- run completes without manual intervention
- trace and metrics files are non-empty
- result JSON contains initial, validation, and final metrics

### 2. FiNER Pilot Matrix

Goal: answer whether ACE behavior changes across model assignment choices on
the same small section-sized split used by the report.

Use the same data sizes for every run:

- `train`: 60 examples
- `val`: 40 examples
- `test`: 80 examples
- `seeds`: 42, 43, 44
- telemetry enabled with 5-second interval

Run these configurations:

| Config | Generator | Reflector | Curator | Purpose |
| --- | --- | --- | --- | --- |
| `react_no_playbook_gptoss120b` | GPT-oss-120b | none | none | baseline without ACE adaptation |
| `ace_all_gptoss120b` | GPT-oss-120b | GPT-oss-120b | GPT-oss-120b | cheap single-model ACE |
| `ace_all_minimax_m27` | minimax/minimax-m2.7 | minimax/minimax-m2.7 | minimax/minimax-m2.7 | stronger single-model ACE |
| `ace_mixed_strong_reflector` | GPT-oss-120b | minimax/minimax-m2.7 | GPT-oss-120b | proposed reflector-impact test |

Report:

- initial test accuracy
- best validation accuracy
- final test accuracy
- no-answer rate
- token usage by role
- wall-clock runtime
- estimated or measured cost
- CPU and memory summary

### 3. FiNER Larger Run

Goal: check whether pilot trends hold on a larger FiNER slice.

Use:

- full configured train file if affordable, otherwise at least 500-1000 train
  examples
- full configured validation file if affordable, otherwise at least 300-500
  validation examples
- full available test subset
- `seeds`: at least 42; preferably 42, 43, 44

Prioritize configurations from the pilot:

- best single-model ACE config
- `ace_mixed_strong_reflector`
- `react_no_playbook` baseline

Report the same metrics as the pilot matrix, plus:

- playbook length over time
- playbook token count over time
- validation curve over training steps

### 4. Reflector Impact Ablation

Goal: isolate whether the Reflector benefits from a stronger model more than
the other roles.

Run at least on the 60/40/80 FiNER split:

| Config | Generator | Reflector | Curator |
| --- | --- | --- | --- |
| `all_cheap` | GPT-oss-120b | GPT-oss-120b | GPT-oss-120b |
| `strong_reflector` | GPT-oss-120b | minimax/minimax-m2.7 | GPT-oss-120b |
| `strong_curator` | GPT-oss-120b | GPT-oss-120b | minimax/minimax-m2.7 |
| `all_strong` | minimax/minimax-m2.7 | minimax/minimax-m2.7 | minimax/minimax-m2.7 |

Main comparison:

- accuracy gain per added dollar/token
- validation gain per added dollar/token
- no-answer reduction
- role-level token and latency breakdown

### 5. Telemetry Overhead

Goal: quantify the cost of MAESTRO observability.

For one representative FiNER setup, run matched pairs:

- telemetry enabled
- telemetry disabled

Use the same:

- model config
- data slice
- seed
- worker count
- max rounds
- curator frequency

Report:

- wall-clock runtime delta
- LLM call count delta
- accuracy delta
- trace file size
- metrics file size
- CPU and memory delta

Interpretation rule:

- if accuracy differs materially, rerun because telemetry should not change the
  model/task behavior except through timing or API instability.

### 6. Call-Graph Stability

Goal: answer the proposal question about call-graph stability across repeated
runs.

For each selected configuration, run at least three seeds or repeated runs.

Compute:

- Jaccard similarity over span operation/agent sets
- LCS similarity over ordered span labels
- counts of `call_llm`, `invoke_agent`, and environment/tool spans
- per-role span count distribution

Recommended span label:

```text
<agent.name>:<gen_ai.operation.name>
```

For AppWorld, include tool/environment spans if present.

### 7. FiNER Failure Analysis

Goal: explain why accuracy changes and whether failures come from model quality,
formatting, parsing, or adaptation behavior.

Sample at least 30 incorrect FiNER outputs per key configuration and categorize:

- no final answer
- invalid JSON or malformed response
- wrong number of comma-separated tags
- valid format but wrong tags
- empty response or API failure
- regression after reflection/curation

Report:

- category counts
- representative examples
- whether the final answer failed before or after reflection

### 8. AppWorld Smoke

Goal: validate AppWorld end-to-end execution with telemetry using the vendored
`ace-appworld/` setup described in `APPWORLD.md`.

Run:

```bash
cd ace-appworld
source .venv/bin/activate
export APPWORLD_PROJECT_PATH="$(pwd)"
APPWORLD_MAESTRO_TELEMETRY=1 \
APPWORLD_MAESTRO_METRICS_INTERVAL_SECONDS=1 \
appworld run ACE_online_no_GT \
  --task-id 50e1ac9_1 \
  --override '{"config":{"dataset":"dev","agent":{"max_steps":0,"logger_config":{"verbose":false,"color":false}}}}' \
  --root .
```

Pass condition:

- telemetry metadata file exists
- OTEL trace JSONL exists
- metrics JSONL exists
- run exits cleanly

Then run a real small subset:

```bash
appworld run ACE_online_no_GT \
  --override '{"config":{"dataset":"dev","sample_size":3}}' \
  --root .
```

### 9. AppWorld Full Evaluation

Goal: complete the proposal's AppWorld reproduction component.

Run at least:

- ReAct/no-ACE baseline if available
- ACE online no-GT
- ACE offline no-GT adaptation followed by evaluation

Evaluate on:

- `test_normal`
- `test_challenge`

Report:

- Task Goal Completion (TGC)
- Scenario Goal Completion (SGC)
- per-split runtime
- per-split token usage
- CPU/memory summary
- telemetry call graph summary

Use:

```bash
appworld evaluate <EXPERIMENT_NAME> test_normal --root .
appworld evaluate <EXPERIMENT_NAME> test_challenge --root .
```

### 10. Cost-Accuracy Tradeoff

Goal: support the final cost-accuracy discussion.

For every FiNER and AppWorld run, aggregate:

- input tokens by role
- output tokens by role
- total tokens by role
- wall-clock LLM call duration by role
- estimated API cost by role
- total run cost
- final task metric

Required plots:

- cost vs accuracy
- token usage by role
- latency by role
- CPU/memory timeline
- playbook growth over training steps

## Minimum Final Report Set

The final report should include at least:

- FiNER pilot matrix over three seeds
- one larger FiNER run or a clear explanation for why it was infeasible
- telemetry overhead comparison
- call-graph stability analysis
- AppWorld smoke and at least one AppWorld evaluated split
- cost-accuracy table for the tested model configurations

## Optional If Time Allows

- Run Formula as a second finance task.
- Add Dynamic Cheatsheet or GEPA-style baseline if implementation time permits.
- Run AppWorld `test_normal` and `test_challenge` for all model configurations,
  not just the best FiNER-derived configuration.
