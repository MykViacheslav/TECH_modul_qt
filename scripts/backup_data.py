#!/usr/bin/env python3
"""
Backup local TECH_modul data directory (offline mode).

- Uses TECH_MODUL_DATA_DIR if set; otherwise falls back to <repo_root>/data
- Creates a timestamped backup under <repo_root>/data_backups/backup_YYYYMMDD_HHMMSS/
- Copies the entire data directory preserving structure
- No encryption is applied (as requested)
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from datetime import datetime


def get_data_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[1]  # scripts/.. -> repo root
    data_dir_env = os.environ.get("TECH_MODUL_DATA_DIR")
    if data_dir_env:
        p = Path(data_dir_env).expanduser().resolve()
        if p.exists():
            return p
    return (repo_root / "data").resolve()


def ensure_backup_root(backup_root: Path) -> None:
    backup_root.mkdir(parents=True, exist_ok=True)


def main() -> int:
    data_dir = get_data_dir()
    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        return 1

    repo_root = data_dir.parents[1]  # one level above data -> repo root
    backup_root = repo_root / "data_backups"
    ensure_backup_root(backup_root)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_target = backup_root / f"backup_{timestamp}"
    destination = backup_target / data_dir.name

    print(f"Creating backup: {destination}")
    try:
        # Copy the entire data directory into the backup destination
        shutil.copytree(data_dir, destination)
    except Exception as e:
        print(f"Backup failed: {e}")
        return 2

    print(f"Backup completed successfully at {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
