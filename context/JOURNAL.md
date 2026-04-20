# Journal

## 2026-04-20 - Fixed zero latency/cost-timing in MAESTRO telemetry

The MAESTRO analysis run for `openrouter-gpt-oss-120b` showed all LLM-related
timing as zero: `duration_ns=0`, `start_time=end_time=1684411200000000000`,
`wall_time_seconds=0.0`, `llm.call_time_seconds=0.0`. Token counts and dollar
costs were correct.

**Root cause**: AppWorld uses `freezegun.freeze_time()` to freeze the system
clock to each task's simulated datetime (e.g. 2023-05-18) so that business
logic (`DateTime.now()`, verification-code expiry, subscription checks, etc.)
behaves deterministically. Freezegun globally patches `time.time_ns()`,
`time.time()`, and `time.perf_counter()` — the exact functions the
OpenTelemetry SDK and ACE telemetry code rely on for span timestamps and
wall-clock measurements. All spans created inside the `AppWorld` context got
the same frozen timestamp, making `start_time == end_time` and all durations
zero.

**Fix**: Use `freezegun.api.real_time_ns` and `freezegun.api.real_perf_counter`
— saved references to the original unpatched functions that always return real
wall-clock time. Stored in a dict (which freezegun cannot traverse) with a
graceful fallback to `time.time_ns`/`time.perf_counter` when freezegun is
absent.

Changed files:
- `ace-appworld/experiments/code/ace/telemetry.py` — added
  `_real_time_ns()`/`_real_perf_counter()` helpers; `telemetry_span()` now
  passes `start_time=_real_time_ns()` and `end_on_exit=False` with explicit
  `span.end(end_time=_real_time_ns())`; wall-clock via `_real_perf_counter()`.
- `ace-appworld/experiments/code/ace/lite_llm_generator.py` — LLM call timing
  now uses `_real_perf_counter()` instead of `time.perf_counter()`.

The experiment results need to be re-run after this fix.

## 2026-04-19 - OpenRouter FiNER smoke comparison

Finished the 2026-04-19 FiNER smoke experiments comparing `minimax/minimax-m2.7`,
`openai/gpt-oss-120b:nitro`, and `openai/gpt-oss-20b:nitro` on the same subset
setup.

At the tag-accuracy level, `minimax/minimax-m2.7` showed the strongest improvement:
51.88% initial to 68.44% final, a +16.56pp gain. The two GPT-OSS 120B smoke runs
were also clearly useful, improving from 52.19% to 61.56% (+9.38pp) and from 54.69%
to 66.25% (+11.56pp). By contrast, GPT-OSS 20B only moved from 38.12% to 40.00%
(+1.88pp) and from 40.94% to 41.88% (+0.94pp).

The high-level takeaway is that MiniMax M2.7 had a substantial ACE improvement on
this subset, while GPT-OSS 120B was also pretty good and much stronger than GPT-OSS
20B in these runs.

## 2026-04-18 - Paper-faithful ACE defaults

Several FiNER smoke runs started failing in a strange way: the API call returned a
valid-looking chat completion object, but `message.content` was `None`, so ACE logged
`API returned None content` and marked the sample incorrect. The failures were much
more common on thinking models such as `openai/gpt-oss-20b` and
`minimax/minimax-m2.7` through OpenRouter than on `openai/gpt-oss-120b`.
Curator calls also occasionally crashed while the OpenAI client was parsing malformed
provider JSON.

The important distinction is that the original ACE paper/released-code path uses
standard non-thinking chat-completion behavior. ACE should consume only visible
`message.content` from Generator, Reflector, and Curator calls. Provider-returned
reasoning is diagnostic metadata only and is not passed to the Curator or used to
update the playbook.

The default reproduction path is restored to `max_tokens=4096`, provider JSON mode
off, no OpenRouter reasoning controls, no prompt rewriting, and no hidden/provider
reasoning inputs to ACE agents. The unified experiment runner no longer exposes
thinking/reasoning flags or a JSON-mode preset.

The retained robustness layer is deliberately narrow: empty visible content and
malformed provider JSON are logged as provider-call failures, counted as failed
calls/samples where the workflow can continue, and are not retried. Timeout,
rate-limit, and server-error retry behavior remains operational transport handling.

## 2026-04-20 - Full FiNER offline-run cost estimates (gpt-oss-120b)

Estimated the cost of running the full FiNER offline adaptation with
gpt-oss-120b by extrapolating from the subset run (60/40/80 train/val/test,
total $1.90 at OpenRouter Nitro pricing).

**Method**: Extracted per-call pricing from the subset telemetry, computed
phase-wise token/cost breakdowns, then extrapolated to the full dataset
(1000/500/441) accounting for playbook growth. The playbook accumulates
~174 tokens per training step until capping at the 80K token budget (~step
450), after which per-step cost plateaus. Full runs use eval_steps=100
(10 validation evaluations). Per-call pricing was reverse-engineered from
cost_usd and token counts as a perfect linear fit, confirming per-model
rates.

**At OpenRouter Nitro pricing ($0.35/M input, $0.75/M output)**:

| Phase | Est. Cost |
|-------|-----------|
| Initial test (441 samples, no playbook) | ~$0.65 |
| Training (1000 steps, growing playbook) | ~$86 |
| Validation (10 evals × 500 samples) | ~$123 |
| Final test (441 samples, full playbook) | ~$13 |
| **Total** | **~$220 ±30% ($150–$290)** |

**At OpenRouter Standard pricing ($0.039/M input, $0.19/M output)**:

The same token volumes scale differently because training and validation
are input-dominated (reading the growing playbook on every call). The
input price drops 9× vs only 2.5× for output, so costs shrink
disproportionately:

| Phase | Est. Cost |
|-------|-----------|
| Initial test | ~$0.12 |
| Training | ~$11 |
| Validation | ~$15 |
| Final test | ~$1.60 |
| **Total** | **~$28 ±30% ($20–$36)** |

**Paper comparison**: The ACE paper (Table 4) reports $2.9 for *online*
FiNER adaptation — a different setup where the model sequentially predicts
and updates context on each of the 441 test samples (no separate training
phase). Our pipeline runs *offline* adaptation: training on 1000 samples
with an iteratively growing playbook, periodic validation, then held-out
test evaluation. Offline is far more expensive due to the iterative
training loop with expanding context. The paper does not report offline
FiNER dollar costs.
