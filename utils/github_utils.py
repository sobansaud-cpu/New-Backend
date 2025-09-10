import os
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Union
import shutil

def push_to_github(project_id: str, repo_name: str, token: str) -> Dict[str, Union[bool, str]]:
    try:
        if not all([project_id, repo_name, token]):
            raise ValueError("Missing required parameters")
        if "/" not in repo_name:
            raise ValueError("Repository name must be in format 'username/repo'")

        username, repo = repo_name.split("/")
        remote_url = f"https://{username}:{token}@github.com/{repo_name}.git"

        tmp_dir = tempfile.mkdtemp()
        project_dir = Path("projects") / project_id
        if not project_dir.exists():
            raise FileNotFoundError(f"Project not found: {project_dir}")

        shutil.copytree(project_dir, tmp_dir, dirs_exist_ok=True)

        # Initialize Git
        subprocess.run(["git", "init"], cwd=tmp_dir, check=True)
        subprocess.run(["git", "config", "user.name", "AI Builder"], cwd=tmp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "builder@example.com"], cwd=tmp_dir, check=True)

        # Add and commit
        subprocess.run(["git", "add", "."], cwd=tmp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit by AI Builder"], cwd=tmp_dir, check=True)

        # Set main as default branch (GitHub default)
        subprocess.run(["git", "branch", "-M", "main"], cwd=tmp_dir, check=True)

        # Add remote
        subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=tmp_dir, check=True)

        # Push to main
        push_result = subprocess.run(
            ["git", "push", "-u", "origin", "main"],
            cwd=tmp_dir,
            capture_output=True,
            text=True
        )

        if push_result.returncode != 0:
            raise Exception(f"Git push failed:\n{push_result.stderr}")

        return {
            "success": True,
            "repoUrl": f"https://github.com/{repo_name}",
            "message": "✅ Successfully pushed to GitHub"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
