"""Tests for the optional scope, integrity, configuration, and doctor gates."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
GATES = ROOT / "gates"


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def run_gate(repo: Path, name: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(repo / "scripts" / name), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


class RepoCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="guardrails-additional-"))
        self.repo = self.tmp / "repo"
        (self.repo / "scripts").mkdir(parents=True)
        for gate in GATES.glob("*.py"):
            shutil.copy(gate, self.repo / "scripts" / gate.name)
        git(self.repo, "init", "-q")
        git(self.repo, "symbolic-ref", "HEAD", "refs/heads/main")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "test")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def commit_all(self, message: str, *, no_verify: bool = False) -> None:
        result = git(self.repo, "add", "-A")
        self.assertEqual(result.returncode, 0, result.stderr)
        args = ["commit", "-q"]
        if no_verify:
            args.append("--no-verify")
        result = git(self.repo, *args, "-m", message)
        self.assertEqual(result.returncode, 0, result.stderr)


class TestScopeGate(RepoCase):
    def configure_scope(self) -> None:
        write(
            self.repo / ".agent-guardrails" / "scope.json",
            json.dumps({
                "version": 1,
                "allowed_paths": ["src/allowed.py", "tests/**"],
                "forbidden_paths": ["src/locked/**"],
            }),
        )
        write(self.repo / "src" / "allowed.py", "value = 1\n")
        write(self.repo / "src" / "locked" / "finished.py", "value = 1\n")
        write(self.repo / "tests" / "test_allowed.py", "assert True\n")
        self.commit_all("initial scope")

    def test_scope_blocks_outside_and_forbidden_paths(self):
        self.configure_scope()
        write(self.repo / "src" / "allowed.py", "value = 2\n")
        write(self.repo / "src" / "locked" / "finished.py", "value = 2\n")
        write(self.repo / "src" / "unrelated.py", "value = 2\n")
        git(self.repo, "add", "-A")

        result = run_gate(self.repo, "check_scope.py")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("src/locked/finished.py", result.stdout)
        self.assertIn("src/unrelated.py", result.stdout)

    def test_scope_can_emit_json_and_pass(self):
        self.configure_scope()
        write(self.repo / "src" / "allowed.py", "value = 2\n")
        git(self.repo, "add", "src/allowed.py")

        result = run_gate(self.repo, "check_scope.py", "--json")
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(payload["gate"], "scope")
        self.assertEqual(payload["status"], "PASS")

    def test_scope_is_optional_when_no_file_exists(self):
        write(self.repo / "src" / "anything.py", "value = 1\n")
        self.commit_all("initial")
        write(self.repo / "src" / "anything.py", "value = 2\n")
        git(self.repo, "add", "src/anything.py")

        result = run_gate(self.repo, "check_scope.py")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("INACTIVE", result.stdout)


class TestGuardrailIntegrity(RepoCase):
    def configure_policy(self) -> None:
        write(
            self.repo / "guardrail_policy.json",
            json.dumps({
                "version": 1,
                "protected_paths": ["scripts/check_frozen.py", "guardrail_policy.json"],
            }),
        )
        write(self.repo / "scripts" / "check_frozen.py", "print('stable')\n")
        write(self.repo / "src" / "other.py", "value = 1\n")
        self.commit_all("initial guardrails")

    def test_protected_change_requires_all_markers(self):
        self.configure_policy()
        write(self.repo / "scripts" / "check_frozen.py", "print('changed')\n")
        git(self.repo, "add", "scripts/check_frozen.py")
        message = self.tmp / "message.txt"
        write(message, "change guardrail\n")

        result = run_gate(self.repo, "check_guardrail_integrity.py", "--message-file", str(message))

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("GUARDRAIL-IMPACT", result.stdout)

    def test_protected_change_passes_with_all_markers(self):
        self.configure_policy()
        write(self.repo / "scripts" / "check_frozen.py", "print('changed')\n")
        git(self.repo, "add", "scripts/check_frozen.py")
        message = self.tmp / "message.txt"
        write(
            message,
            "guardrail: improve matching\n\n"
            "GUARDRAIL-CHANGE: support an additional path form\n"
            "GUARDRAIL-IMPACT: a wrong match could permit an unreviewed edit\n"
            "GUARDRAIL-VERIFY: run the complete gate test suite\n",
        )

        result = run_gate(self.repo, "check_guardrail_integrity.py", "--message-file", str(message))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_markers_below_scissors_line_do_not_count(self):
        # With `git commit -v` the message file holds the verbose diff below
        # the scissors line. A diff context line carrying GUARDRAIL text used
        # to be read as a declaration, so committing a file that merely
        # contains the marker strings would satisfy this gate.
        self.configure_policy()
        write(self.repo / "guardrail_policy.json", json.dumps({
            "version": 1,
            "protected_paths": ["scripts/check_frozen.py", "guardrail_policy.json"],
            "_markers_note": "GUARDRAIL-CHANGE GUARDRAIL-IMPACT GUARDRAIL-VERIFY",
        }))
        git(self.repo, "add", "guardrail_policy.json")
        message = self.tmp / "message.txt"
        write(
            message,
            "policy: note the marker names\n\n"
            "# ------------------------ >8 ------------------------\n"
            " GUARDRAIL-CHANGE: a context line from the verbose diff\n"
            " GUARDRAIL-IMPACT: a context line from the verbose diff\n"
            " GUARDRAIL-VERIFY: a context line from the verbose diff\n",
        )

        result = run_gate(self.repo, "check_guardrail_integrity.py", "--message-file", str(message))

        self.assertEqual(result.returncode, 1,
                         "markers below the scissors line must not count\n"
                         + result.stdout + result.stderr)

    def test_later_markers_do_not_backdate_guardrail_change(self):
        self.configure_policy()
        write(self.repo / "scripts" / "check_frozen.py", "print('changed')\n")
        self.commit_all("unacknowledged guardrail change")
        write(self.repo / "src" / "other.py", "value = 2\n")
        self.commit_all(
            "unrelated follow-up\n\n"
            "GUARDRAIL-CHANGE: after the fact\n"
            "GUARDRAIL-IMPACT: protection may be weakened\n"
            "GUARDRAIL-VERIFY: run tests\n",
        )

        result = run_gate(self.repo, "check_guardrail_integrity.py", "--base", "HEAD~2", "--head", "HEAD")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)


class TestGitPolicyConfiguration(RepoCase):
    def test_configured_branch_and_language_are_used(self):
        write(self.repo / "git_policy.json", json.dumps({
            "main_refs": ["main"],
            "code_extensions": [".rs"],
            "unmerged_branch_grace_days": 0,
            "exempt_branches": [],
            "managed_worktree_prefixes": [],
        }))
        write(self.repo / "README.md", "initial\n")
        self.commit_all("initial")
        git(self.repo, "checkout", "-q", "-b", "feature")
        write(self.repo / "src" / "main.rs", "fn main() {}\n")
        self.commit_all("rust change")

        result = run_gate(self.repo, "check_git_policy.py")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("feature", result.stdout)


class TestDoctor(RepoCase):
    def test_doctor_reports_installed_target(self):
        write(self.repo / "frozen.json", json.dumps({"version": 1, "frozen": []}))
        write(self.repo / "git_policy.json", json.dumps({}))
        write(self.repo / "guardrail_policy.json", json.dumps({"version": 1, "protected_paths": ["scripts/**"]}))
        hooks = self.repo / ".git" / "hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        write(hooks / "pre-commit", "#!/bin/sh\ncheck_frozen.py check_git_policy.py check_scope.py\n")
        write(hooks / "commit-msg", "#!/bin/sh\ncheck_frozen.py check_guardrail_integrity.py\n")
        self.commit_all("installed", no_verify=True)

        result = run_gate(self.repo, "doctor.py", "--json")
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(payload["status"], "PASS")
        self.assertTrue(any(item["status"] == "INFO" for item in payload["checks"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
