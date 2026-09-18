---
name: clearml-jobs
description: Submit training and other GPU jobs to the SIL ClearML server (api.sil.hosted.allegro.ai) and monitor them. Use when creating or editing a launcher script (run_train.py-style) that enqueues work to a ClearML queue, choosing a queue/GPU, forwarding config values to a remote training script, debugging a task that fails on the agent (docker image, requirements, missing code), or checking task status, logs and workers. Covers the launcher/worker split, Task.create + execute_remotely, queue and hardware map, and the REST monitoring helpers.
---

# ClearML Jobs (SIL)

How we post jobs to the SIL ClearML server. The pattern is the same in `asr-finetuning`,
`tts-finetuning`, `madlad-finetuning`, `T5Gemma-finetuning` and `bt-finetuning`: a **launcher**
runs locally and creates/enqueues a task; a **worker script** runs on the GPU agent.

```
run_train.py  (local, no GPU)          train.py  (on the ClearML agent, GPU)
  Task.create(script="train.py", ...)    Task.init(...)   <- first, before argparse
  task.execute_remotely(queue_name=q)    argparse reads ClearML-injected values
```

Never put training logic in the launcher and never call `Task.create` from the worker script.

## Server and credentials

| | |
|---|---|
| API | `https://api.sil.hosted.allegro.ai` |
| Web UI | `https://app.sil.hosted.allegro.ai/` |
| Files | `https://files.sil.hosted.allegro.ai` |

Normal setup is `clearml-init`, which writes `~/clearml.conf` — the SDK picks it up with no code
changes. Repos that talk to the REST API directly keep creds in `.env` as
`CLEARML_ACCES_KEY` (sic, typo'd in several repos) / `CLEARML_SECRET_KEY`; the SDK env-var names
are `CLEARML_API_ACCESS_KEY` / `CLEARML_API_SECRET_KEY` / `CLEARML_API_HOST`.

HuggingFace tokens are **not** passed through ClearML parameters — the trainers read
`os.getenv("HF_TOKEN")` from the agent's environment. A new secret needs either a worker-side env
var or `docker_args="--env FOO=bar"`.

## Queues and hardware

| Queue | Worker | GPUs | Use for |
|---|---|---|---|
| `cheetah_94gb` | `cheetah-gpu-dallas` | 2 × ~96 GB (H100 NVL class) | Long or large training. **Default for real runs.** |
| `jobs_urgent` | `aqua-gpu-dallas` | 8 × ~40 GB (A100 40GB class) | Short jobs, the historical default in the finetuning repos |
| `jobs_backlog` | `aqua-gpu-dallas` | same pool | Low-priority / overnight |
| `production` | `aqua-gpu-dallas` | same pool | Aqua production capacity — **don't park long jobs here** |

The `aqua-gpu-dallas` queues are shared with Aqua production. A 40 GB card will not hold a 27B+
model at long sequence lengths; that work belongs on `cheetah_94gb`.

`queues.get_all` lists the rest: `cheetah_47gb` (half-card slice of the same box), `multi_gpu`,
the older `lambert_24gb` / `shannon_24gb` boxes, and a `.cpu_only` variant of each shared queue
(`jobs_urgent.cpu_only`, `jobs_backlog.cpu_only`, `production.cpu_only`) — use those for data prep
or upload tasks so they don't sit on a GPU.

Make the queue a config field (`queue: str = "jobs_urgent"`) plus a `--queue` CLI override, as in
`asr-finetuning/config_settings.py` — never hard-code it at the `execute_remotely` call.

## The launcher

```python
from clearml import Task

task = Task.create(
    project_name="IDX TTS",                 # see project names below
    task_name=f"TTS-{dataset.split('/')[-1]}-{model_suffix}",
    script="train.py",                      # path in the repo, run by the agent
    add_task_init_call=False,               # train.py calls Task.init() itself
    requirements_file="requirements.txt",
    docker="pytorch/pytorch:2.7.0-cuda11.8-cudnn9-runtime",
    docker_bash_setup_script=(
        "apt-get update && apt-get install -y software-properties-common "
        "&& add-apt-repository -y ppa:ubuntuhandbook1/ffmpeg7 "
        "&& apt-get update && apt-get install -y ffmpeg && pip uninstall -y torchvision"
    ),
    argparse_args=[("dataset", dataset), ("epochs", epochs), ...],
)
task.execute_remotely(queue_name=queue)
```

`templates/run_train.py` in this skill is a working starter version of the whole file.

Project names in use: `IDX ASR`, `IDX TTS`, `IDX Translation Fine-tuning/IDX MADLAD Exp`,
`bt-finetuning`. Put a new experiment under the existing project for its modality rather than
inventing a sibling; `/` nests sub-projects.

Task names should carry the dataset and the variant — `f"ASR-{dataset.split('/')[-1]}-{suffix}"` —
because the queue view shows nothing else. `task.set_tags([source_lang, target_lang])` (madlad)
makes a sweep filterable.

### Arguments: the parameter bridge

`argparse_args` is a list of `(name, value)` pairs that ClearML stores as hyperparameters and
injects into the worker's argparse at `Task.init`. Rules that bite:

- **Everything is stringified.** Pass `str(v)`; `None` becomes the literal string `"None"`, so
  drop `None` values instead of forwarding them (`exclude_none=True` in
  `tts-finetuning/config.py::to_args_list`).
- **`store_true` flags** are passed as `(name, "")` — presence is what counts.
- **Lists** go as a space-joined string (`("books", " ".join(books))`) with `nargs="*"` on the
  worker side.
- **Names must match the worker's argparse exactly**, underscores and all.

With a Pydantic config, forward every field and subtract the launcher-only ones rather than
listing fields by hand — a field added to the config then reaches `train.py` for free:

```python
argparse_args=[
    ("epochs", epochs), ("model_suffix", model_suffix),   # overridden per-model
] + [
    (field, getattr(args, field))
    for field in config.model_fields
    if field not in {"epochs", "model_suffix",        # set above
                     "model_base", "num_models",      # launcher-only scheduling
                     "min_epochs", "max_epochs",
                     "queue", "docker", "config"}     # launcher-only infrastructure
]
```

Print the resolved args before submitting (both repos do). It is the only cheap chance to catch a
misspelled field, and a wrong value costs a full GPU run.

### The worker script

```python
# train.py — top of file, BEFORE argparse is built
from clearml import Task
task = Task.init(project_name="IDX TTS", task_name="TTS Training")
```

`Task.init` patches argparse; if it runs after `parse_args()` the injected values are silently
ignored and the job trains on defaults. The `project_name`/`task_name` here are placeholders —
when the agent runs the task, the launcher's names win.

`tts-finetuning` wraps it in try/except so `python train.py --dataset ... --max_rows 32` still
runs locally as a smoke test without ClearML. Worth copying.

Inside the worker, `Task.current_task().get_logger()` reports scalars, images and audio to the
task's plots tab (see `SpectrogramLogCallback` in `tts-finetuning/train.py`). HF `Trainer` users
just set `--report-to clearml`.

### Sweeps

A sweep is a loop around `Task.create` — one task per variant, all enqueued before the launcher
exits (`asr-finetuning/run_train.py` generates a geometric epoch schedule and submits N models).
`execute_remotely` on a `Task.create`d task only enqueues, so the loop continues; on the *current*
task (one made by `Task.init`) it aborts the local process after enqueuing.

Print a summary table of `(variant, task.id)` at the end — those ids are what you monitor with.

### Code delivery to the agent

By default the agent reconstructs the repo: recorded git remote + commit, plus a diff of
**uncommitted changes to tracked files**. So:

- Untracked files do not travel. A brand-new module must be `git add`ed before submitting.
- The agent needs read access to the repo. When it doesn't have it (private repo, or the files
  server is down), fall back to the `bt-finetuning/launchers/launch_train.py` approach: tar the
  modules, base64 them into a bootstrap script, force it in with
  `task.update_task({"script": {"binary": "python3", "diff": src, "entry_point": ...}})`, then
  `Task.enqueue(task, queue_name=...)`. Run that launcher from a **non-git** directory or ClearML
  resolves the repo instead of embedding, and assert the stored diff length afterwards — it
  truncates silently.

`Task.enqueue(task, queue_name=...)` is the alternative to `execute_remotely` when you need to
edit the task between creation and launch.

## Docker images and environment

The agent pulls `docker=`, runs `docker_bash_setup_script` as root, then builds a venv from
`requirements_file`.

- Put **apt** packages in `docker_bash_setup_script` (that's where `ffmpeg` comes from). The
  trailing `pip uninstall -y torchvision` in the pytorch image avoids a torchvision/torch ABI
  mismatch when requirements pull a different torch.
- Keep `requirements.txt` torch/CUDA pins consistent with the image, or the venv build silently
  reinstalls torch and wastes 10 minutes per job.
- For an image that already has the dependencies, skip the venv entirely:

```python
docker_args=" ".join([
    "--entrypoint=",                                        # needed for e.g. vllm/vllm-openai
    "--env CLEARML_AGENT_SKIP_PIP_VENV_INSTALL=/usr/bin/python3",
    "--env CLEARML_AGENT_SKIP_PYTHON_ENV_INSTALL=1",
    "--shm-size=16g",                                       # dataloader workers need it
])
```

## Monitoring

Web UI first: `https://app.sil.hosted.allegro.ai/` → project → task → CONSOLE / SCALARS.

From Python:

```python
from clearml import Task
t = Task.get_task(task_id="<id>")
print(t.get_status())                 # queued | in_progress | completed | failed | stopped
t.get_reported_scalars()              # metric history
```

From the shell, `scripts/clearml_helpers.sh` in this skill wraps the REST API:

```bash
source scripts/clearml_helpers.sh
T=$(get_token)              # Basic auth 401s on most endpoints; auth.login → Bearer token
workers "$T"                # which worker is busy, and with what
task_status "$T" <task_id>
task_log "$T" <task_id> 200
```

`workers "$T"` before submitting is the quick check for whether a queue is actually being served —
a task sitting in `queued` usually means no agent is up, not a bad task.

## Gotchas

1. `add_task_init_call=False` when the worker script calls `Task.init` itself (asr, tts);
   `True` only when it doesn't (madlad). Getting it wrong gives a duplicate init or no parameters.
2. `Task.init` must precede argparse construction in the worker.
3. `None` forwarded through `argparse_args` arrives as the string `"None"`.
4. Untracked files are not in the task diff.
5. Long jobs on `production` / `jobs_*` squeeze Aqua; use `cheetah_94gb`.
6. `execute_remotely` from a script that itself ran `Task.init` will abort that script — expected,
   but surprising inside a loop.
7. A failed job that never printed a training line is nearly always image/requirements, not code:
   read the first 100 log lines (`task_log`) before re-reading the trainer.

## Checklist before submitting

- [ ] New/renamed files committed (they ride in the diff only if tracked)
- [ ] Args printed and eyeballed — dataset, epochs/steps, output repo, `push_to_hub`
- [ ] Output HF repo name won't clobber a previous run's
- [ ] Queue matches the model size, and a worker is serving it
- [ ] A short local or `--max_rows` smoke test passed first
