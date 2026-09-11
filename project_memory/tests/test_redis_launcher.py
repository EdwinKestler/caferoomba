from __future__ import annotations

import os
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path


class RedisLauncherSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[2]
        cls.script = cls.root / "scripts/project_memory_redis.sh"
        cls.lab_root = cls.root / ".caferoomba"
        cls.lab_root.mkdir(mode=0o700, exist_ok=True)

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="launcher-test-", dir=self.lab_root
        )
        self.addCleanup(self.temporary.cleanup)
        self.sandbox = Path(self.temporary.name)
        self.fake_cli = self.sandbox / "redis-cli"
        self.fake_cli.write_text(
            "#!/bin/sh\n"
            "if [ \"${FAKE_REDIS_ANSWERS:-0}\" = 1 ]; then printf 'PONG\\n'; fi\n"
            "exit 0\n",
            encoding="utf-8",
        )
        self.fake_cli.chmod(0o700)

    def _environment(self, state: Path, socket_path: Path, *, answers: bool) -> dict[str, str]:
        return {
            **os.environ,
            "PROJECT_MEMORY_REDIS_DIR": str(state),
            "PROJECT_MEMORY_REDIS_SOCKET": str(socket_path),
            "REDIS_SERVER_BIN": "/bin/true",
            "REDIS_CLI_BIN": str(self.fake_cli),
            "FAKE_REDIS_ANSWERS": "1" if answers else "0",
        }

    def _run(
        self,
        command: str,
        state: Path,
        socket_path: Path,
        *,
        answers: bool,
        server_bin: str = "/bin/true",
    ) -> subprocess.CompletedProcess[str]:
        environment = self._environment(state, socket_path, answers=answers)
        environment["REDIS_SERVER_BIN"] = server_bin
        return subprocess.run(
            [str(self.script), command],
            cwd=self.root,
            env=environment,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )

    def test_reset_removes_only_redis_state_and_preserves_sqlite_ledger(self) -> None:
        state = self.sandbox / "redis-state"
        state.mkdir()
        (state / "redis.log").write_text("disposable redis log\n", encoding="utf-8")
        (state / "dump.rdb").write_bytes(b"disposable projection")
        (state / "temp-checkpoint.rdb").write_bytes(b"disposable temporary projection")
        socket_path = state / "redis.sock"
        stale_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale_socket.bind(str(socket_path))
        stale_socket.close()
        self.assertTrue(socket_path.exists())
        durable = state / "memory-v25.sqlite3"
        durable_bytes = b"SQLite durable authority must survive Redis reset"
        durable.write_bytes(durable_bytes)
        evidence = state / "operator-evidence.txt"
        evidence.write_text("preserve operator evidence\n", encoding="utf-8")
        unrelated = state / "notes.bin"
        unrelated.write_bytes(b"preserve unrelated state")

        result = self._run("reset", state, socket_path, answers=False)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(state.is_dir())
        for disposable in ("redis.log", "dump.rdb", "temp-checkpoint.rdb", "redis.sock"):
            self.assertFalse((state / disposable).exists(), disposable)
        self.assertEqual(durable.read_bytes(), durable_bytes)
        self.assertEqual(
            evidence.read_text(encoding="utf-8"), "preserve operator evidence\n"
        )
        self.assertEqual(unrelated.read_bytes(), b"preserve unrelated state")

    def test_reset_preflights_all_deletions_before_stop_has_side_effects(self) -> None:
        state = self.sandbox / "p"
        state.mkdir()
        pid_file = state / "redis.pid"
        pid_file.write_text("999999999\n", encoding="utf-8")
        socket_path = state / "s"
        stale_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale_socket.bind(str(socket_path))
        stale_socket.close()
        evidence = self.sandbox / "outside-log-evidence"
        evidence.write_text("must remain untouched\n", encoding="utf-8")
        (state / "redis.log").symlink_to(evidence)

        result = self._run("reset", state, socket_path, answers=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", (result.stdout + result.stderr).lower())
        self.assertEqual(pid_file.read_text(encoding="utf-8"), "999999999\n")
        self.assertTrue(socket_path.exists())
        self.assertTrue(socket_path.is_socket())
        self.assertEqual(evidence.read_text(encoding="utf-8"), "must remain untouched\n")

    def test_start_and_stop_refuse_a_symlinked_state_directory(self) -> None:
        for command, answers in (("start", True), ("stop", False)):
            with self.subTest(command=command):
                real_state = self.sandbox / f"real-state-{command}"
                real_state.mkdir()
                (real_state / "redis.log").write_text("preserve\n", encoding="utf-8")
                if command == "start":
                    (real_state / "redis.pid").write_text(
                        f"{os.getpid()}\n", encoding="utf-8"
                    )
                linked_state = self.sandbox / f"linked-state-{command}"
                linked_state.symlink_to(real_state, target_is_directory=True)
                socket_path = linked_state / "redis.sock"
                result = self._run(
                    command, linked_state, socket_path, answers=answers
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("symlink", (result.stdout + result.stderr).lower())
                self.assertTrue(linked_state.is_symlink())
                self.assertTrue(real_state.is_dir())

    def test_start_and_stop_refuse_a_non_socket_occupant(self) -> None:
        for command, answers in (("start", True), ("stop", False)):
            with self.subTest(command=command):
                state = self.sandbox / f"non-socket-{command}"
                state.mkdir()
                (state / "redis.log").write_text("preserve\n", encoding="utf-8")
                if command == "start":
                    (state / "redis.pid").write_text(
                        f"{os.getpid()}\n", encoding="utf-8"
                    )
                socket_path = state / "redis.sock"
                occupant = b"ordinary file must not be unlinked as a socket"
                socket_path.write_bytes(occupant)

                result = self._run(command, state, socket_path, answers=answers)

                self.assertNotEqual(result.returncode, 0)
                output = (result.stdout + result.stderr).lower()
                self.assertTrue("socket" in output and ("refus" in output or "regular" in output))
                self.assertEqual(socket_path.read_bytes(), occupant)

    def test_stop_removes_a_well_formed_dead_pid_as_safe_stale_state(self) -> None:
        state = self.sandbox / "stale-pid"
        state.mkdir()
        (state / "redis.log").write_text("preserve\n", encoding="utf-8")
        pid_file = state / "redis.pid"
        pid_file.write_text("999999999\n", encoding="utf-8")
        socket_path = state / "redis.sock"

        result = self._run("stop", state, socket_path, answers=False)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(pid_file.exists())
        self.assertTrue(state.is_dir())
        self.assertEqual(
            (state / "redis.log").read_text(encoding="utf-8"), "preserve\n"
        )

    def test_start_and_stop_refuse_malformed_or_symlinked_pid_state(self) -> None:
        for command in ("start", "stop"):
            for kind in ("malformed", "symlink"):
                with self.subTest(command=command, kind=kind):
                    state = self.sandbox / f"pid-{command}-{kind}"
                    state.mkdir()
                    (state / "redis.log").write_text("preserve\n", encoding="utf-8")
                    pid_file = state / "redis.pid"
                    if kind == "malformed":
                        pid_file.write_text("not-a-pid\n", encoding="utf-8")
                        evidence_path = pid_file
                    else:
                        evidence_path = self.sandbox / f"pid-target-{command}"
                        evidence_path.write_text("999999999\n", encoding="utf-8")
                        pid_file.symlink_to(evidence_path)
                    before = evidence_path.read_bytes()
                    socket_path = state / "redis.sock"

                    result = self._run(
                        command,
                        state,
                        socket_path,
                        answers=False,
                        server_bin="/bin/false",
                    )

                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("pid", (result.stdout + result.stderr).lower())
                    self.assertTrue(pid_file.exists() or pid_file.is_symlink())
                    self.assertEqual(evidence_path.read_bytes(), before)

    def test_start_and_stop_refuse_an_unrelated_live_or_reused_pid(self) -> None:
        for command in ("start", "stop"):
            with self.subTest(command=command):
                state = self.sandbox / ("u-a" if command == "start" else "u-b")
                state.mkdir()
                (state / "redis.log").write_text("preserve\n", encoding="utf-8")
                pid_file = state / "redis.pid"
                pid_file.write_text(f"{os.getpid()}\n", encoding="utf-8")
                socket_path = state / "s"
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as responder:
                    responder.bind(str(socket_path))
                    os.chmod(socket_path, 0o600)

                    result = self._run(command, state, socket_path, answers=True)

                    self.assertNotEqual(result.returncode, 0)
                    output = (result.stdout + result.stderr).lower()
                    self.assertTrue(
                        "pid" in output
                        or "not owned" in output
                        or "not launcher-owned" in output
                    )
                    self.assertEqual(
                        pid_file.read_text(encoding="utf-8"), f"{os.getpid()}\n"
                    )
                    self.assertTrue(socket_path.exists())


if __name__ == "__main__":
    unittest.main()
