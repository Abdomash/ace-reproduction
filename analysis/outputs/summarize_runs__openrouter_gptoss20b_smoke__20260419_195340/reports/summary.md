# ace_finer_offline_ace_all_gptoss20b_subset_smoke_42_20260418_175143
Path: /home/abdo/ace-reproduction/results/openrouter_gptoss20b_smoke/ace_finer_offline_ace_all_gptoss20b_subset_smoke_42_20260418_175143
Task: finer | Mode: offline | Provider: minimax | Eval steps: 15
Models: generator=openai/gpt-oss-20b:nitro reflector=openai/gpt-oss-20b:nitro curator=openai/gpt-oss-20b:nitro

Test summary:
  split    tag_acc   correct_tags   exact_samples   no_answer
  initial 40.94%    131/320        14/80           23
  final   41.88%    134/320        16/80           27
  delta   tag_acc=+0.94pp correct_tags=+3 exact_samples=+2

Tag-correct distribution per sample:
  initial: {0: 33, 1: 6, 2: 12, 3: 15, 4: 14}
  final:   {0: 29, 1: 10, 2: 15, 3: 10, 4: 16}

Training pre/post:
  tag_acc: 58.75% -> 72.92% (141/240 -> 175/240)
  exact:   20/60 -> 35/60

Validation checkpoints:
  best_accuracy: 58.75%
  step   val_acc   exact    train_pre -> train_post   bullets   tokens
  15     37.50%    7/40     60.00% -> 73.33%    37       2420
  30     40.00%    11/40    56.67% -> 70.83%    67       4892
  45     56.25%    15/40    55.56% -> 75.56%    94       7014
  60     58.75%    15/40    58.75% -> 72.92%    123      8979
  selected best checkpoint: step 60 at 58.75%

Playbooks:
  best  bullets=123  chars=40337  helpful_sum=94   harmful_sum=34   harmful_bullets=12
  final bullets=123  chars=40337  helpful_sum=94   harmful_sum=34   harmful_bullets=12
  best_equals_final: True

LLM usage and cost:
  role       calls  cost        tokens      prompt     response   reasoning   avg_time
  generator  494    $0.000000   3266119     2587420    678699     0           8.16s
  reflector  74     $0.000000   304255      205648     98607      0           3.12s
  curator    60     $0.000000   419990      337449     82541      0           4.54s
  total      628    $0.000000   3990364     3130517    859847     0           7.22s
  calls_with_provider_cost=0/628

Exact-match movement:
  became_correct: [2, 7, 11, 16, 21, 27, 30, 34, 38]
  became_wrong:   [5, 28, 33, 42, 69, 70, 74]

Artifacts:
  bullet_usage=80 curator_ops=123 curator_failures=60 trace_lines=936 metrics_lines=341

Notes:
  - No provider cost metadata was found in LLM logs; cost totals are $0.000000.

# ace_finer_offline_ace_all_gptoss20b_subset_smoke_42_20260418_223218
Path: /home/abdo/ace-reproduction/results/openrouter_gptoss20b_smoke/ace_finer_offline_ace_all_gptoss20b_subset_smoke_42_20260418_223218
Task: finer | Mode: offline | Provider: minimax | Eval steps: 15
Models: generator=openai/gpt-oss-20b:nitro reflector=openai/gpt-oss-20b:nitro curator=openai/gpt-oss-20b:nitro

Test summary:
  split    tag_acc   correct_tags   exact_samples   no_answer
  initial 38.12%    122/320        11/80           23
  final   40.00%    128/320        16/80           30
  delta   tag_acc=+1.88pp correct_tags=+6 exact_samples=+5

Tag-correct distribution per sample:
  initial: {0: 30, 1: 9, 2: 21, 3: 9, 4: 11}
  final:   {0: 37, 1: 2, 2: 13, 3: 12, 4: 16}

Training pre/post:
  tag_acc: 52.92% -> 70.00% (127/240 -> 168/240)
  exact:   18/60 -> 34/60

Validation checkpoints:
  best_accuracy: 48.12%
  step   val_acc   exact    train_pre -> train_post   bullets   tokens
  15     39.38%    9/40     56.67% -> 86.67%    43       2859
  30     43.12%    10/40    53.33% -> 74.17%    77       5390
  45     48.12%    9/40     53.89% -> 73.33%    109      7734
  60     35.62%    9/40     52.92% -> 70.00%    147      10367
  selected best checkpoint: step 45 at 48.12%

Playbooks:
  best  bullets=109  chars=35302  helpful_sum=3    harmful_sum=3    harmful_bullets=2
  final bullets=147  chars=47044  helpful_sum=8    harmful_sum=3    harmful_bullets=2
  best_equals_final: False

LLM usage and cost:
  role       calls  cost        tokens      prompt     response   reasoning   avg_time
  generator  499    $0.000000   4874333     3604494    1269839    1279818     6.15s
  reflector  77     $0.000000   277793      193920     83873      58342       3.06s
  curator    60     $0.000000   487782      381602     106180     93291       4.81s
  total      636    $0.000000   5639908     4180016    1459892    1431451     5.65s
  calls_with_provider_cost=0/636

Exact-match movement:
  became_correct: [2, 33, 38, 41, 56, 71, 77, 78, 79]
  became_wrong:   [4, 34, 39, 70]

Artifacts:
  bullet_usage=78 curator_ops=147 curator_failures=100 trace_lines=952 metrics_lines=376

Notes:
  - Best and final playbooks differ; final test usually uses the best validated playbook.
  - No provider cost metadata was found in LLM logs; cost totals are $0.000000.

# Comparison
run_id
  initial_tag  final_tag   delta_tag_acc  delta_tags  exact_i  exact_f  best_val
ace_finer_offline_ace_all_gptoss20b_subset_smoke_42_20260418_175143
  40.94%       41.88%      +0.94pp        +3          14/80    16/80    58.75%
ace_finer_offline_ace_all_gptoss20b_subset_smoke_42_20260418_223218
  38.12%       40.00%      +1.88pp        +6          11/80    16/80    48.12%
