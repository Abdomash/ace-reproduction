# offline_seed-42_20260421_150728
Path: /home/abdo/ace-reproduction/results/ace-finer/subset/openrouter-deepseek-deepseek-v3-2/offline_seed-42_20260421_150728
Task: finer | Mode: offline | Provider: openrouter | Eval steps: 15
Models: generator=deepseek/deepseek-v3.2 reflector=deepseek/deepseek-v3.2 curator=deepseek/deepseek-v3.2

Test summary:
  split    tag_acc   correct_tags   exact_samples   no_answer
  initial 71.25%    228/320        29/80           0
  final   76.88%    246/320        36/80           0
  delta   tag_acc=+5.63pp correct_tags=+18 exact_samples=+7

Tag-correct distribution per sample:
  initial: {0: 3, 1: 7, 2: 18, 3: 23, 4: 29}
  final:   {0: 1, 1: 6, 2: 15, 3: 22, 4: 36}

Training pre/post:
  tag_acc: 85.83% -> 95.83% (206/240 -> 230/240)
  exact:   41/60 -> 50/60

Validation checkpoints:
  best_accuracy: 82.50%
  step   val_acc   exact    train_pre -> train_post   bullets   tokens
  15     78.12%    21/40    90.00% -> 96.67%    20       1816
  30     82.50%    26/40    88.33% -> 97.50%    40       3931
  45     82.50%    24/40    87.78% -> 96.11%    54       5518
  60     78.12%    22/40    85.83% -> 95.83%    69       7081
  selected best checkpoint: step 30 at 82.50%

Playbooks:
  best  bullets=40   chars=18788  helpful_sum=63   harmful_sum=3    harmful_bullets=3
  final bullets=69   chars=34346  helpful_sum=153  harmful_sum=13   harmful_bullets=8
  best_equals_final: False

LLM usage and cost:
  role       calls  cost        tokens      prompt     response   reasoning   avg_time
  generator  462    $0.621175   2927575     2619668    307907     0           25.02s
  reflector  63     $0.069790   257802      210412     47390      0           29.07s
  curator    60     $0.125670   345034      312292     32742      0           26.68s
  total      585    $0.816635   3530411     3142372    388039     0           25.63s
  calls_with_provider_cost=585/585

Exact-match movement:
  became_correct: [16, 22, 27, 30, 33, 54, 57, 62, 64, 71]
  became_wrong:   [48, 72, 74]

Artifacts:
  bullet_usage=101 curator_ops=69 curator_failures=77 trace_lines=850 metrics_lines=1470

Notes:
  - Best and final playbooks differ; final test usually uses the best validated playbook.
