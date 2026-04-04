#!/usr/bin/env python3
"""
Apply data-dir configuration for TECH_modul.
Reads repository data_config.json (or the template) and, if TECH_MODUL_DATA_DIR is set,
defines the environment variable for the running process. This helps to switch between
production sandbox data without editing code.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_config() -> dict:
    root = get_repo_root()
    config_path = root / "data_config.json"
    if not config_path.exists():
        config_path = root / "data_config.json.template"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def apply_config() -> None:
    cfg = load_config()
    value = cfg.get("TECH_MODUL_DATA_DIR")
    if value:
        expanded = Path(value).expanduser().resolve()
        os.environ["TECH_MODUL_DATA_DIR"] = str(expanded)
        print(f"[data_dir_config] Set TECH_MODUL_DATA_DIR to {expanded}")
    else:
        print("[data_dir_config] No TECH_MODUL_DATA_DIR set in config; using existing environment or default data dir.")


if __name__ == "__main__":
    apply_config()
