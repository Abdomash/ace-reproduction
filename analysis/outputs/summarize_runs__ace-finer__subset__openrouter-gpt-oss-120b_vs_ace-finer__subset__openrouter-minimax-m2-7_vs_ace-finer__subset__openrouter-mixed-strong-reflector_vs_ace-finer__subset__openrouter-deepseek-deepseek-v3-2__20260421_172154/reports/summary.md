# offline_seed-42_20260418_143058
Path: /home/abdo/ace-reproduction/results/ace-finer/subset/openrouter-gpt-oss-120b/offline_seed-42_20260418_143058
Task: finer | Mode: offline | Provider: minimax | Eval steps: 100
Models: generator=openai/gpt-oss-120b reflector=openai/gpt-oss-120b curator=openai/gpt-oss-120b

Test summary:
  split    tag_acc   correct_tags   exact_samples   no_answer
  initial 57.19%    183/320        18/80           2
  final   57.50%    184/320        17/80           0
  delta   tag_acc=+0.31pp correct_tags=+1 exact_samples=-1

Tag-correct distribution per sample:
  initial: {0: 11, 1: 12, 2: 18, 3: 21, 4: 18}
  final:   {0: 10, 1: 13, 2: 17, 3: 23, 4: 17}

Training pre/post:
  tag_acc: 72.08% -> 82.50% (173/240 -> 198/240)
  exact:   25/60 -> 34/60

Validation checkpoints:
  best_accuracy: 0.00%
  step   val_acc   exact    train_pre -> train_post   bullets   tokens

Playbooks:
  best  bullets=0    chars=184    helpful_sum=0    harmful_sum=0    harmful_bullets=0
  final bullets=90   chars=32825  helpful_sum=90   harmful_sum=22   harmful_bullets=10
  best_equals_final: False

LLM usage and cost:
  role       calls  cost        tokens      prompt     response   reasoning   avg_time
  generator  326    $0.000000   1806611     1490368    316243     0           25.80s
  reflector  71     $0.000000   295538      199722     95816      0           39.58s
  curator    60     $0.000000   423750      366835     56915      0           21.32s
  total      457    $0.000000   2525899     2056925    468974     0           27.36s
  calls_with_provider_cost=0/457

Exact-match movement:
  became_correct: [41, 50]
  became_wrong:   [21, 30, 74]

Artifacts:
  bullet_usage=85 curator_ops=87 curator_failures=3174 trace_lines=754 metrics_lines=1810

Notes:
  - No validation checkpoints ran; best_playbook likely stayed at the initial playbook.
  - Best playbook has zero learned bullets.
  - Best and final playbooks differ; final test usually uses the best validated playbook.
  - Tag-level accuracy improved, but exact-sample accuracy did not improve.
  - No provider cost metadata was found in LLM logs; cost totals are $0.000000.

# offline_seed-42_20260418_171221
Path: /home/abdo/ace-reproduction/results/ace-finer/subset/openrouter-gpt-oss-120b/offline_seed-42_20260418_171221
Task: finer | Mode: offline | Provider: minimax | Eval steps: 15
Models: generator=openai/gpt-oss-120b:nitro reflector=openai/gpt-oss-120b:nitro curator=openai/gpt-oss-120b:nitro

Test summary:
  split    tag_acc   correct_tags   exact_samples   no_answer
  initial 52.19%    167/320        18/80           0
  final   61.56%    197/320        18/80           0
  delta   tag_acc=+9.38pp correct_tags=+30 exact_samples=+0

Tag-correct distribution per sample:
  initial: {0: 16, 1: 12, 2: 19, 3: 15, 4: 18}
  final:   {0: 5, 1: 13, 2: 20, 3: 24, 4: 18}

Training pre/post:
  tag_acc: 73.33% -> 88.75% (176/240 -> 213/240)
  exact:   28/60 -> 43/60

Validation checkpoints:
  best_accuracy: 83.75%
  step   val_acc   exact    train_pre -> train_post   bullets   tokens
  15     83.75%    24/40    75.00% -> 86.67%    41       3161
  30     80.00%    22/40    80.83% -> 90.00%    73       5598
  45     79.38%    23/40    73.89% -> 90.00%    103      8107
  60     73.75%    17/40    73.33% -> 88.75%    134      10351
  selected best checkpoint: step 15 at 83.75%

Playbooks:
  best  bullets=41   chars=14174  helpful_sum=11   harmful_sum=4    harmful_bullets=2
  final bullets=134  chars=46465  helpful_sum=69   harmful_sum=14   harmful_bullets=6
  best_equals_final: False

LLM usage and cost:
  role       calls  cost        tokens      prompt     response   reasoning   avg_time
  generator  475    $0.000000   3670463     3160935    509528     0           3.36s
  reflector  63     $0.000000   225408      173199     52209      0           1.50s
  curator    60     $0.000000   453559      396119     57440      0           2.56s
  total      598    $0.000000   4349430     3730253    619177     0           3.08s
  calls_with_provider_cost=0/598

Exact-match movement:
  became_correct: [20, 31, 41, 46, 71]
  became_wrong:   [4, 7, 14, 25, 28]

Artifacts:
  bullet_usage=88 curator_ops=134 curator_failures=None trace_lines=876 metrics_lines=176

Notes:
  - Best and final playbooks differ; final test usually uses the best validated playbook.
  - Tag-level accuracy improved, but exact-sample accuracy did not improve.
  - No provider cost metadata was found in LLM logs; cost totals are $0.000000.

# offline_seed-42_20260418_221428
Path: /home/abdo/ace-reproduction/results/ace-finer/subset/openrouter-gpt-oss-120b/offline_seed-42_20260418_221428
Task: finer | Mode: offline | Provider: minimax | Eval steps: 15
Models: generator=openai/gpt-oss-120b:nitro reflector=openai/gpt-oss-120b:nitro curator=openai/gpt-oss-120b:nitro

Test summary:
  split    tag_acc   correct_tags   exact_samples   no_answer
  initial 54.69%    175/320        19/80           1
  final   66.25%    212/320        27/80           0
  delta   tag_acc=+11.56pp correct_tags=+37 exact_samples=+8

Tag-correct distribution per sample:
  initial: {0: 12, 1: 15, 2: 18, 3: 16, 4: 19}
  final:   {0: 6, 1: 10, 2: 17, 3: 20, 4: 27}

Training pre/post:
  tag_acc: 70.00% -> 92.92% (168/240 -> 223/240)
  exact:   25/60 -> 47/60

Validation checkpoints:
  best_accuracy: 80.62%
  step   val_acc   exact    train_pre -> train_post   bullets   tokens
  15     77.50%    21/40    60.00% -> 88.33%    36       3196
  30     79.38%    21/40    68.33% -> 88.33%    70       6214
  45     80.62%    20/40    67.22% -> 91.67%    99       8872
  60     75.62%    19/40    70.00% -> 92.92%    127      11354
  selected best checkpoint: step 45 at 80.62%

Playbooks:
  best  bullets=99   chars=39978  helpful_sum=11   harmful_sum=3    harmful_bullets=2
  final bullets=127  chars=51314  helpful_sum=11   harmful_sum=3    harmful_bullets=2
  best_equals_final: False

LLM usage and cost:
  role       calls  cost        tokens      prompt     response   reasoning   avg_time
  generator  480    $0.000000   4343732     3811196    532536     311225      3.39s
  reflector  65     $0.000000   213326      169897     43429      11582       2.17s
  curator    60     $0.000000   479217      424640     54577      22728       2.99s
  total      605    $0.000000   5036275     4405733    630542     345535      3.22s
  calls_with_provider_cost=0/605

Exact-match movement:
  became_correct: [11, 20, 22, 40, 46, 48, 55, 64, 69, 71, 73]
  became_wrong:   [2, 12, 18]

Artifacts:
  bullet_usage=85 curator_ops=127 curator_failures=None trace_lines=890 metrics_lines=179

Notes:
  - Best and final playbooks differ; final test usually uses the best validated playbook.
  - No provider cost metadata was found in LLM logs; cost totals are $0.000000.

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

# offline_seed-42_20260418_230446
Path: /home/abdo/ace-reproduction/results/ace-finer/subset/openrouter-minimax-m2-7/offline_seed-42_20260418_230446
Task: finer | Mode: offline | Provider: minimax | Eval steps: 15
Models: generator=minimax/minimax-m2.7 reflector=minimax/minimax-m2.7 curator=minimax/minimax-m2.7

Test summary:
  split    tag_acc   correct_tags   exact_samples   no_answer
  initial 51.88%    166/320        23/80           28
  final   68.44%    219/320        34/80           3
  delta   tag_acc=+16.56pp correct_tags=+53 exact_samples=+11

Tag-correct distribution per sample:
  initial: {0: 28, 1: 3, 2: 7, 3: 19, 4: 23}
  final:   {0: 6, 1: 13, 2: 11, 3: 16, 4: 34}

Training pre/post:
  tag_acc: 73.75% -> 90.42% (177/240 -> 217/240)
  exact:   32/60 -> 48/60

Validation checkpoints:
  best_accuracy: 81.88%
  step   val_acc   exact    train_pre -> train_post   bullets   tokens
  15     80.62%    23/40    70.00% -> 90.00%    31       3626
  30     68.12%    14/40    73.33% -> 91.67%    55       7426
  45     81.88%    25/40    75.56% -> 92.78%    80       11406
  60     75.62%    19/40    73.75% -> 90.42%    99       14739
  selected best checkpoint: step 45 at 81.88%

Playbooks:
  best  bullets=80   chars=55701  helpful_sum=22   harmful_sum=8    harmful_bullets=8
  final bullets=99   chars=72375  helpful_sum=31   harmful_sum=13   harmful_bullets=13
  best_equals_final: False

LLM usage and cost:
  role       calls  cost        tokens      prompt     response   reasoning   avg_time
  generator  465    $0.000000   5112010     4363561    748449     685245      23.35s
  reflector  62     $0.000000   264583      169785     94798      83545       30.06s
  curator    53     $0.000000   512373      447710     64663      46530       25.42s
  total      580    $0.000000   5888966     4981056    907910     815320      24.25s
  calls_with_provider_cost=0/580

Exact-match movement:
  became_correct: [2, 10, 20, 22, 25, 30, 38, 40, 49, 58, 63, 64, 65, 67, 72, 73, 78, 79]
  became_wrong:   [3, 12, 14, 23, 33, 60, 74]

Artifacts:
  bullet_usage=92 curator_ops=99 curator_failures=20 trace_lines=840 metrics_lines=1537

Notes:
  - Best and final playbooks differ; final test usually uses the best validated playbook.
  - No provider cost metadata was found in LLM logs; cost totals are $0.000000.

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

# Comparison
run_id
  initial_tag  final_tag   delta_tag_acc  delta_tags  exact_i  exact_f  best_val
offline_seed-42_20260418_143058
  57.19%       57.50%      +0.31pp        +1          18/80    17/80    0.00%
offline_seed-42_20260418_171221
  52.19%       61.56%      +9.38pp        +30         18/80    18/80    83.75%
offline_seed-42_20260418_221428
  54.69%       66.25%      +11.56pp       +37         19/80    27/80    80.62%
offline_seed-42_20260419_024022
  56.88%       66.88%      +10.00pp       +32         19/80    26/80    81.25%
offline_seed-42_20260418_230446
  51.88%       68.44%      +16.56pp       +53         23/80    34/80    81.88%
offline_seed-42_20260421_025609
  54.69%       65.31%      +10.62pp       +34         17/80    26/80    78.12%
offline_seed-42_20260421_150728
  71.25%       76.88%      +5.63pp        +18         29/80    36/80    82.50%
