# AppWorld Integration Plan

## Scope and Intent

This document defines the full implementation plan for integrating the AppWorld agent benchmark into the ACE reproduction framework, following the pattern established by the FiNER integration but adapting for AppWorld's fundamentally different interactive coding agent paradigm.

AppWorld is an **interactive coding agent** benchmark -- the model generates Python code that executes against a live environment (9 apps, 457 APIs), not a single-shot text Q&A task. ACE wraps around a ReAct-style agent loop, making this integration substantially more complex than FiNER.


## Confirmed Decisions

- **Integration scope**: Full agent integration matching the ACE paper (ReAct agent loop over AppWorld execution environment).
- **Prompt source**: Port prompts from the original `ace-agent/ace-appworld` repository (not written from scratch).
- **Training approach**: Override in ACE core (`ace/ace/ace.py`) with `_train_single_appworld_sample()` for multi-step ReAct loop.
- **AppWorld package**: Use `https://github.com/ace-agent/ace-appworld/tree/main` directly (clone + editable install, pinned commit SHA), not vanilla `appworld` from PyPI.
- **Evaluation metrics**: TGC (Task Goal Completion) and SGC (Scenario Goal Completion) on test-normal and test-challenge splits.
- **Telemetry interval**: 15s (matching PLAN.md convention for AppWorld).
- **Run naming**: `ace_appworld_<mode>_<config>_<seed>_<timestamp>`.


## Architecture Overview

The original `ace-appworld` repo uses its own standalone agent loop (`StarAgent`/`Agent` classes) with its own LLM wrapper (`lite_llm_generator.py`). Our reproduction project has its own ACE orchestrator (`ace/ace/ace.py`) designed for FiNER-style text Q&A. We adapt our ACE orchestrator to support AppWorld's interactive agent pattern while keeping the FiNER flow intact.

Key architectural difference from FiNER:

| Aspect | FiNER | AppWorld |
|--------|-------|----------|
| Task type | Text Q&A | Interactive coding agent |
| Generator output | JSON with `final_answer` | Python code in ```python``` blocks |
| Evaluation | Exact string match | Database-state unit tests (TGC/SGC) |
| Per-sample cost | Single LLM call | Multi-step ReAct loop (5-30 LLM calls) |
| Environment | None | AppWorld execution sandbox |
| Playbook sections | STRATEGIES, FORMULAS, CODE SNIPPETS, MISTAKES, HEURISTICS, CONTEXT CLUES, OTHERS | STRATEGIES AND HARD RULES, APIS TO USE, CODE SNIPPETS, MISTAKES, HEURISTICS, VERIFICATION CHECKLIST, TROUBLESHOOTING, OTHERS |
| Reflection input | Reasoning trace + wrong answer | Full execution trace + API error messages |


## Phase 1: AppWorld Environment Setup

### 1.1 Clone and install the ACE-modified AppWorld (pinned)

```bash
cd /home/abdo/ace-reproduction
git lfs install
git clone https://github.com/ace-agent/ace-appworld.git ace-appworld
cd ace-appworld
git checkout <PINNED_ACE_APPWORLD_COMMIT_SHA>
export APPWORLD_PROJECT_PATH="$(pwd)"
```

### 1.2 Create virtual environment and install

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -e "experiments[simplified]"
appworld install --repo
```

Notes:
- Do not run `pip install appworld` from PyPI.
- Keep `ace-appworld` commit-pinned for reproducible runs.

### 1.3 Download data and verify

```bash
appworld download data
appworld verify tests
appworld verify tasks
```

### 1.4 Add optional dependency to `ace/pyproject.toml`

Do not add PyPI `appworld` to `ace/pyproject.toml`. Keep AppWorld installation in setup scripts/docs from the pinned repository clone.

Optional ACE-side extras can still be declared:

```toml
[project.optional-dependencies]
appworld = ["jinja2>=3.0.0"]
```


## Phase 2: New Files to Create

| # | File | Description |
|---|------|-------------|
| 1 | `ace/eval/appworld/__init__.py` | Package init |
| 2 | `ace/eval/appworld/react_agent.py` | ReAct agent loop wrapping AppWorld environment |
| 3 | `ace/eval/appworld/data_processor.py` | DataProcessor for AppWorld tasks (TGC/SGC evaluation) |
| 4 | `ace/eval/appworld/run.py` | CLI entry point (matches finance/mind2web pattern) |
| 5 | `ace/eval/appworld/prepare_data.py` | Script to generate JSONL metadata for AppWorld task splits |
| 6 | `ace/eval/appworld/data/sample_config.json` | Config pointing to task split metadata |
| 7 | `ace/eval/appworld/prompts/generator.txt` | Generator prompt (ported from original `appworld_react_generator_prompt.txt`) |
| 8 | `ace/eval/appworld/prompts/reflector.txt` | Reflector prompt (ported from original `appworld_react_reflector_no_gt_prompt.txt`) |
| 9 | `ace/eval/appworld/prompts/curator.txt` | Curator prompt (ported from original `appworld_react_curator_prompt.txt`) |
| 10 | `ace/eval/appworld/prompts/initial_playbook.txt` | Initial empty playbook for AppWorld |
| 11 | `ace/slurm/ace_appworld_smoke.sbatch` | Smoke test (1hr, 1 task, eval_only) |
| 12 | `ace/slurm/ace_appworld_pilot.sbatch` | Pilot run (6hr, small subset) |
| 13 | `ace/slurm/ace_appworld_full.sbatch` | Full experiment (24hr, 3 seeds x 3 configs) |


## Phase 3: Files to Modify

| # | File | Changes |
|---|------|---------|
| 1 | `ace/pyproject.toml` | Add optional `appworld` extra for helper libs only (no PyPI `appworld`) |
| 2 | `ace/ace/ace.py` | Add `_train_single_appworld_sample()`; modify `run()` to detect `task_type == "appworld"` and route to AppWorld-specific paths; add AppWorld empty playbook template |
| 3 | `ace/ace/prompts/generator.py` | Add `GENERATOR_PROMPT_APPWORLD` variant |
| 4 | `ace/ace/prompts/reflector.py` | Add `REFLECTOR_PROMPT_APPWORLD` variant |
| 5 | `ace/ace/prompts/curator.py` | Add `CURATOR_PROMPT_APPWORLD` variant with AppWorld-specific sections |
| 6 | `ace/ace/core/generator.py` | Add `generate_for_appworld()` method that formats AppWorld-specific prompt and extracts code blocks |
| 7 | `ace/telemetry.py` | Add explicit `"appworld"` recognition for 15s default interval |
| 8 | `ace/utils.py` | Add AppWorld playbook section slug mappings |
| 9 | `ace/playbook_utils.py` | Add AppWorld section-aware parsing (if needed) |


## Phase 4: Core Design Details

### 4.1 `react_agent.py` -- The Key New Component

This ports the original `SimplifiedReActStarAgent` and `SimplifiedReActAgent` to work with our ACE infrastructure. The key difference from FiNER is that each "sample" is a multi-step interactive episode.

```python
class AppWorldReActAgent:
    """ReAct agent that generates code and executes it in AppWorld environment.
    
    Ported from ace-appworld's SimplifiedReActStarAgent, adapted to use
    ACE's Generator/Reflector/Curator and telemetry infrastructure.
    """

    def __init__(self, generator, api_provider, model, max_tokens, ...):
        # Uses ACE's Generator for LLM calls, but manages its own message history
        # and AppWorld environment interaction

    def solve_task(self, task_id, playbook, max_steps=30):
        """Run the ReAct loop for a single AppWorld task (evaluation mode).
        
        Steps:
        1. Load AppWorld world for this task
        2. Build initial prompt from Jinja2 template with:
           - task instruction, supervisor info, app descriptions, playbook
        3. For each step (up to max_steps):
           a. Call Generator to produce code
           b. Extract Python code from ```python...``` blocks
           c. Execute code in world.execute(code)
           d. Append execution output to message history
           e. If world.task_completed(): break
        4. Return: execution trace, task_completed bool, messages history
        """

    def solve_task_with_reflection(self, task_id, playbook, reflector, curator,
                                    max_steps=30, max_retries=5, ...):
        """Extended solve that calls Reflector/Curator on failure (training mode).
        
        Steps:
        1. solve_task() with current playbook
        2. If task fails:
           a. Get test report from AppWorld evaluation
           b. Call Reflector with full execution trace + test report
           c. Call Curator to update playbook based on reflection
           d. Optionally retry with updated playbook
        3. Return: execution trace, task_completed, reflection_content, updated_playbook
        """

    def _build_initial_prompt(self, world, playbook):
        """Build the Jinja2-templated initial prompt for the ReAct loop."""
        # Uses the generator.txt prompt template
        # Fills: {{input_str}}, {{main_user}}, {{app_descriptions}}, {{playbook}}

    def _extract_code_from_response(self, text):
        """Extract Python code from ```python...``` blocks in model response.
        
        Handles:
        - Full code blocks: ```python\n...code...\n```
        - Partial code blocks (no closing ```)
        - Multiple code blocks (takes first if ignore_multiple_calls=True)
        """

    def _truncate_execution_output(self, output, max_chars=20000):
        """Truncate long execution outputs to avoid context overflow."""

    def _trim_message_history(self, messages, max_length=400000):
        """Trim old observation blocks when message history exceeds max_length.
        
        Strategy (from original):
        1. Replace old observation outputs with "[NOT SHOWN FOR BREVITY]"
        2. Remove complete history blocks if observations exhausted
        3. Always preserve last 5 interaction blocks
        """
```

### 4.2 `data_processor.py` -- AppWorld Evaluation

```python
class DataProcessor:
    """Processor for AppWorld agent tasks.
    
    Evaluation uses AppWorld's built-in database-state unit tests,
    reporting TGC (Task Goal Completion) and SGC (Scenario Goal Completion).
    """

    def __init__(self, task_name: str):
        self.task_name = task_name  # "appworld" or "appworld_challenge"

    def process_task_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Convert AppWorld task metadata to ACE standard format.
        
        Input: list of {task_id, instruction, supervisor, app_descriptions, ...}
        Output: list of {
            context: API docs + app descriptions + supervisor info,
            question: task instruction,
            target: task_id (for evaluation routing),
            others: {supervisor, ground_truth metadata, dataset_name, ...}
        }
        """

    def answer_is_correct(self, predicted: str, ground_truth: str) -> bool:
        """Check if a single task passed all unit tests.
        
        predicted: task_id or evaluation result dict
        ground_truth: task_id (used to look up evaluation)
        
        Calls appworld evaluate for this specific task.
        Returns True if task passed all no_op_fail unit tests.
        """

    def evaluate_accuracy(self, out: List[str], target: List[str]) -> float:
        """Return scalar TGC for ACE compatibility.

        This stays float so existing ACE formatting and logs continue to work.
        """

    def evaluate_metrics(self, out: List[str], target: List[str]) -> dict:
        """Compute full AppWorld metrics.
        
        Returns: {
            "tgc": float,
            "sgc": float, 
            "num_tasks": int,
            "num_scenarios": int,
            "accuracy": float  # mirrors tgc for compatibility
        }
        """
```

### 4.3 `prepare_data.py` -- Task Split Metadata

This script generates JSONL files containing task metadata (not the actual task data, which lives in AppWorld's own data directory). Each line contains:

```json
{
    "task_id": "e10a3c",
    "instruction": "Find my most liked song on Spotify...",
    "supervisor": {"first_name": "...", "last_name": "...", "email": "...", "phone_number": "..."},
    "app_descriptions": {"spotify": "...", "venmo": "..."},
    "dataset_name": "train",
    "difficulty": 2
}
```

Split files: `appworld_train.jsonl`, `appworld_val.jsonl`, `appworld_test_normal.jsonl`, `appworld_test_challenge.jsonl`

### 4.4 `run.py` -- CLI Entry Point

Follows the same pattern as `finance/run.py` with additional AppWorld-specific args:

```python
def parse_args():
    parser = argparse.ArgumentParser(description="ACE System - AppWorld")

    # Standard ACE args (same as finance/run.py)
    parser.add_argument("--task_name", required=True)  # "appworld" or "appworld_challenge"
    parser.add_argument("--mode", choices=["offline", "online", "eval_only"])
    parser.add_argument("--api_provider", choices=["sambanova", "together", "openai", "minimax"])
    parser.add_argument("--generator_model", "--reflector_model", "--curator_model")
    parser.add_argument("--num_epochs", "--max_num_rounds", "--curator_frequency", ...)
    parser.add_argument("--telemetry_enabled", "--seed", "--config_name", ...)

    # AppWorld-specific args
    parser.add_argument("--dataset_name", default="train",
                        choices=["train", "dev", "test_normal", "test_challenge"])
    parser.add_argument("--max_agent_steps", type=int, default=30,
                        help="Max ReAct loop iterations per task")
    parser.add_argument("--appworld_root", type=str, default=None,
                        help="Path to AppWorld root directory")
    parser.add_argument("--max_retries", type=int, default=5,
                        help="Max reflection+retry cycles per training task")
    parser.add_argument("--ignore_multiple_calls", action="store_true",
                        help="Use only first code block when multiple found")
    parser.add_argument("--max_prompt_length", type=int, default=None,
                        help="Max prompt length before trimming")
    return parser.parse_args()
```

Main flow:
1. Load task IDs from AppWorld via `load_task_ids(dataset_name)`
2. Load task metadata and convert to ACE sample format
3. Create ACE system
4. **Offline mode**: ACE training loop where each "sample" is an AppWorld task with multi-step ReAct interaction
5. **Eval only mode**: Run each test task through the ReAct agent with the learned playbook
6. **Online mode**: Sequential test + train on each task, updating playbook as you go
7. Compute TGC/SGC via AppWorld Python API from run artifacts (avoid per-task CLI subprocess overhead)

### 4.5 ACE Core Modifications (`ace/ace/ace.py`)

To avoid overloading `ace.py` with task-specific branches, introduce a thin task adapter boundary:

- Add an AppWorld task adapter (e.g., `ace/eval/appworld/task_adapter.py`) that owns agent-loop/evaluation specifics.
- Keep `ACE.run()` orchestration generic and delegate task-specific train/test paths through adapter hooks.
- Minimize changes to existing FiNER/Mind2Web code paths.

#### Task type detection

Add `task_type` awareness to the ACE class:

```python
class ACE:
    def __init__(self, ..., task_type: str = "standard"):
        self.task_type = task_type  # "standard" or "appworld"
```

#### AppWorld-specific empty playbook

```python
def _initialize_empty_playbook(self) -> str:
    if self.task_type == "appworld":
        return self._initialize_appworld_playbook()
    return self._initialize_standard_playbook()

def _initialize_appworld_playbook(self) -> str:
    return """## STRATEGIES AND HARD RULES

## APIS TO USE FOR SPECIFIC INFORMATION

## USEFUL CODE SNIPPETS AND TEMPLATES

## COMMON MISTAKES AND CORRECT STRATEGIES

## PROBLEM-SOLVING HEURISTICS AND WORKFLOWS

## VERIFICATION CHECKLIST

## TROUBLESHOOTING AND PITFALLS

## OTHERS"""
```

#### AppWorld-specific training

```python
def _train_single_appworld_sample(self, task_dict, data_processor, step_id, epoch, step,
                                    usage_log_path, log_dir, config_params, total_samples):
    """Train on a single AppWorld task with multi-step ReAct loop.
    
    Steps:
    1. Extract task_id from task_dict
    2. Run AppWorldReActAgent.solve_task_with_reflection()
    3. If task fails:
       a. Generator produces initial code (via ReAct loop)
       b. On failure, Reflector analyzes execution trace
       c. Curator updates playbook based on reflection
       d. Retry with updated playbook (up to max_num_rounds)
    4. If task succeeds:
       a. Reflector tags helpful playbook bullets
    5. Return pre_train_answer, post_train_answer, tracking_dict
    """
```

#### AppWorld-specific test evaluation

Override `_run_test()` to use the ReAct agent loop instead of single-shot evaluation:

```python
def _run_test(self, test_samples, data_processor, playbook, config, log_dir, save_path, prefix):
    if self.task_type == "appworld":
        return self._run_appworld_test(test_samples, data_processor, playbook, config, log_dir, save_path, prefix)
    # ... existing single-shot test logic
```

Implementation note: keep the returned object compatible with existing result consumers (`accuracy` as scalar float, with extra AppWorld metrics included alongside it).

### 4.6 AppWorld Playbook Sections

The AppWorld playbook uses different sections than FiNER. Section slug mappings need to be added to `ace/utils.py`:

```python
APPWORLD_SECTION_SLUGS = {
    "strategies_and_hard_rules": "str",
    "apis_to_use_for_specific_information": "api",
    "useful_code_snippets_and_templates": "code",
    "common_mistakes_and_correct_strategies": "mis",
    "problem_solving_heuristics_and_workflows": "heur",
    "verification_checklist": "veri",
    "troubleshooting_and_pitfalls": "trou",
    "others": "misc",
}
```

The Curator prompt must enforce this section whitelist (only ADD operations allowed):

```python
APPWORLD_ALLOWED_SECTIONS = {
    "strategies_and_hard_rules",
    "apis_to_use_for_specific_information",
    "useful_code_snippets_and_templates",
    "common_mistakes_and_correct_strategies",
    "problem_solving_heuristics_and_workflows",
    "verification_checklist",
    "troubleshooting_and_pitfalls",
    "others",
}
```

### 4.7 Prompt Templates

All three prompts are ported from the original `ace-appworld` repository.

Rendering rule:
- AppWorld prompt files are rendered via Jinja2 only.
- Existing ACE `.format()` prompts in `ace/ace/prompts/*.py` stay unchanged for current tasks.
- Do not pass Jinja templates through `.format()`.

#### Generator Prompt (`prompts/generator.txt`)

- Few-shot ReAct prompt with 2-3 worked examples
- Uses Jinja2 templates: `{{ playbook }}`, `{{ main_user.first_name }}`, `{{ main_user.last_name }}`, `{{ input_str }}`, `{{ app_descriptions }}`
- Format: `SYSTEM:\n...`, `USER:\n...`, `ASSISTANT:\n...```python\n...\n```` pattern
- The model generates Python code in ```python``` blocks, which are extracted and executed

#### Reflector Prompt (`prompts/reflector.txt`)

- Analyzes execution trace, identifies errors, root causes, correct approaches
- Template variables: `{{ground_truth_code}}`, `{{test_report}}`, `{{generated_code}}`, `{{execution_error}}`, `{{playbook}}`, `{{previous_reflection}}`
- Outputs JSON: `{reasoning, error_identification, root_cause_analysis, correct_approach, key_insight}`

#### Curator Prompt (`prompts/curator.txt`)

- Identifies new insights to ADD to the playbook based on reflections
- Template variables: `{initial_generated_code}`, `{final_generated_code}`, `{guidebook}`, `{current_playbook}`, `{question_context}`, `{gt}`
- Outputs JSON: `{reasoning, operations: [{type: "ADD", section, content}]}`
- Only ADD operations supported; section must be in the AppWorld whitelist

#### Initial Playbook (`prompts/initial_playbook.txt`)

- Small initial playbook with ~8 bullets across key sections (ported from original `appworld_initial_playbook.txt`)
- Contains basic strategies like "Always call apis.supervisor.complete_task() when done" and "Check API documentation before calling unfamiliar APIs"


## Phase 5: Slurm Templates

### Smoke (`ace_appworld_smoke.sbatch`)

```bash
#!/bin/bash --login
#SBATCH --job-name=ace_appworld_smoke
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --qos=normal
#SBATCH --time=01:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16GB
#SBATCH --gres=gpu:p100:1

# Run eval_only on a single task
python -m eval.appworld.run \
  --task_name appworld \
  --mode eval_only \
  --dataset_name dev \
  --max_agent_steps 10 \
  --api_provider "${API_PROVIDER}" \
  --generator_model "${GENERATOR_MODEL}" \
  --telemetry_enabled \
  --telemetry_metrics_interval_seconds 15 \
  --config_name smoke \
  --seed 42 \
  --save_path "${SAVE_PATH}"
```

### Pilot (`ace_appworld_pilot.sbatch`)

```bash
#!/bin/bash --login
#SBATCH --job-name=ace_appworld_pilot
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --qos=normal
#SBATCH --time=08:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32GB
#SBATCH --gres=gpu:v100:1

# Run offline training on small subset
python -m eval.appworld.run \
  --task_name appworld \
  --mode offline \
  --dataset_name train \
  --max_agent_steps 20 \
  --api_provider "${API_PROVIDER}" \
  --generator_model "${GENERATOR_MODEL}" \
  --reflector_model "${REFLECTOR_MODEL}" \
  --curator_model "${CURATOR_MODEL}" \
  --json_mode \
  --telemetry_enabled \
  --telemetry_metrics_interval_seconds 15 \
  --config_name pilot \
  --seed 42 \
  --save_path "${SAVE_PATH}"
```

### Full (`ace_appworld_full.sbatch`)

```bash
#!/bin/bash --login
#SBATCH --job-name=ace_appworld_full
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --qos=normal
#SBATCH --time=24:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=40GB
#SBATCH --gres=gpu:v100:1

run_one() {
  local config_name="$1"
  local seed="$2"
  local api_provider="$3"
  local generator_model="$4"
  local reflector_model="$5"
  local curator_model="$6"
  local dataset_name="$7"

  # Step 1: Offline adaptation
  python -m eval.appworld.run \
    --task_name appworld \
    --mode offline \
    --dataset_name train \
    --max_agent_steps 30 \
    --api_provider "${api_provider}" \
    --generator_model "${generator_model}" \
    --reflector_model "${reflector_model}" \
    --curator_model "${curator_model}" \
    --json_mode \
    --telemetry_enabled \
    --telemetry_metrics_interval_seconds 15 \
    --config_name "${config_name}_offline" \
    --seed "${seed}" \
    --save_path "${SAVE_PATH}"

  # Step 2: Evaluate on test_normal with learned playbook
  python -m eval.appworld.run \
    --task_name appworld \
    --mode eval_only \
    --dataset_name test_normal \
    --max_agent_steps 30 \
    --api_provider "${api_provider}" \
    --generator_model "${generator_model}" \
    --telemetry_enabled \
    --telemetry_metrics_interval_seconds 15 \
    --config_name "${config_name}_eval_test_normal" \
    --seed "${seed}" \
    --save_path "${SAVE_PATH}"

  # Step 3: Evaluate on test_challenge with learned playbook
  python -m eval.appworld.run \
    --task_name appworld \
    --mode eval_only \
    --dataset_name test_challenge \
    --max_agent_steps 30 \
    --api_provider "${api_provider}" \
    --generator_model "${generator_model}" \
    --telemetry_enabled \
    --telemetry_metrics_interval_seconds 15 \
    --config_name "${config_name}_eval_test_challenge" \
    --seed "${seed}" \
    --save_path "${SAVE_PATH}"
}

for seed in 42 43 44; do
  run_one "all_gptoss20b" "${seed}" "openai" "gpt-oss:20b" "gpt-oss:20b" "gpt-oss:20b"
  run_one "all_minimax" "${seed}" "minimax" "MiniMax-M2.5" "MiniMax-M2.5" "MiniMax-M2.5"
  run_one "mixed_reflector_strong" "${seed}" "openai" "gpt-oss:20b" "MiniMax-M2.5" "gpt-oss:20b"
done
```


## Phase 6: Execution Order

1. **Environment setup** -- Clone ace-appworld, install, download data, verify
2. **Create `ace/eval/appworld/` directory structure** -- `__init__.py`, `prompts/`, `data/`
3. **Port prompt templates** from original repo into `ace/eval/appworld/prompts/`
4. **Implement `react_agent.py`** -- The core ReAct agent loop
5. **Implement `data_processor.py`** -- TGC/SGC evaluation
6. **Implement `prepare_data.py`** -- Generate JSONL metadata for task splits
7. **Implement `run.py`** -- CLI entry point
8. **Modify ACE core** (`ace/ace/ace.py`) -- Add task_type awareness, AppWorld training path
9. **Add AppWorld playbook sections** to `playbook_utils.py`, `utils.py`, `telemetry.py`
10. **Add AppWorld prompt variants** to `ace/ace/prompts/generator.py`, `reflector.py`, `curator.py`
11. **Add `generate_for_appworld()`** to `ace/ace/core/generator.py`
12. **Create Slurm templates** -- smoke, pilot, full
13. **Smoke test** -- Run 1-2 tasks in eval_only mode with dev split
14. **Pilot test** -- Small subset of training + evaluation
15. **Update documentation** -- PLAN.md, NOTES.md


## Experimental Design

### Datasets and Modes

- **AppWorld train**: Used for offline adaptation
- **AppWorld dev**: Used for validation during offline training
- **AppWorld test_normal**: Primary test split for evaluation
- **AppWorld test_challenge**: Harder test split for evaluation

### Model Configurations

For each task/mode, run the following matrix (matching FiNER):

1. `all_minimax`: Generator=MiniMax-M2.5, Reflector=MiniMax-M2.5, Curator=MiniMax-M2.5
2. `all_gptoss20b`: Generator=GPT-oss-20b, Reflector=GPT-oss-20b, Curator=GPT-oss-20b
3. `mixed_reflector_strong`: Generator=GPT-oss-20b, Reflector=MiniMax-M2.5, Curator=GPT-oss-20b

### Repeats and Seeds

- Minimum 3 seeds per config: `[42, 43, 44]`
- All output paths carry seed and run_id for traceability

### Metrics

- **TGC** (Task Goal Completion): Fraction of tasks where all no_op_fail unit tests pass
- **SGC** (Scenario Goal Completion): Fraction of scenarios (groups of related tasks) fully completed
- **System-level telemetry**: Same as FiNER (latency, tokens, CPU/memory, cost)
- **Stability**: Call-graph Jaccard/LCS across repeated runs


## Key Risks and Mitigations

1. **AppWorld package compatibility**: The ACE-modified `ace-appworld` repo may have API differences from vanilla `appworld`.
   - Mitigation: Install from the ACE fork, not PyPI. Pin the version.

2. **Code execution safety**: AppWorld executes arbitrary LLM-generated code.
   - Mitigation: AppWorld uses IPython sandboxing. Ensure this works in our Slurm environment. Consider Docker isolation if needed.

3. **Long runtimes**: Each AppWorld task involves multi-step code execution (5-30 LLM calls per task). A full training run over hundreds of tasks will take many hours.
   - Mitigation: Generous Slurm time limits (24hr for full). Staged rollout (smoke -> pilot -> full).

4. **Playbook format mismatch**: AppWorld uses different playbook sections than FiNER. The curator and playbook utilities need section-aware handling.
   - Mitigation: Add `task_type` parameter to playbook utilities; use AppWorld-specific section lists when task_type is "appworld".

5. **Original repo prompt template format**: The original uses Jinja2 templates with `{{ }}` syntax, while our ACE framework uses Python `.format()` with `{}`.
   - Mitigation: Keep the original Jinja2 format for AppWorld prompts (they are loaded from .txt files and rendered with Jinja2), separate from ACE's existing Python-format prompts.

6. **Message history management**: The ReAct loop accumulates long message histories that need trimming.
   - Mitigation: Port the original's `_trim_message_history()` and `trimmed_messages` property, which progressively shortens old observation blocks.

7. **Test evaluation integration**: AppWorld evaluation can be invoked via CLI, but subprocess-per-task is slow and brittle.
   - Mitigation: Prefer AppWorld Python API (`world.evaluate()` or equivalent) in-process for training/test loops; reserve CLI for whole-run sanity checks.


## Validation and Quality Gates

### Smoke Test Criteria

- One AppWorld dev task completes the ReAct loop (even if task fails)
- Telemetry traces are generated with correct span hierarchy
- Playbook is updated if Curator is called
- Results directory has expected artifact structure

### Pilot Test Criteria

- Offline training completes on a small subset (10-20 tasks)
- Validation accuracy (TGC) is computed and tracked
- Final test evaluation on test_normal produces TGC/SGC scores
- All telemetry metrics are plausible (non-negative latencies, reasonable token counts)

### Full Experiment Quality

- No missing run metadata (config/model/provider/seed/run_id)
- All matrix cells have complete outputs or documented failure reasons
- Re-runs are deterministic where expected (seeded), with variance reported where stochastic
