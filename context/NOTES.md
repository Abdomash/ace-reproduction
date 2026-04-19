# Implementation Notes

This file records assumptions and deviations encountered during implementation.

## 2026-04-04

- Assumption: `NOTES.md` did not exist in the repository root, so it was created to satisfy the request to track implementation assumptions.
- Assumption: MAESTRO telemetry can be imported either from an installed package or from local source at `projects/maestro/src`; fallback `sys.path` injection was added in `projects/ace/telemetry.py` to reduce environment friction.
- Deviation from strict dependency pinning plan: telemetry dependencies were not added to `projects/ace/pyproject.toml` in this patch set. Current approach relies on MAESTRO-side optional dependencies and local import fallback.
- Assumption: run folder naming should follow the adopted canonical run id, so ACE now writes into `save_dir/<run_id>` where `run_id` defaults to `ace_<task>_<mode>_<config>_<seed>_<timestamp>`.
- Assumption: preserve backward compatibility for `final_results.json` consumers by keeping previous top-level result keys in addition to the new `run_id`/`telemetry` wrapper fields.
- Unexpected pre-existing behavior: empty-response handling in `timed_llm_call` only recognized `train_*`/`test_*` call IDs. This was broadened to include `online_train_*` and `test_eval_*` to match current ACE call patterns.
- Assumption: telemetry should be best-effort. If MAESTRO telemetry import/setup fails, ACE run continues with telemetry disabled and records the startup error in run metadata.
- Assumption: default metrics interval should be task-specific per plan (`5s` for FiNER, `15s` otherwise) unless overridden by CLI/config.
- Deviation from strict scheduler execution policy: Slurm templates were added but not executed from this environment because `mcmgt01` access and cluster-side dry run are outside this workspace.
- Unexpected environment issue during smoke: local `maestro` import initially resolved to a non-repo package. `projects/ace/telemetry.py` now clears conflicting preloaded `maestro*` modules and retries import from local `projects/maestro/src`.
- Smoke execution note: because no real provider credentials are available here, LLM-path verification used deterministic local stubs/fake client to validate telemetry spans and output artifacts without external API calls.
- Partial local visualization run was executed with synthetic fake-client responses (no external API). This produced full artifact structure, telemetry, LLM logs, and ready-to-view plots under `analysis/outputs/local_partial_run/.../plots`.

## 2026-04-07

- Command log (current session): `git status --short`; `git diff --stat`; `git diff --cached --stat`; `git log --oneline -5`; `ls -la`; `ls -la ace`; `ls -la projects/ace/ace`; `python - <<'PY' ...`; `wc -l results/.../bullet_usage_log.jsonl`; `ps -eo ... | rg ...`; `pgrep -af ...`; `ss -tpn | rg ...`; `ls -lt results/...`; `git blame -L ... projects/ace/llm.py`; `git remote -v`; `webfetch https://arxiv.org/abs/...`; `bash resume.sh`.
