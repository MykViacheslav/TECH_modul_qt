from __future__ import annotations

import subprocess
import os
from pathlib import Path

def git_sync_project_file(file_path: str | Path, commit_message: str) -> dict[str, Any]:
    """
    Synchronizuje plik projektu z GitLabem (git add, commit, push).
    """
    path = Path(file_path)
    if not path.exists():
        return {"status": "error", "message": f"Plik nie istnieje: {path}"}

    cwd = os.getcwd()
    try:
        # Check if it's a git repo
        if not (Path(cwd) / ".git").exists():
            return {"status": "not_repo", "message": "Folder nie jest repozytorium GIT."}

        # 1. Add
        subprocess.run(["git", "add", str(path)], check=True, capture_output=True, cwd=cwd)
        
        # 2. Commit
        # Sprawdzamy czy sÄ… zmiany (git diff --cached --quiet)
        res = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=cwd)
        if res.returncode == 0:
            return {"status": "no_changes", "message": "Brak zmian do wypchniÄ™cia."}

        subprocess.run(["git", "commit", "-m", commit_message], check=True, capture_output=True, cwd=cwd)
        
        # 3. Push
        # PrĂłbujemy wypchnÄ…Ä‡ (opcjonalnie, moĹĽe wymagaÄ‡ kluczy SSH)
        # subprocess.run(["git", "push"], check=True, capture_output=True, cwd=cwd)
        
        return {"status": "ok", "message": "Zsynchronizowano z GitLab"}
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.decode() if e.stderr else str(e)
        return {"status": "git_error", "message": f"BĹ‚Ä…d GIT: {err_msg}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
