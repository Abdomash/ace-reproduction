# Slurm Environment

To maximize resource utilization, most testbed nodes have been pooled into a Slurm cluster. With this setup we aim to have an environment similar to the Slurm setup on IBEX. However, since we have a smaller pool of users, we can afford to have a more custom configuration and be more relaxed in resource usage constraints.

## IBEX portability

For most workloads, you can easily move them from our cluster directly to IBEX and vise-versa. You can also bring to our cluster most sbatch scripts you learn to use from IBEX learning resources (see below). However, note that IBEX’s modules are not supported on our setup.

Another important consideration to note is that our cluster **does not share the same storage as IBEX**. We have separate filesystems.

## Learning to use Slurm

In case you’re unfamiliar with Slurm, we recommend that you watch the [IBEX 101 training session](https://youtu.be/VaglExEnVH4). You can find the introduction to IBEX as well as other useful Slurm tutorials on the [learning resources page from IBEX](https://www.hpc.kaust.edu.sa/ibex/training).

## Interacting with Slurm

To use our Slurm setup, you need to be connected to the testbed. Make sure you have [access to the testbed](/internal/rocs-testbed/access-to-testbed) before proceeding.

### Login to the head node

Interaction with the Slurm cluster is done through the head node, `mcmgt01`.
Jobs can only be deployed from this node.

SSH into the head node before running any of the commands below.

```bash
ssh mcmgt01
```

# Deploying jobs

There are two types of job you can launch on Slurm: batch jobs and interactive jobs.
To simplify, consider launching a job as launching an experiment (but keep in mind jobs are more powerful than that!).

## Batch jobs

Batch jobs are the most common type of job in Slurm.
They specify a script to execute and the resources required to run it. They are called batch jobs because we submit them to a queue and run without user interaction, remaining in the queue until the requested resources are available.

Batch jobs are configured using sbatch scripts and issued to slurm with the `sbatch` command.
An sbatch script is just a bash script with sbatch directives that define the job’s resource requirements and configuration.

Here is an example sbatch script you can use when running experiments.
For a full list of available configuration options, refer to the official [sbatch documentation](https://slurm.schedmd.com/sbatch.html).

### Sbatch template - General

```bash
#!/bin/bash --login
#
#SBATCH --job-name=ml_job
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#
#SBATCH --time=10:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=50GB
#SBATCH --gres=gpu:a100:1
#SBATCH --constraint=gpu_a100_80gb

set -e # stop bash script on first error

mamba activate <your_env>

# Optionally add "$@" to pass additional arguments to the script
python experiment.py --option_1 value_1 -flag "$@"
```

A few notes on the above script:

* Notice the `--login` flag passed to bash. You need it in order to use your conda/mamba environment.
* Slurm allows filename patterns to contain [replacement symbols](https://slurm.schedmd.com/sbatch.html#SECTION_%3CB%3Efilename-pattern%3C/B%3E) like %x (job name) and %j (job ID).
* If you don’t want to split output and err, delete the `--error` flag.
* We’re specifying a time limit of 10 hours. Always try to specify a time limit for your jobs.
* Because we didn’t specify, Slurm assumes you are requesting a single node.
* `--gres=gpu:a100:1` requests a node with a free A100 GPU.
  * Other GPU options are p100 and v100.
* `--constraint` selects nodes with specific features. In this case, we’re requesting a node that has an A100 with 80GB (we also have A100s with 40GB). To get a full list of available features per node, run the [ninfo](#ninfo) command.
* The script executes in the working directory where you call the sbatch command.
* You can optionally pass extra arguments to the script as if you were running a bash script directly.

```bash
sbatch sbatch_template.sh --extra_option extra_value ...
# The "$@" bash variable in the sbatch_template.sh will be replaced
# with the extra parameters passed
```

The job is issued to the Slurm queue using:

```text
sbatch sbatch_script.sh
```

## Interactive jobs

Interactive jobs allow you to interact directly with the resources you allocate. This is particularly useful for developing or debugging your code.
There are multiple ways you can achieve this interactive setup.

### Bash shell

The simplest way to interact with a node is to use srun to launch a job and request an interactive bash shell.

```bash
srun --gres=gpu:p100:1 --time=4:00:00 --pty bash -l
# Example output
user@mcnode01:~$
```

To ensure users can debug reliably on the testbed, interactive workloads are prioritized during the day (i.e., from 8AM to 8PM) on a set of resources.

**Note**: Interactive sessions are meant for debugging and are limited in maximum duration, available resources and number of jobs.
Please refer to the [limits section](#resource-and-runtime-limits) to understand currently applicable limits.

### Tips

A debug shell can quickly be obtained using the commands below.

* `sgpu` - shell with any gpu - prioritizes weakest gpu available
* `sp100` | `sv100` | `sa100` - shell with 1x P100 | V100 | A100 GPU respectively
* The resources can be customized by appending regular slurm flags:

```ruby
$ sv100 --mem=50GB -c 10
```

The interactive shell will exist until you close the connection started by srun. To prevent the connection from terminating, you might find it useful to launch the above command in a tmux session. The tmux session will keep the command running across accidental terminal window closings or SSH timeouts to mcmgt01 due to innactivity.

### Remote development tips

In our environment you can only connect to the Slurm login node (mcmgt01) via SSH. Direct SSH connections to compute nodes are not supported. As a result, connecting our IDE directly to compute nodes (which usually rely on SSH) is not possible.

**Recommended Workflow**

1. **Write your code on the login node**
   The login node, mcmgt01, shares the network file systems with the compute nodes.
   You can use VSCode’s [Remote-SSH](https://code.visualstudio.com/docs/remote/ssh) extension to connect to mcmgt01 and develop code there.
2. **Request a compute node with an interactive shell**
   Allocate a GPU/CPU compute node using an interactive job.

   ```bash
   user@mcmgt01:~$ sv100
   # Example output
   user@mcnode33:~$
   ```
3. **Run your code on the compute node**

   ```bash
   user@mcnode33:~$ mamba activate env
   user@mcnode33:~$ make
   user@mcnode33:~$ ./my_app
   ```

**Note**: VSCode’s debugger won’t work on this setup since the code is executed on another node, the compute node. Instead, consider using a terminal-based debugger like gdb (C/C++) or pgdb (Python), or rely on print statements for debugging.

### Sbatch template - Jupyter Lab

Another common interactive setup is to launch a Jupyter Lab server.

```bash
#!/bin/bash --login
#SBATCH --job-name=jupyter
#SBATCH --output=%x-%j.out
#
#SBATCH --time=10:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:v100:1
#SBATCH --mem=50G

set -e # stop bash script on first error

# You can install jupyter in a mamba env with 'mamba install jupyter'
mamba activate <env_with_jupyter_installed>

# Ask the OS for a free port on the machine
JUPYTER_LAB_PORT=$(python -c 'import socket; s=socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()')
jupyter lab --ip=0.0.0.0 --port=$JUPYTER_LAB_PORT --no-browser
```

Once your job has been deployed, you will be able to access the Jupyter Lab session through your local browser.
You can find the URL for the Jupyter Lab at the bottom of the output log.
It will look something like this:

```coffeescript
To access the server, open this file in a browser:
  ...
  Or copy and paste one of these URLs:
    http://mcnode01:50365/lab?token=d80b8c90aff74407e96b57c7c2d516a0177e08ba5832a7a0
```

# Efficient slurm usage

The goal of this Slurm setup is maximize resource utilization, hence minimizing time where our resources are idle.
Here are some guidelines we ask our users to follow in order to help us achieve it.

## Guidelines

* Whenever possible, specify a time limit on your jobs
* Avoid having more than one interactive job at the same time
* If your job needs a GPU, aim to select the weakest GPU that serves your usecase P100 > V100 > A100.
* Don’t ask for exclusive access to nodes if you don’t need to

## Resource and runtime limits

* Interactive sessions (launched with `srun`) are limited to 4 hours
* Max job length: 14 days
* Available resources depend on the job’s Quality of Service (QoS)
  * `normal` (default QoS)
    * GPU restrictions: A100=2, P100=8, V100=8
  * `spot` (low priority QoS)
    * No resource restrictions
    * Jobs may be preempted by jobs in the normal QoS
    * Intended for [preemptible jobs](#preemptible-jobs)
* Upcoming policy (not yet enforced):
  * Long-running jobs (>3 days) will need to be preemptible

If you need more resources for a single non-preemptible job, please [contact us](/internal/rocs-testbed/contacts) and consider requesting a [reservation](#reservations) for this workload.

## Job monitoring

To ensure the resources requested by a job are efficiently being used, the testbed comes with a job monitoring system.
The resource utilization of a specific job can be visualized through a Grafana dashboard. You can obtain a link to the dashboard by running the `jobstats` command in a slurm node (e.g. mcmgt01).

```text
$ jobstats <jobid> -g
```

The credentials to access the dashboard (Username / Password) are: `rocs/rocs`.

![Jobstats dashboard](img/jobstats_dashboard.png)

The dashboard displays various metrics for the job’s allocated resources, including the CPU, memory and GPU utilization. It also shows the current workload on the nodes where the job is running.

Often it’s hard to predict the resources requirements for a job. By monitoring resources, we can adjust the resources requested to make our job more efficient. Adjustments can add more resources if we identify a bottleneck, e.g. we need more CPU cores, or decrease resources if we notice we overestimated the resource, e.g. too much memory.

**Note**: Job monitored data is only kept for 15 days.

**Note**: The dashboard URL generated from the command above specifies the correct timeframe for the job. If you change the job ID in the top-left corner of the dashboard, the timeframe won’t update automatically. You can manually update the timeframe in the top-right of the dashboard if you know the desired range, or preferably, generate a new URL for the job you want to monitor by running the `jobstats` command in the terminal again.

**Note**: [jobstats](https://github.com/PrincetonUniversity/jobstats) is a tool developed at the Princeton University.

## Job summaries

Sometimes we just want a quick overview of our job’s resource utilization. You can obtain a summary of resource utilization by running `jobstats` command on a Slurm node.

```text
$ jobstats <jobid>
```

![Jobstat summary](img/jobstats_summary.png)

The summary reports includes a “Notes” section providing helpful tips.

These summary reports can be emailed when a batch job is completed by adding the following flags to an sbatch script.

```objectivec
#SBATCH --mail-type=END
#SBATCH --mail-user=<your_email>
```

**Note**: Unlike the raw monitored data, the job summary data is never deleted.

## Automatic Job Termination

Guidelines are not enough to enforce good resource utilization. For this reason, we implemented mechanisms to terminate jobs if their resources are not used efficiently.
These automatic terminations will mainly affect two types of allocations: interactive allocations when the user is not working; and incorrectly configured jobs (e.g. requesting more GPUs than the job is using).

The automatic termination process operates as follows:
If a job is identified as having poor resource utilization, an automatic email warning is sent to inform the user of the potential for job cancellation. If the issue persists, the job is canceled, and another email will be sent to notify the user.

### Termination Policies

* Poor GPU utilization: GPU jobs where any GPU has less than 15% GPU utilization over the last hour will receive a termination warning. The job will be canceled if the low utilization remains for two consecutive hours.

**Note**: Job termination policies are enforced using a forked version of [job_defense_shield](https://github.com/jdh4/job_defense_shield).

## Reservations

Users naturally prefer to use the most powerful resources available (e.g A100) even if their experiments do not need them (e.g. a P100 is sufficient). This can block others from running experiments that truly require the hardware, like when training LLMs that need GPUs with more than 40GB of memory.

To improve fairness and reduce scheduling uncertainty in our shared GPU cluster, we support resource reservations in our Slurm environment. Namely, we allow time-based resource reservation for users or groups — for example, a daily reservation for an A100 80GB from 8am to 5pm.

To request a reservation, please submit a reservation request using our [GitHub issue tracker](https://github.com/sands-lab/rocs-testbed/issues). To avoid disrupting ongoing experiments, reservations may take up to one week to be granted. Please plan ahead!

**Note**: If you don’t have access to this GitHub repo, please [reach out](/internal/rocs-testbed/contacts) to us.

In the spirit of transparency and openness, all reservation requests and decisions are publicly visible to all users.

You can request a reservation by creating a new issue, and selecting the “GPU Reservation Request” item. Then, fill all details in the form, following the template below.

**Note**: Reservation utilization is monitored, and underused or misused reservations will be revoked.

To run jobs within a reservation:

```bash
srun <other_options> --reservation=<reservation_name>
```

**Default restrictions on jobs requesting reservations**:

* Jobs can only run during the reservation time.
* Jobs can only use the resources allocated to the reservation.

## Preemptible jobs

All the testbed resources are available for use when they are idle.
Reservations guarantee resources for associated users, but if the reserved resources are unused, they remain accessible to other jobs. Similarly, users may request more resources than the current [resource limits](#resource-and-runtime-limits), as long as they accept that their jobs can be **preempted** either by a reservation holder or by a non-preemptible job.

Jobs are not preemptible by default. To use idle resources, a job must explicitly allow preemption by combining Slurm’s [signal](https://slurm.schedmd.com/sbatch.html#OPT_signal) flag with the `spot` QoS. The signal flag is required to use idle reservation resources and allows Slurm to notify your job with a signal before preempting it, giving it time to clean up. The `spot` qos allows you to run on non-reserved idle resources beyond the per-user [resource limits](#resource-and-runtime-limits).

```bash
sa100 --signal=R:ALRM@60 --qos=spot
```

* R - Allows the job to run on reserved resources
* ALRM - Signal Slurm should send to warn about preemption
  * **Important**: Only sent to tasks launched with `srun`!
  * Can alternatively be sent to sbatch script
* 60 - Grace period in seconds until Slurm forcefully terminates the job

To quickly request a preemptible interactive job, suffix the command helpers with a `p` (for preemptible):

* `sgpup` | `sp100p` | `sv100p` | `sa100p` - request any GPU | P100 | V100 | A100
* Jobs launched with these commands will receive a warning before preemption

**Note**: In the future, long running jobs (e.g. going for more than a few days) might need to be preemptible. This is required to ensure resources are fairly distributed and that long running jobs are not hogging all the resources for too long.

### Tips for enabling preemption on your sbatch job

Basic example of python script capable of handling preemption:

```bash
#!/bin/bash
#SBATCH --signal=R:USR1@60 # Enable preemption on reservation and warn job of preemption
#SBATCH --qos=spot         # Enable preemption on non-reserved resources

# Important: By default only tasks launched with *srun* receive the preemption signal
srun python3 ml.py
```

```python
# ml.py
import signal, time, os

should_checkpoint = False
def handle_usr1(signum, frame):
    global should_checkpoint
    print(f"Caught SIGUSR1 at {time.ctime()}")
    should_checkpoint = True
signal.signal(signal.SIGUSR1, handle_usr1)

job_id = os.environ.get("SLURM_JOB_ID")
CKPT_PATH = f"{job_id}_state.ckpt"

print(f"Running job with job ID {job_id}")
start_epoch = 0
if os.path.isfile(CKPT_PATH):
    start_epoch = int(open(CKPT_PATH).read())
    print(f"Checkpoint found. Continuing computation from {start_epoch}")

for epoch in range(start_epoch, 100):
    time.sleep(3) # simulate computation
    # wait for safe point to checkpoint
    if should_checkpoint:
        print(f"Checkpointing at {time.ctime()} - epoch {epoch}")
        open(CKPT_PATH, "w").write(f"{epoch}")
        print("Checkpoint saved. Exiting.")
        exit(0)
```

By default, preempted sbatch jobs will be requeued automatically. This can be disabled with `--no-requeue`. Jobs retain their job ID when requeued.

Manually adding checkpointing mechanisms to your code can be challenging. If you’d like a hand, don’t hesitate to [reach out](/internal/rocs-testbed/contacts) - we’re happy to help!

If you’re running ML workloads, your framework should have checkpoint mechanisms:

* **PyTorch Lightning** makes it very easy - with just two arguments you can [checkpoint](https://lightning.ai/docs/pytorch/stable/common/checkpointing.html) the entire “trainer” state (e.g. epoch and learning rate). Highly recommendended.
* **Native Pytorch** also supports checkpointing but it requires some manual setup: [checkpointing](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html), [distributed checkpointing](https://docs.pytorch.org/tutorials/recipes/distributed_checkpoint_recipe.html).

## Performance considerations

Although we aim to keep testbed resources uniform, some heterogeneity exists. For benchmarking or performance-sensitive workloads, take the following differences into account:

### A100 GPU types

The slurm pool contains both PCI and SXM A100s. Key differences:

* PCI A100s have ~10% lower single-card performance
* PCI A100s have significantly slower GPU interconnects:
  * 1:1 GPU communication is ~3x slower
  * 1-to-all GPU communication is ~10x slower

**Selecting A100 GPU type**:
Slurm might assign PCI A100s to your jobs based on availability. To maximize performance or GPU communication speed, you can select the GPU type using constraints:

```bash
#SBATCH --gres=gpu:a100:1
#SBATCH --constraint=gpu_pci # PCI A100
#SBATCH --constraint=gpu_sxm # SXM A100
```

# Useful utilities

## ginfo

Inspired by IBEX, we decided to port their `ginfo` command to our Slurm cluster. It displays the number of GPUs in used and those that are idle and available for new jobs.

```bash
$ ginfo
GPU Model        Used    Idle   Drain    Down   Maint   Total
a100                9       7       0       0       0      16
p100                0       3       0       0       0       3
v100                1      11       4       8       0      24
       Totals:     10      21       4       8       0      43
```

## ninfo

Provides a detailed information about nodes in the cluster including CPU, Memory, available GPUs and specific features like CPU model.

```bash
$ ninfo
NODELIST    CPUS   MEMORY    AVAIL_FEATURES                                 GRES
mcnode01    40     128785    cpu_intel_xeon_e5_2630,gpu,gpu_p100            gpu:p100:1
mcnode02    40     128785    cpu_intel_xeon_e5_2630,gpu,gpu_p100            gpu:p100:1
mcnode22    128    515614    cpu_amd_epyc_7763,gpu,gpu_a100,gpu_a100_80gb   gpu:a100:4
mcnode25    128    515614    cpu_amd_epyc_7763,gpu,gpu_a100,gpu_a100_40gb   gpu:a100:4
mcnode32    16     515644    cpu_intel_xeon_silver_4112,gpu,gpu_v100        gpu:v100:2
mcnode33    16     499516    cpu_intel_xeon_silver_4112,gpu,gpu_v100        gpu:v100:3
```

## srecent

Shows a quick overview of user launched jobs that started up to 7 days from now.

```bash
$ srecent
JobID        JobName         Start                  End                    Elapsed      AllocTRES                                                    NodeList             State ExitCode
1416         ds_exp          2024-12-31T12:07:38    2024-12-31T12:07:40    00:00:02     billing=8,cpu=8,gres/gpu:v100=2,gres/gpu=2,mem=80G,node=2    mcnode[31-32]       FAILED      1:0
1417         ds_exp          2024-12-31T12:08:12    2024-12-31T12:08:14    00:00:02     billing=8,cpu=8,gres/gpu:v100=2,gres/gpu=2,mem=80G,node=2    mcnode[31-32]       FAILED      1:0
1418         ds_exp          2024-12-31T12:08:49    2024-12-31T12:09:03    00:00:14     billing=8,cpu=8,gres/gpu:v100=2,gres/gpu=2,mem=80G,node=2    mcnode[31-32]       FAILED      1:0
1419         ds_exp          2024-12-31T12:09:39    2024-12-31T12:19:43    00:10:04     billing=8,cpu=8,gres/gpu:a100=2,gres/gpu=2,mem=80G,node=2    mcnode[23,25]      TIMEOUT      0:0
```

## Slurm commands

* Only show my jobs

  ```bash
  squeue --me
  ```
* Cancel all of my jobs

  ```bash
  scancel --me
  ```
* Retrieve recent job information from my jobs started today (alias of srecent)

  ```bash
  sacct -X -o "JobID,Start%-22,End,Elapsed%-12,JobName%-15,AllocTRES%-60,NodeList%-15,State,ExitCode"
  ```
  By default, sacct only shows jobs from the current day. Adding the
  `--starttime=now-2day` option will include jobs that started up to two days ago.
  `sacct` is very flexible, check out its [documentation](https://slurm.schedmd.com/sacct.htmlhttps://slurm.schedmd.com/sacct.html#OPT_format) for more options.
* Get all job details

  ```bash
  sacct -j <job_id> --json | less
  ```
* Show available partitions and current state of nodes

  ```bash
  sinfo
  ```

# Multinode jobs

## DeepSpeed template

On Slurm, it’s easier to launch a deepspeed job using the torchrun launcher instead of the deepspeed launcher. The launcher’s job is only to start the needed processes across the different machines. It does not change the behavior of the deepspeed library inside the code so we can safely use another launcher.

Adjust the template below for your use case, namely, remember to:

* Use your mamba environment
* Change the CMD variable to your own command
* Adjust the requested resources for your use case

```bash
#!/bin/bash -l
#SBATCH --job-name=ds_exp
#SBATCH --time 00:10:00           # maximum execution time (HH:MM:SS)
#SBATCH --output=%x-%j.out        # output file name
#SBATCH --ntasks-per-node=1       # crucial - only 1 task per node! Per gpu tasks are spawned by launcher
#SBATCH --cpus-per-gpu=4
#SBATCH --mem-per-gpu=40GB
#SBATCH --nodes=2
#SBATCH --gpus-per-node=a100:1

set -e
mamba activate deepspeed-env

# The launcher will prepend the python executable to the training script
CMD=" \
    train.py \
    --deepspeed \
    --deepspeed_config ds_config.json \
    "

# Print debug communication info
export NCCL_DEBUG="INFO"
# Specify network interface for inter-node communication
# fabric is our 100Gbps network - All nodes in the slurm pool support it
export NCCL_SOCKET_IFNAME=fabric
# Consider disabling IB/RoCE transport if you're not using the fabric network
# export NCCL_IB_DISABLE=1

# === SHOULD NOT NEED TO MODIFY ANYTHING BELOW THIS POINT ===

# srun error handling:
# --wait=60: wait 60 sec after the first task terminates before terminating all remaining tasks
# --kill-on-bad-exit=1: terminate a step if any task exits with a non-zero exit code
SRUN_ARGS=" \
    --wait=60 \
    --kill-on-bad-exit=1 \
   "

# Meeting point for processes to know who to talk to - Not used for inter-node communication
MASTER_ADDR=$(scontrol show hostnames $SLURM_JOB_NODELIST | head -n 1)
MASTER_PORT=$(( ${SLURM_JOB_ID} % 16384 + 49152))

# torchrun args
# --tee 3: redirect stdout + stderr from all workers to stdout of process 0
LAUNCHER="torchrun \
    --nproc_per_node gpu \
    --nnodes $SLURM_NNODES \
    --rdzv_endpoint $MASTER_ADDR:$MASTER_PORT \
    --rdzv_backend c10d \
    --tee 3 \
    "

set -x
srun $SRUN_ARGS $LAUNCHER $CMD
```

**Tip**: The template above asks for the same GPU configuration on all nodes, which might be hard to have available on the cluster as you increase the number of GPUs. Instead, if your job can have a different number of GPUs per node, consider requesting only the total number GPUs needed and letting slurm allocate them across the available nodes. Here’s how you can do that:

```bash
# 2 nodes with 4 A100 GPU per node
#SBATCH --nodes=2
#SBATCH --gpus-per-node=a100:4
# Or simply request 8 A100s - might result in nodes having different number of GPUs
#SBATCH --gpus=a100:8
```

If for some reason the DeepSpeed launcher is required, it can be used by editing the template above:

```bash
## Replace section after MASTER_PORT=...
HOSTFILE=hostfile.${SLURM_JOBID}.txt
function makehostfile() {
    perl -e '$slots=$ENV{"SLURM_GPUS_ON_NODE"};
    @nodes = split /\n/, qx[scontrol show hostnames $ENV{"SLURM_JOB_NODELIST"}];
    print map { "$b$_ slots=$slots\n" } @nodes'
}
makehostfile > $HOSTFILE
EXTRA_DEEPSPEED_ARGS=""
LAUNCHER="deepspeed --hostfile=$HOSTFILE --no_ssh \
          --master_addr=$MASTER_ADDR --master_port=$MASTER_PORT $EXTRA_DEEPSPEED_ARGS"

set -x
srun $SRUN_ARGS bash -c "$LAUNCHER --node_rank $SLURM_PROCID $CMD"
rm $HOSTFILE
```

# Troubleshooting jobs

Sometimes you might be surprised to find that your job is not getting the right resources or that it unexpectedly terminated. Here are some actions you can take to troubleshoot these issues.

If your job started less than 7 days ago, try running the `srecent` command. This command outputs a short summary of recent jobs and is often enough to understand the issue. This command is an alias to the slurm command `sacct`. In the sections below, we will use `sacct` to explore issues in more details, but the information printed is the same as what `srecent` provides.

## Allocation issues

To check the resources allocated to your job (AllocTRES), run:

```bash
sacct -X -j <job_id> -o "JOBName%-20, AllocTRES%-60, NodeList%-15"
```

Example output:

```bash
JobName    AllocTRES                                                    NodeList
---------- ------------------------------------------------------------ ---------------
ds_exp     billing=8,cpu=8,gres/gpu:v100=2,gres/gpu=2,mem=80G,node=2    mcnode[31-32]
ds_exp     billing=8,cpu=8,gres/gpu:a100=2,gres/gpu=2,mem=80G,node=2    mcnode[23,25]
```

Notice that some resources are automatically set if you don’t specify them. This is the case for the number of cpus for example.
A common issue is finding that these defaults are not suitable for your case and might need to be explicitly set.

Another common issue is not specifying the memory unit in the `--mem` option. The default unit is megabytes.

## Termination issues

Start by reviewing your job’s output and error logs. The logs often provide the termination reason. If the logs don’t clarify the issue, usethe command below to find out the end state of your job:

```bash
sacct -X -j <job_id> -o "JOBName%-20, State%-20, ExitCode"
```

Here are examples of the most common reasons for unexpected job termination:

```bash
JobID        JobName              State                ExitCode
------------ -------------------- -------------------- --------
180          adv_exp              OUT_OF_MEMORY           0:125
182          launch-jupyter       TIMEOUT                   0:0
187          a100_exp             CANCELLED BY 64030        0:0
```

**Note**: CANCELLED BY 64030 means the job was automatically terminated due to one of our termination policies.

## Complete job information

Sometimes we can get a better understanding of the issue by reviewing all the job details. Detailed job information can be obtained with:

```bash
sacct -j <job_id> --json | less
```

## Assistance

If the previous tips didn’t help you to identify the issue, please [reach out](/internal/rocs-testbed/contacts) to us. We’ll be happy to help. Be sure to provide a clear description of the issue and the job ID.
