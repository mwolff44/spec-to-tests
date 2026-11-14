#!/usr/bin/env python3
"""Hermetic behaviour tests for tdd-skill/scripts/tdd-verify-cycle.sh.

The gate is language-agnostic: its contract is a suite of Git-index and
worktree comparisons plus a caller-supplied runner.  These tests therefore
never import Python/Go/TS projects.  Every case builds a throwaway Git
repository under TMPDIR (or /tmp/opencode), uses TDD_LANG=custom with the
script's real TDD_SRC_RE / TDD_TEST_RE / TDD_RUN / TDD_RUN_ALL knobs, and
wires a tiny fake POSIX shell runner that succeeds iff its target file contains a
sentinel.  No network, no third-party library, no shared state.

What is asserted is the script's mechanics only -- not test quality, not an
agent's RED-before-GREEN chronology.  The script verifies a HEAD/index
contrast at commit time; it cannot attest how the change was authored.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve()
SKILL_ROOT = HERE.parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "tdd-verify-cycle.sh"

SENTINEL = "GREEN_SENTINEL"

# Fake runner: green when the selected target implements the behaviour.
# It is intentionally shell-only so the tests exercise a real external
# command through the script's eval-based runner templates.
RUNNER = f"""#!/bin/sh
target="${{FAKE_TARGET:-src/feature.py}}"
grep -q {SENTINEL} "$target" 2>/dev/null
"""


class GateRepoTest(unittest.TestCase):
    """Base fixture: an isolated Git repository and a controlled environment."""

    maxDiff = None

    def setUp(self) -> None:
        base = os.environ.get("TMPDIR") or "/tmp/opencode"
        pathlib.Path(base).mkdir(parents=True, exist_ok=True)
        self.repo = pathlib.Path(tempfile.mkdtemp(prefix="tdd-gate-", dir=base))
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)

        self.env = os.environ.copy()
        for key in (
            "TDD_LANG",
            "TDD_SRC_RE",
            "TDD_TEST_RE",
            "TDD_RUN",
            "TDD_RUN_ALL",
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_INDEX_FILE",
        ):
            self.env.pop(key, None)
        self.env.update(
            {
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_SYSTEM": os.devnull,
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_AUTHOR_NAME": "TDD Test",
                "GIT_AUTHOR_EMAIL": "tdd@example.invalid",
                "GIT_COMMITTER_NAME": "TDD Test",
                "GIT_COMMITTER_EMAIL": "tdd@example.invalid",
                "TDD_LANG": "custom",
                "TDD_SRC_RE": r"^src/.*\.py$",
                "TDD_TEST_RE": r"^tests/.*\.py$",
                "TDD_RUN": 'sh runner.sh "$sel"',
                "TDD_RUN_ALL": "sh runner.sh",
                "FAKE_TARGET": "src/feature.py",
            }
        )
        self.git("init", "-q", "-b", "main")

    # -- fixtures -----------------------------------------------------------
    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        proc = subprocess.run(
            ["git", *args],
            cwd=self.repo,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if check and proc.returncode != 0:
            self.fail(
                f"git {' '.join(args)} failed ({proc.returncode})\n"
                f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
            )
        return proc

    def write(self, rel: str, content: str) -> pathlib.Path:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def read_bytes(self, rel: str) -> bytes:
        return (self.repo / rel).read_bytes()

    def write_runner(self) -> None:
        self.write("runner.sh", RUNNER)

    def commit_all(self, message: str = "baseline") -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def baseline(
        self,
        src: str = "old\n",
        src_rel: str = "src/feature.py",
        test: str = "def test_x():\n    pass\n",
    ) -> None:
        self.write_runner()
        self.write(src_rel, src)
        self.write("tests/test_feature.py", test)
        self.commit_all()

    def stage(self, *rels: str) -> None:
        self.git("add", "--", *rels)

    def marker(self, first_line: str = "sel") -> None:
        self.write(".tdd-cycle", first_line + "\n")

    def run_gate(self, **overrides: str) -> subprocess.CompletedProcess:
        env = self.env.copy()
        env.update({str(k): str(v) for k, v in overrides.items()})
        return subprocess.run(
            ["bash", str(SCRIPT)],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    @staticmethod
    def output(proc: subprocess.CompletedProcess) -> str:
        return proc.stdout + proc.stderr

    def assert_gate_fails(self, proc: subprocess.CompletedProcess, needle: str) -> None:
        self.assertNotEqual(proc.returncode, 0, self.output(proc))
        self.assertIn(needle, self.output(proc))

    def index_snapshot(self) -> tuple[str, str]:
        return (
            self.git("ls-files", "-s").stdout,
            self.git("diff", "--cached", "--binary").stdout,
        )

    def untracked_files(self) -> list[str]:
        lines = self.git("status", "--porcelain").stdout.splitlines()
        return sorted(line[3:] for line in lines if line.startswith("?? "))


class CycleGateTests(GateRepoTest):
    # -- scope / declaration ------------------------------------------------
    def test_nothing_to_validate_exits_zero(self) -> None:
        """No staged production code and no marker: the gate stays out."""
        self.baseline()
        proc = self.run_gate()
        self.assertEqual(proc.returncode, 0, self.output(proc))

        # A test-only commit is also outside the gate's business.
        self.write(
            "tests/test_feature.py",
            "def test_x():\n    pass\n\ndef test_y():\n    pass\n",
        )
        self.stage("tests/test_feature.py")
        proc = self.run_gate()
        self.assertEqual(proc.returncode, 0, self.output(proc))

    def test_production_code_without_marker_is_rejected(self) -> None:
        self.baseline()
        self.write("src/feature.py", SENTINEL + "\n")
        self.stage("src/feature.py")
        proc = self.run_gate()
        self.assert_gate_fails(proc, "production code staged with no '.tdd-cycle' declared")

    def test_empty_marker_is_rejected(self) -> None:
        self.baseline()
        self.write("src/feature.py", SENTINEL + "\n")
        self.stage("src/feature.py")
        self.marker("")
        proc = self.run_gate()
        self.assert_gate_fails(proc, "is empty")

    def test_unknown_language_is_rejected(self) -> None:
        self.baseline()
        proc = self.run_gate(TDD_LANG="rust")
        self.assert_gate_fails(proc, "unknown TDD_LANG='rust'")

    # -- RED -> GREEN proof -------------------------------------------------
    def test_baseline_fails_and_proposal_passes(self) -> None:
        """HEAD lacks the behaviour (RED) and the index implements it (GREEN)."""
        self.baseline(src="old\n")
        self.write("src/feature.py", SENTINEL + "\n")
        self.write(
            "tests/test_feature.py",
            "def test_x():\n    pass\n\ndef test_new():\n    pass\n",
        )
        self.stage("src/feature.py", "tests/test_feature.py")
        self.marker("sel")

        proc = self.run_gate()
        self.assertEqual(proc.returncode, 0, self.output(proc))
        self.assertIn("RED confirmed", self.output(proc))
        self.assertIn("GREEN confirmed", self.output(proc))

    def test_first_green_without_new_code_is_rejected(self) -> None:
        """The strict profile refuses a target that is green at baseline."""
        self.baseline(src=SENTINEL + "\n")
        self.write("src/feature.py", SENTINEL + "\n# staged comment\n")
        self.write(
            "tests/test_feature.py",
            "def test_x():\n    pass\n\ndef test_already_green():\n    pass\n",
        )
        self.stage("src/feature.py", "tests/test_feature.py")
        self.marker("sel")

        proc = self.run_gate()
        self.assert_gate_fails(proc, "RED check FAILED")

    def test_new_file_structural_red_is_accepted(self) -> None:
        """A brand-new production file is absent at HEAD: ImportError-class RED."""
        self.write_runner()
        self.write("tests/test_feature.py", "def test_x():\n    pass\n")
        self.commit_all()

        self.write("src/feature.py", SENTINEL + "\n")
        self.write(
            "tests/test_feature.py",
            "def test_x():\n    pass\n\ndef test_new_api():\n    pass\n",
        )
        self.stage("src/feature.py", "tests/test_feature.py")
        self.marker("sel")

        proc = self.run_gate()
        self.assertEqual(proc.returncode, 0, self.output(proc))
        self.assertIn("RED confirmed", self.output(proc))
        self.assertIn("GREEN confirmed", self.output(proc))

    def test_failed_green_is_rejected(self) -> None:
        self.baseline(src="old\n")
        self.write("src/feature.py", "BROKEN\n")
        self.stage("src/feature.py")
        self.marker("sel")

        proc = self.run_gate()
        self.assert_gate_fails(proc, "GREEN check FAILED: with the staged code")

    # -- test-modification guard -------------------------------------------
    def test_deleted_test_file_is_rejected(self) -> None:
        self.baseline()
        self.write("src/feature.py", SENTINEL + "\n")
        self.stage("src/feature.py")
        self.git("rm", "-q", "tests/test_feature.py")
        self.marker("sel")

        proc = self.run_gate()
        self.assert_gate_fails(proc, "deletes existing test")

    def test_non_additive_test_edit_is_rejected(self) -> None:
        self.baseline()
        self.write("src/feature.py", SENTINEL + "\n")
        self.write("tests/test_feature.py", "def test_renamed():\n    pass\n")
        self.stage("src/feature.py", "tests/test_feature.py")
        self.marker("sel")

        proc = self.run_gate()
        self.assert_gate_fails(proc, "changes existing lines")

    def test_non_additive_test_edit_with_space_in_path_is_rejected(self) -> None:
        """Gate B must treat a spaced test path as one unit.

        Regression for the former ``for f in $staged_test_edits`` word-splitting
        bug: git was asked about a nonexistent path and reported zero removed
        lines, silently allowing a non-additive edit.  The gate now reads the
        test lists into arrays, so the path stays intact.
        """
        self.write_runner()
        self.write("src/feature.py", "old\n")
        self.write("tests/test feature.py", "def test_x():\n    pass\n")
        self.commit_all()
        self.write("src/feature.py", SENTINEL + "\n")
        self.write("tests/test feature.py", "def test_renamed():\n    pass\n")
        self.stage("src/feature.py", "tests/test feature.py")
        self.marker("sel")

        proc = self.run_gate()
        self.assert_gate_fails(proc, "changes existing lines")

    # -- refactor mode ------------------------------------------------------
    def test_refactor_without_test_change_is_green_only(self) -> None:
        self.baseline(src="old\n")
        self.write("src/feature.py", SENTINEL + "\n")
        self.stage("src/feature.py")
        self.marker("refactor")

        proc = self.run_gate()
        self.assertEqual(proc.returncode, 0, self.output(proc))
        self.assertIn("GREEN confirmed", self.output(proc))
        self.assertNotIn("RED confirmed", self.output(proc))

    def test_refactor_with_test_change_is_rejected(self) -> None:
        self.baseline(src="old\n")
        self.write("src/feature.py", SENTINEL + "\n")
        self.write(
            "tests/test_feature.py",
            "def test_x():\n    pass\n\ndef test_appended():\n    pass\n",
        )
        self.stage("src/feature.py", "tests/test_feature.py")
        self.marker("refactor")

        proc = self.run_gate()
        self.assert_gate_fails(proc, "refactor commit stages test files")

    def test_refactor_with_spaced_test_path_is_rejected(self) -> None:
        """Refactor diagnostics keep a spaced test path in one piece."""
        self.write_runner()
        self.write("src/feature.py", "old\n")
        self.write("tests/test feature.py", "def test_x():\n    pass\n")
        self.commit_all()

        self.write("src/feature.py", SENTINEL + "\n")
        self.write(
            "tests/test feature.py",
            "def test_x():\n    pass\n\ndef test_appended():\n    pass\n",
        )
        self.stage("src/feature.py", "tests/test feature.py")
        self.marker("refactor")

        proc = self.run_gate()
        self.assert_gate_fails(proc, "refactor commit stages test files")
        self.assertIn("  tests/test feature.py", self.output(proc))

    # -- runner / HEAD preconditions ---------------------------------------
    def test_missing_runner_is_rejected(self) -> None:
        self.baseline()
        self.write("src/feature.py", SENTINEL + "\n")
        self.stage("src/feature.py")
        self.marker("sel")

        proc = self.run_gate(
            TDD_RUN='definitely-no-such-runner-xyz "$sel"',
            TDD_RUN_ALL="definitely-no-such-runner-xyz",
        )
        self.assert_gate_fails(proc, "not found on PATH")

    def test_missing_head_is_rejected(self) -> None:
        self.write_runner()
        self.write("src/feature.py", SENTINEL + "\n")
        self.stage("src/feature.py")
        self.marker("sel")

        proc = self.run_gate()
        self.assert_gate_fails(proc, "no HEAD commit")

    # -- worktree / index preservation -------------------------------------
    def test_success_restores_worktree_bytes_and_index(self) -> None:
        self.baseline()
        self.write("src/feature.py", SENTINEL + "\n")
        self.stage("src/feature.py")
        tweaked = SENTINEL + "\n# unstaged local edit\n"
        self.write("src/feature.py", tweaked)
        self.write("scratch.txt", "keep me\n")
        self.marker("sel")

        before_index = self.index_snapshot()
        before_untracked = self.untracked_files()

        proc = self.run_gate()
        self.assertEqual(proc.returncode, 0, self.output(proc))
        # Unstaged bytes restored verbatim, index still proposes the staged blob.
        self.assertEqual(self.read_bytes("src/feature.py"), tweaked.encode())
        self.assertEqual(
            self.git("show", ":src/feature.py").stdout,
            SENTINEL + "\n",
        )
        self.assertEqual(self.index_snapshot(), before_index)
        self.assertEqual(self.untracked_files(), before_untracked)

    def test_failure_restores_worktree_bytes_and_index(self) -> None:
        self.baseline()
        self.write("src/feature.py", "BROKEN\n")
        self.stage("src/feature.py")
        tweaked = "BROKEN\n# unstaged local edit\n"
        self.write("src/feature.py", tweaked)
        self.write("scratch.txt", "keep me\n")
        self.marker("sel")

        before_index = self.index_snapshot()
        before_untracked = self.untracked_files()

        proc = self.run_gate()
        self.assert_gate_fails(proc, "GREEN check FAILED")
        self.assertEqual(self.read_bytes("src/feature.py"), tweaked.encode())
        self.assertEqual(self.git("show", ":src/feature.py").stdout, "BROKEN\n")
        self.assertEqual(self.index_snapshot(), before_index)
        self.assertEqual(self.untracked_files(), before_untracked)

    def test_deleted_worktree_source_is_refused_without_mutation(self) -> None:
        """A staged source deleted from the worktree cannot be backed up.

        The gate must refuse *before* any baseline/proposal swap: it must never
        turn a failed ``cp`` into an empty backup, which cleanup would later
        write back as a fabricated empty file.  The worktree deletion, the
        staged blob, untracked files and the index must all stay intact.
        """
        self.baseline()
        self.write("src/feature.py", SENTINEL + "\n")
        self.stage("src/feature.py")
        staged = self.git("show", ":src/feature.py").stdout
        (self.repo / "src/feature.py").unlink()
        self.write("scratch.txt", "keep me\n")
        self.marker("sel")

        before_index = self.index_snapshot()
        before_untracked = self.untracked_files()

        proc = self.run_gate()
        self.assert_gate_fails(proc, "cannot back up staged source 'src/feature.py'")
        self.assertFalse((self.repo / "src/feature.py").exists())
        self.assertEqual(self.git("show", ":src/feature.py").stdout, staged)
        self.assertEqual(self.index_snapshot(), before_index)
        self.assertEqual(self.untracked_files(), before_untracked)

    def test_failed_backup_copy_is_refused_without_mutation(self) -> None:
        """A failing ``cp`` refuses before the swap, with no empty backup."""
        self.baseline()
        self.write("src/feature.py", SENTINEL + "\n")
        self.stage("src/feature.py")
        self.write("scratch.txt", "keep me\n")
        self.marker("sel")
        # Controlled fault: the gate calls the unqualified `cp` for its backup.
        self.write("bin/cp", "#!/bin/sh\nexit 1\n")
        (self.repo / "bin/cp").chmod(0o755)
        fault_path = f"{self.repo / 'bin'}{os.pathsep}{self.env['PATH']}"

        before_index = self.index_snapshot()
        before_untracked = self.untracked_files()

        proc = self.run_gate(PATH=fault_path)
        self.assert_gate_fails(
            proc, "cannot back up staged source 'src/feature.py' (cp failed)"
        )
        self.assertEqual(self.read_bytes("src/feature.py"), (SENTINEL + "\n").encode())
        self.assertEqual(self.index_snapshot(), before_index)
        self.assertEqual(self.untracked_files(), before_untracked)

    def test_paths_with_spaces_restore_verbatim(self) -> None:
        src_rel = "src dir/feature module.py"
        self.baseline(src="old\n", src_rel=src_rel)
        self.write(src_rel, SENTINEL + "\n")
        self.stage(src_rel)
        tweaked = SENTINEL + "\n# unstaged local edit\n"
        self.write(src_rel, tweaked)
        self.marker("sel")

        proc = self.run_gate(
            TDD_SRC_RE=r"^src dir/.*\.py$",
            FAKE_TARGET=src_rel,
        )
        self.assertEqual(proc.returncode, 0, self.output(proc))
        self.assertIn("GREEN confirmed", self.output(proc))
        self.assertEqual(self.read_bytes(src_rel), tweaked.encode())
        self.assertEqual(self.git("show", f":{src_rel}").stdout, SENTINEL + "\n")


class ScriptStaticTests(unittest.TestCase):
    def test_script_exists_and_bash_syntax_is_valid(self) -> None:
        self.assertTrue(SCRIPT.is_file(), f"missing script: {SCRIPT}")
        proc = subprocess.run(
            ["bash", "-n", str(SCRIPT)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
