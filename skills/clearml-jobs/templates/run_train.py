#!/usr/bin/env python3
"""ClearML task submission for <project> training.

Runs locally: builds the task, forwards config to train.py, enqueues it.

    python run_train.py --config configs/examples/example.yaml --queue cheetah_94gb
"""
from clearml import Task
import argparse
import sys

from config_settings import TrainingConfig  # Pydantic settings model


p = argparse.ArgumentParser(description="Submit training job to ClearML")
p.add_argument("--config", type=str, help="Path to YAML/TOML config file")
p.add_argument("--dataset", type=str, help="HuggingFace dataset name")
p.add_argument("--epochs", type=float, help="Number of epochs")
p.add_argument("--lr", type=float, help="Learning rate")
p.add_argument("--model_suffix", type=str, help="Suffix for the hub model name")
p.add_argument("--push_to_hub", action="store_true", help="Push model to the hub")
# Launcher-only (not forwarded to train.py)
p.add_argument("--queue", type=str, help="ClearML queue name")
p.add_argument("--docker", type=str, help="Docker image for the agent")

args = p.parse_args()

cli_overrides = {k: v for k, v in vars(args).items()
                 if v is not None and not (isinstance(v, bool) and not v)}
try:
    config = TrainingConfig.from_yaml_and_args(args.config, cli_overrides)
except Exception as e:
    print(f"Configuration error: {e}", file=sys.stderr)
    sys.exit(1)

LAUNCHER_ONLY = {"config", "queue", "docker"}

args_list = []
for field in config.model_fields:
    if field in LAUNCHER_ONLY:
        continue
    value = getattr(config, field)
    if value is None:
        continue                       # "None" would arrive as a literal string
    if isinstance(value, bool):
        if value:
            args_list.append((field, ""))   # store_true flag: presence is the value
        continue
    if isinstance(value, list):
        args_list.append((field, " ".join(str(v) for v in value)))
        continue
    args_list.append((field, str(value)))

print("=== Submitting to ClearML ===")
for k, v in args_list:
    print(f"  --{k} (flag)" if v == "" else f"  --{k}: {v}")
print("=============================")

task = Task.create(
    project_name="IDX <MODALITY>",
    task_name=f"<PREFIX>-{config.dataset.split('/')[-1]}"
              f"{'-' + config.model_suffix if config.model_suffix else ''}",
    script="train.py",
    add_task_init_call=False,          # train.py calls Task.init() itself
    requirements_file="requirements.txt",
    docker=config.docker,
    docker_bash_setup_script=(
        "apt-get update && apt-get install -y software-properties-common "
        "&& add-apt-repository -y ppa:ubuntuhandbook1/ffmpeg7 "
        "&& apt-get update && apt-get install -y ffmpeg && pip uninstall -y torchvision"
    ),
    argparse_args=args_list,
)

task.execute_remotely(queue_name=config.queue)
print(f"Submitted task {task.id} to queue {config.queue}")
