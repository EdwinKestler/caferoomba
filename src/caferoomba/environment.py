"""Environment inspection used by doctor. No secret values."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(command: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=8)
        text = (result.stdout or result.stderr).strip()
        line = text.splitlines()[0] if text else ""
        return result.returncode, line
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""


def report() -> dict:
    mem = None
    if hasattr(os, "sysconf"):
        try:
            mem = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        except (ValueError, OSError):
            mem = None
    nvidia = _run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"])
    grok = _run(["grok", "--version"])
    _, commit = _run(["git", "-C", str(ROOT), "rev-parse", "HEAD"])
    _, branch = _run(["git", "-C", str(ROOT), "rev-parse", "--abbrev-ref", "HEAD"])
    _, dirty = _run(["git", "-C", str(ROOT), "status", "--porcelain"])
    return {
        "os": platform.platform(),
        "arch": platform.machine(),
        "python": platform.python_version(),
        "ram_bytes": mem,
        "git": {"commit": commit or None, "branch": branch or None, "dirty": bool(dirty)},
        "is_jetson": Path("/etc/nv_tegra_release").exists(),
        "tools": {
            "uv": _run(["uv", "--version"])[1] or None,
            "ffmpeg": _run(["ffmpeg", "-version"])[1] or None,
            "ffprobe": _run(["ffprobe", "-version"])[1] or None,
            "docker": _run(["docker", "--version"])[1] or None,
            "node": _run(["node", "--version"])[1] or None,
            "gcloud": _run(["gcloud", "--version"])[1] or None,
            "redis_cli": shutil.which("redis-cli"),
            "grok": grok[1] or None,
        },
        "nvidia_smi": nvidia[1] if nvidia[0] == 0 else None,
        "credentials_present": {
            "gcloud_adc": Path.home().joinpath(
                ".config/gcloud/application_default_credentials.json"
            ).exists(),
            "github_token_env": bool(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")),
            "nvidia_api_key": bool(os.environ.get("NVIDIA_API_KEY")),
            "cosmos_url": bool(os.environ.get("COSMOS_TEACHER_URL")),
        },
        "project_memory": {
            "config": (ROOT / ".project-memory.json").is_file(),
            "ledger": (ROOT / ".caferoomba/project-memory/memory-v25.sqlite3").is_file(),
        },
        "venv_dev": (ROOT / ".venv-dev").is_dir(),
        "legacy_requirements_not_installed_by_default": True,
    }
