"""Offline Colab setup smoke checks, never a claim of durable storage or training."""

from __future__ import annotations

import argparse
import fcntl
import importlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def check_storage(workspace: Path) -> dict:
    """Probe only an owned temporary directory; leave existing artifacts untouched."""
    workspace = workspace.resolve(strict=True)
    if not workspace.is_dir():
        raise ValueError("Workspace must be an existing mounted directory")
    with tempfile.TemporaryDirectory(prefix=".caferoomba-preflight-", dir=workspace) as tmp:
        directory = Path(tmp)
        source, target = directory / "new", directory / "published"
        payload = os.urandom(64)
        with source.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        target.write_bytes(b"previous")
        os.replace(source, target)
        directory_fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        if target.read_bytes() != payload or source.exists():
            raise RuntimeError("Workspace replacement/readback failed")
        # A separate interpreter must be unable to acquire our held lock, and
        # able to acquire it after release. Do not rely on inherited descriptors.
        lock_path = directory / "lock"
        child = (
            "import fcntl,sys\n"
            "with open(sys.argv[1], 'r+b') as stream:\n"
            " try: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
            " except BlockingIOError: sys.exit(23)\n"
        )
        with lock_path.open("xb") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            held = subprocess.run([sys.executable, "-c", child, str(lock_path)],
                                  capture_output=True, timeout=15, check=False)
            if held.returncode != 23:
                raise RuntimeError("Workspace does not enforce cross-process exclusion")
        released = subprocess.run([sys.executable, "-c", child, str(lock_path)],
                                  capture_output=True, timeout=15, check=False)
        if released.returncode != 0:
            raise RuntimeError("Workspace lock was not released")
    return {
        "write_replace_readback": True,
        "directory_fsync": True,
        "cross_process_lock": True,
        "restart_persistence_verified": False,
        "warning": "Verify persistence after runtime deletion separately; keep artifact backups.",
    }


def check_setup(repo: Path, workspace: Path, revision: str, device: str = "cpu") -> dict:
    """Check the selected kernel, pinned clean checkout and mounted filesystem.

    No package installation, authentication, network requests, training or runtime
    creation occurs here. Native import failures deliberately stop the preflight.
    """
    if sys.version_info < (3, 11):
        raise RuntimeError("Python 3.11 or newer required")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Expected a full 40-character published revision")
    if device not in {"cpu", "cuda"}:
        raise ValueError("Device must be cpu or cuda")
    repo = repo.resolve(strict=True)

    def git(*args: str) -> str:
        return subprocess.check_output(["git", "-C", str(repo), *args],
                                       text=True, timeout=15).strip()

    if git("rev-parse", "HEAD") != revision:
        raise ValueError("Checkout revision differs from the selected revision")
    if git("status", "--porcelain"):
        raise ValueError("Use a clean checkout for source provenance")
    import caferoomba

    if not Path(caferoomba.__file__).resolve().is_relative_to(repo / "src"):
        raise ValueError("Active kernel imports caferoomba from another checkout")
    versions = {}
    for name in ("torch", "onnx", "onnxruntime", "numpy", "PIL", "nbformat"):
        module = importlib.import_module(name)
        versions[name] = module.__version__
    if device == "cuda":
        torch = importlib.import_module("torch")
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA requested but unavailable in the active kernel")
        # Exercise the selected device rather than equating discovery with usability.
        (torch.ones(1, device="cuda") + 1).cpu()
    for executable in ("ffmpeg", "ffprobe"):
        binary = shutil.which(executable)
        if binary is None:
            raise RuntimeError(f"Missing required executable: {executable}")
        result = subprocess.run([binary, "-version"], check=True,
                                capture_output=True, text=True, timeout=15)
        versions[executable] = result.stdout.splitlines()[0]
    return {
        "schema_version": "caferoomba.colab-preflight.v1",
        "source_revision": revision,
        "python": platform.python_version(),
        "platform": platform.system(),
        "machine": platform.machine(),
        "requested_device": device,
        "versions": versions,
        "storage": check_storage(workspace),
        "training_executed": False,
        "cloud_runtime_created": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = parser.parse_args()
    print(json.dumps(check_setup(args.repo, args.workspace, args.revision, args.device), indent=2))


if __name__ == "__main__":
    main()
