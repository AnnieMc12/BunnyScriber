"""
Configuration persistence for BunnyScriber.

Stores settings in a JSON file in the user's home directory.
API keys are stored locally and never uploaded.
"""

import json
import os
import copy

from bunnyscriber.constants import DEFAULT_CONFIG, CONFIG_FILENAME


def _config_path() -> str:
    """Return the path to the config file in the user's home directory."""
    return os.path.join(os.path.expanduser("~"), f".{CONFIG_FILENAME}")


def load_config() -> dict:
    """Load configuration from disk, returning defaults for missing keys."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    path = _config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            config.update(saved)
        except (json.JSONDecodeError, OSError):
            pass
    return config


def save_config(config: dict) -> None:
    """Save configuration to disk."""
    path = _config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_work_dir(config: dict) -> str:
    """Return the working directory for intermediate files."""
    work_dir = config.get("work_dir")
    if not work_dir:
        work_dir = os.path.join(os.path.expanduser("~"), "bunnyscriber_work")
    os.makedirs(work_dir, exist_ok=True)
    return work_dir
