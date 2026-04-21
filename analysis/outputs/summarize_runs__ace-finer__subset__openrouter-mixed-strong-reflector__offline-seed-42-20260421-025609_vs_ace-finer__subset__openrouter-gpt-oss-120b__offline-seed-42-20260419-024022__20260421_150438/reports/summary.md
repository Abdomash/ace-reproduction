# offline_seed-42_20260421_025609
Path: /home/abdo/ace-reproduction/results/ace-finer/subset/openrouter-mixed-strong-reflector/offline_seed-42_20260421_025609
Task: finer | Mode: offline | Provider: openrouter | Eval steps: 15
Models: generator=openai/gpt-oss-120b reflector=minimax/minimax-m2.7 curator=openai/gpt-oss-120b

Test summary:
  split    tag_acc   correct_tags   exact_samples   no_answer
  initial 54.69%    175/320        17/80           0
  final   65.31%    209/320        26/80           0
  delta   tag_acc=+10.62pp correct_tags=+34 exact_samples=+9

Tag-correct distribution per sample:
  initial: {0: 11, 1: 13, 2: 23, 3: 16, 4: 17}
  final:   {0: 4, 1: 14, 2: 17, 3: 19, 4: 26}

Training pre/post:
  tag_acc: 77.08% -> 88.75% (185/240 -> 213/240)
  exact:   33/60 -> 45/60

Validation checkpoints:
  best_accuracy: 78.12%
  step   val_acc   exact    train_pre -> train_post   bullets   tokens
  15     76.88%    20/40    78.33% -> 91.67%    40       3345
  30     75.62%    19/40    80.00% -> 92.50%    78       6840
  45     78.12%    21/40    76.11% -> 91.67%    106      9409
  60     78.12%    20/40    77.08% -> 88.75%    131      11543
  selected best checkpoint: step 45 at 78.12%

Playbooks:
  best  bullets=108  chars=42173  helpful_sum=16   harmful_sum=8    harmful_bullets=8
  final bullets=133  chars=51698  helpful_sum=20   harmful_sum=9    harmful_bullets=9
  best_equals_final: False

LLM usage and cost:
  role       calls  cost        tokens      prompt     response   reasoning   avg_time
  generator  466    $0.558692   4317956     3856453    461503     406480      19.54s
  reflector  64     $0.161156   256492      156804     99688      91870       31.01s
  curator    51     $0.061518   420761      371268     49493      31838       18.68s
  total      581    $0.781365   4995209     4384525    610684     530188      20.73s
  calls_with_provider_cost=578/581

Exact-match movement:
  became_correct: [2, 11, 22, 27, 40, 48, 55, 64, 69, 71, 73, 79]
  became_wrong:   [3, 13, 39]

Artifacts:
  bullet_usage=93 curator_ops=131 curator_failures=None trace_lines=842 metrics_lines=1331

Notes:
  - Best and final playbooks differ; final test usually uses the best validated playbook.

# offline_seed-42_20260419_024022
Path: /home/abdo/ace-reproduction/results/ace-finer/subset/openrouter-gpt-oss-120b/offline_seed-42_20260419_024022
Task: finer | Mode: offline | Provider: openrouter | Eval steps: 15
Models: generator=openai/gpt-oss-120b:nitro reflector=openai/gpt-oss-120b:nitro curator=openai/gpt-oss-120b:nitro

Test summary:
  split    tag_acc   correct_tags   exact_samples   no_answer
  initial 56.88%    182/320        19/80           0
  final   66.88%    214/320        26/80           0
  delta   tag_acc=+10.00pp correct_tags=+32 exact_samples=+7

Tag-correct distribution per sample:
  initial: {0: 10, 1: 16, 2: 15, 3: 20, 4: 19}
  final:   {0: 5, 1: 11, 2: 15, 3: 23, 4: 26}

Training pre/post:
  tag_acc: 72.08% -> 93.75% (173/240 -> 225/240)
  exact:   27/60 -> 49/60

Validation checkpoints:
  best_accuracy: 81.25%
  step   val_acc   exact    train_pre -> train_post   bullets   tokens
  15     73.12%    17/40    76.67% -> 95.00%    35       2741
  30     81.25%    24/40    77.50% -> 94.17%    68       5471
  45     80.62%    22/40    72.22% -> 95.00%    98       8131
  60     76.88%    22/40    72.08% -> 93.75%    122      10205
  selected best checkpoint: step 30 at 81.25%

Playbooks:
  best  bullets=68   chars=24337  helpful_sum=10   harmful_sum=0    harmful_bullets=0
  final bullets=122  chars=45634  helpful_sum=20   harmful_sum=2    harmful_bullets=2
  best_equals_final: False

LLM usage and cost:
  role       calls  cost        tokens      prompt     response   reasoning   avg_time
  generator  481    $1.627186   3950219     3338695    611524     0           1.33s
  reflector  68     $0.101052   229931      178490     51441      0           0.98s
  curator    60     $0.178128   443843      386886     56957      0           1.20s
  total      609    $1.906366   4623993     3904071    719922     0           1.28s
  calls_with_provider_cost=609/609

Exact-match movement:
  became_correct: [11, 22, 25, 27, 40, 42, 46, 51, 71, 73, 74]
  became_wrong:   [7, 13, 29, 58]

Artifacts:
  bullet_usage=87 curator_ops=122 curator_failures=None trace_lines=898 metrics_lines=75

Notes:
  - Best and final playbooks differ; final test usually uses the best validated playbook.

# Comparison
run_id
  initial_tag  final_tag   delta_tag_acc  delta_tags  exact_i  exact_f  best_val
offline_seed-42_20260421_025609
  54.69%       65.31%      +10.62pp       +34         17/80    26/80    78.12%
offline_seed-42_20260419_024022
  56.88%       66.88%      +10.00pp       +32         19/80    26/80    81.25%
