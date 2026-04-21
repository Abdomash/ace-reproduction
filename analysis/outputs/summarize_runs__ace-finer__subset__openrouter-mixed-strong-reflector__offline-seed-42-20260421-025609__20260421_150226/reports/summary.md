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
