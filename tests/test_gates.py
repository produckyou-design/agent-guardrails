"""Tests for the gates.

These build a real git repository in a temp directory, make real commits, and
run the gates as subprocesses. Nothing is mocked, because the thing being
tested is how the gates read git.

Run:
    python tests/test_gates.py
    python -m unittest discover tests
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATES = ROOT / "gates"

FROZEN = {
    "version": 1,
    "frozen": [
        {
            "label": "Billing",
            "paths": ["src/billing/charge.py"],
            "reason": "Finished and in production.",
            "what_breaks": "Wrong math still renders a normal screen.",
            "before_you_touch": ["Partial refunds live in refund.py."],
            "how_to_verify": "pytest tests/test_billing.py -q",
        }
    ],
}


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8"
    )


def run_gate(repo: Path, name: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(repo / "scripts" / name), *args],
        cwd=repo, capture_output=True, text=True, encoding="utf-8",
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


class GateTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="guardrails-test-"))
        self.repo = self.tmp / "repo"
        (self.repo / "scripts").mkdir(parents=True)
        for gate in GATES.glob("*.py"):
            shutil.copy(gate, self.repo / "scripts" / gate.name)
        write(self.repo / "frozen.json", json.dumps(FROZEN, indent=2))
        write(self.repo / "src" / "billing" / "charge.py", "def charge():\n    return 1\n")
        write(self.repo / "src" / "other.py", "x = 1\n")

        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "test")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "init")
        git(self.repo, "branch", "-M", "main")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def commit(self, path: str, body: str, message: str) -> None:
        write(self.repo / path, body)
        git(self.repo, "add", path)
        git(self.repo, "commit", "-q", "-m", message)


class TestFrozen(GateTestCase):
    def test_free_path_passes(self):
        self.commit("src/other.py", "x = 2\n", "touch a free path")
        r = run_gate(self.repo, "check_frozen.py")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_frozen_path_without_declaration_fails(self):
        self.commit("src/billing/charge.py", "def charge():\n    return 2\n", "edit frozen path")
        r = run_gate(self.repo, "check_frozen.py")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("frozen: FAIL", r.stdout)

    def test_reason_line_alone_is_not_enough(self):
        # A reason answers "why now". It does not answer what breaks or how to
        # get back, which are the two questions that matter. One line is refused.
        self.commit(
            "src/billing/charge.py", "def charge():\n    return 3\n",
            "billing: new method\n\n"
            "UNFREEZE: src/billing/charge.py - new payment method needs a branch",
        )
        r = run_gate(self.repo, "check_frozen.py")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)

    def test_missing_rollback_is_not_enough(self):
        self.commit(
            "src/billing/charge.py", "def charge():\n    return 4\n",
            "billing: new method\n\n"
            "UNFREEZE: src/billing/charge.py - new payment method needs a branch\n"
            "UNFREEZE-IMPACT: wrong math renders a normal screen, only amounts change",
        )
        r = run_gate(self.repo, "check_frozen.py")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)

    def test_all_three_lines_pass(self):
        self.commit(
            "src/billing/charge.py", "def charge():\n    return 5\n",
            "billing: new method\n\n"
            "UNFREEZE: src/billing/charge.py - new payment method needs a branch\n"
            "UNFREEZE-IMPACT: wrong math renders a normal screen, only amounts change\n"
            "UNFREEZE-ROLLBACK: git revert HEAD, then re-run pytest tests/test_billing.py",
        )
        r = run_gate(self.repo, "check_frozen.py")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("allowed by UNFREEZE", r.stdout)

    def test_empty_reason_is_refused(self):
        self.commit(
            "src/billing/charge.py", "def charge():\n    return 6\n",
            "billing: new method\n\n"
            "UNFREEZE: src/billing/charge.py -   \n"
            "UNFREEZE-IMPACT: wrong math renders a normal screen\n"
            "UNFREEZE-ROLLBACK: git revert HEAD",
        )
        r = run_gate(self.repo, "check_frozen.py")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)

    def test_hyphen_in_path_survives(self):
        # An earlier version stripped hyphens out of the target, truncating
        # "src/db/sync-notices.py" to "src/db/sync" and, because matching is a
        # substring test, unlocking every frozen path with that prefix.
        frozen = json.loads(json.dumps(FROZEN))
        frozen["frozen"][0]["paths"] = ["src/db/sync-notices.py", "src/db/sync_orders.py"]
        write(self.repo / "frozen.json", json.dumps(frozen, indent=2))
        write(self.repo / "src" / "db" / "sync-notices.py", "a = 1\n")
        write(self.repo / "src" / "db" / "sync_orders.py", "b = 1\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "add db files")

        # Declare only sync-notices.py, then change sync_orders.py too.
        write(self.repo / "src" / "db" / "sync-notices.py", "a = 2\n")
        write(self.repo / "src" / "db" / "sync_orders.py", "b = 2\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m",
            "db: touch notices\n\n"
            "UNFREEZE: src/db/sync-notices.py - upstream changed the feed format\n"
            "UNFREEZE-IMPACT: notices stop importing, the page goes empty\n"
            "UNFREEZE-ROLLBACK: git revert HEAD")
        r = run_gate(self.repo, "check_frozen.py")
        self.assertEqual(r.returncode, 1, "declaring one file must not unlock another\n"
                                          + r.stdout + r.stderr)

    def test_declaration_in_a_later_commit_does_not_backdate(self):
        # Edit a frozen file with no declaration, then add a declaration-only
        # commit. Without a per-commit rule this would retroactively legalize it.
        self.commit("src/billing/charge.py", "def charge():\n    return 7\n", "edit frozen path")
        self.commit(
            "src/other.py", "x = 3\n",
            "chore: unrelated\n\n"
            "UNFREEZE: src/billing/charge.py - after the fact\n"
            "UNFREEZE-IMPACT: wrong math renders a normal screen\n"
            "UNFREEZE-ROLLBACK: git revert HEAD",
        )
        r = run_gate(self.repo, "check_frozen.py", "--base", "HEAD~2", "--head", "HEAD")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)

    def test_late_marker_passes_but_is_disclosed(self):
        self.commit("src/billing/charge.py", "def charge():\n    return 8\n", "edit frozen path")
        self.commit(
            "src/other.py", "x = 4\n",
            "chore: unrelated\n\n"
            "UNFREEZE: src/billing/charge.py - after the fact\n"
            "UNFREEZE-IMPACT: wrong math renders a normal screen\n"
            "UNFREEZE-ROLLBACK: git revert HEAD\n"
            "UNFREEZE-LATE: belongs to the previous commit, the rule was missed",
        )
        r = run_gate(self.repo, "check_frozen.py", "--base", "HEAD~2", "--head", "HEAD")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("late", r.stdout)

    def test_no_manifest_passes_loudly(self):
        (self.repo / "frozen.json").unlink()
        self.commit("src/billing/charge.py", "def charge():\n    return 9\n", "edit anything")
        r = run_gate(self.repo, "check_frozen.py")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("0 frozen entries", r.stdout)

    def test_failure_output_shows_why_it_is_locked(self):
        # The reason lives in frozen.json, which nobody opens. It has to appear
        # at the point where the commit is refused.
        self.commit("src/billing/charge.py", "def charge():\n    return 10\n", "edit frozen path")
        r = run_gate(self.repo, "check_frozen.py")
        self.assertIn("Wrong math still renders a normal screen", r.stdout)
        self.assertIn("Partial refunds live in refund.py", r.stdout)
        self.assertIn("pytest tests/test_billing.py", r.stdout)

    def test_list_mode(self):
        r = run_gate(self.repo, "check_frozen.py", "--list")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("src/billing/charge.py", r.stdout)


class TestGitPolicy(GateTestCase):
    def test_clean_repo_passes(self):
        r = run_gate(self.repo, "check_git_policy.py")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_stray_worktree_is_reported(self):
        wt = self.tmp / "stray"
        git(self.repo, "worktree", "add", "-q", str(wt), "-b", "stray-branch")
        try:
            r = run_gate(self.repo, "check_git_policy.py")
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("worktree", r.stdout.lower())
        finally:
            git(self.repo, "worktree", "remove", "--force", str(wt))

    def test_list_mode(self):
        r = run_gate(self.repo, "check_git_policy.py", "--list")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class TestOutputIsEnglish(unittest.TestCase):
    def test_no_non_ascii_in_gate_sources(self):
        # The gates ship in English. A stray non-ASCII string means a message
        # was missed in translation and will surface at the worst moment.
        for gate in sorted(GATES.glob("*.py")):
            text = gate.read_text(encoding="utf-8")
            bad = [c for c in text if ord(c) > 0x2027]
            self.assertEqual(bad, [], f"{gate.name} has non-ASCII output: {bad[:5]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
