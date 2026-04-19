# ace_appworld_gptoss120b_subset_20260419_221723
Path: /home/abdo/ace-reproduction/results/ace-appworld/subset/openrouter-gpt-oss-120b/ace_appworld_gptoss120b_subset_20260419_221723
Task: ace-appworld | Dataset: dev

Evaluation:
  task_goal_completion=71.9 scenario_goal_completion=47.4
  tasks=41/57 scenarios=9/19 failures=16
  difficulty: {'1': {'passed': 23, 'total': 30}, '2': {'passed': 16, 'total': 24}, '3': {'passed': 2, 'total': 3}}

LLM usage and cost:
  calls=575 cost=$2.295548 prompt_tokens=19505770 response_tokens=282031 total_tokens=19787801 calls_with_cost=575
  role_counts: {'generator': 575}

API and telemetry:
  api_calls=3082
  spans=1802 trace_files=20 metric_files=20
  process.cpu.usage: avg=1977.00 max=18004.10 %
  process.memory.usage_bytes: avg=437838116.57 max=800616448.00 bytes

Artifacts:
  size=422164849 post_export_size=2837663 tasks=57

# ace_appworld_gptoss120b_subset_20260419_231443
Path: /home/abdo/ace-reproduction/results/ace-appworld/subset/openrouter-gpt-oss-120b/ace_appworld_gptoss120b_subset_20260419_231443
Task: ace-appworld | Dataset: dev

Evaluation:
  task_goal_completion=70.2 scenario_goal_completion=47.4
  tasks=40/57 scenarios=9/19 failures=17
  difficulty: {'1': {'passed': 23, 'total': 30}, '2': {'passed': 15, 'total': 24}, '3': {'passed': 2, 'total': 3}}

LLM usage and cost:
  calls=591 cost=$2.581880 prompt_tokens=20031349 response_tokens=235858 total_tokens=20267207 calls_with_cost=591
  role_counts: {'generator': 591}
  wall_time=1148.36s call_time=1148.36s

API and telemetry:
  api_calls=2945
  spans=1850 trace_files=20 metric_files=20
  process.cpu.usage: avg=163.72 max=24704.20 %
  process.memory.usage_bytes: avg=770315448.40 max=854949888.00 bytes

Artifacts:
  size=431167074 post_export_size=3754213 tasks=57

# Comparison
run_id
  task_goal  scenario_goal  calls  cost
ace_appworld_gptoss120b_subset_20260419_221723
  71.9       47.4           575    $2.295548
ace_appworld_gptoss120b_subset_20260419_231443
  70.2       47.4           591    $2.581880
