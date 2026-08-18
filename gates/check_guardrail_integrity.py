#!/usr/bin/env python3
"""Require explicit evidence when the guardrails themselves change.

This gate protects the policy, gates, hooks, and installer paths that make the
other gates trustworthy. A protected-path change needs all three lines in the
same commit message:

    GUARDRAIL-CHANGE: why the guardrail must change now
    GUARDRAIL-IMPACT: what protection is lost if this is wrong
    GUARDRAIL-VERIFY: how the new guardrail was tested
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "guardrail_policy.json"
DEFAULT_PROTECTED_PATHS = (
    "frozen.json",
    "git_policy.json",
    "guardrail_policy.json",
    "gates/**",
    "scripts/check_frozen.py",
    "scripts/check_git_policy.py",
    "scripts/check_scope.py",
    "scripts/check_guardrail_integrity.py",
    "hooks/**",
    "install.sh",
    "install.ps1",
    "examples/guardrail_policy.json",
    "examples/workflow.yml",
)
MARKERS = (
    "GUARDRAIL-CHANGE",
    "GUARDRAIL-IMPACT",
    "GUARDRAIL-VERIFY",
)


def _git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def _normalise(path: str) -> str:
    value = path.replace("\\", "/").strip()
    while value.startswith("./"):
        value = value[2:]
    return value


def _pattern_regex(pattern: str) -> re.Pattern[str]:
    pattern = _normalise(pattern)
    pieces: list[str] = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            pieces.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            pieces.append(".*")
            index += 2
        elif pattern[index] == "*":
            pieces.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            pieces.append("[^/]")
            index += 1
        else:
            pieces.append(re.escape(pattern[index]))
            index += 1
    return re.compile(r"^" + "".join(pieces) + r"$")


def _matches(path: str, patterns: list[str]) -> bool:
    return any(_pattern_regex(pattern).match(path) for pattern in patterns)


def _parse_name_status(raw: str) -> list[str]:
    tokens = raw.split("\0")
    paths: list[str] = []
    index = 0
    while index < len(tokens):
        status = tokens[index]
        index += 1
        if not status:
            continue
        count = 2 if status[0] in {"R", "C"} else 1
        paths.extend(_normalise(path) for path in tokens[index:index + count] if path)
        index += count
    return sorted(set(paths))


def _changed_paths(*, staged: bool, base: str | None, head: str) -> list[str]:
    args = ["diff", "--name-status", "-z", "--diff-filter=ACDMRTUXB"]
    if staged:
        args.append("--cached")
    else:
        if not base:
            raise ValueError("--base is required for a commit-range check")
        args.append(f"{base}..{head}")
    return _parse_name_status(_git(args))


def _commits(base: str, head: str) -> list[tuple[str, str, list[str]]]:
    commits = [line.strip() for line in _git(["rev-list", "--reverse", f"{base}..{head}"]).splitlines() if line.strip()]
    result: list[tuple[str, str, list[str]]] = []
    for sha in commits:
        message = _git(["show", "-s", "--format=%B", sha])
        raw_paths = _git(["diff-tree", "--root", "--no-commit-id", "--name-status", "-r", "-z", sha])
        result.append((sha, message, _parse_name_status(raw_paths)))
    return result


def _load_policy(ref: str | None) -> list[str]:
    text: str | None = None
    if ref:
        try:
            text = _git(["show", f"{ref}:guardrail_policy.json"])
        except RuntimeError:
            # A repository upgrading from an older install has no baseline
            # policy yet. Use the conservative built-in list; never use a
            # newly edited working-tree policy as the baseline.
            return list(DEFAULT_PROTECTED_PATHS)
    if text is None:
        if CONFIG.is_file():
            text = CONFIG.read_text(encoding="utf-8")
        else:
            return list(DEFAULT_PROTECTED_PATHS)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"guardrail_policy.json is invalid: {exc}") from exc
    paths = data.get("protected_paths") if isinstance(data, dict) else None
    if not isinstance(paths, list) or not all(isinstance(path, str) and path.strip() for path in paths):
        raise ValueError("guardrail_policy.json protected_paths must be a list of strings")
    if not paths:
        raise ValueError("guardrail_policy.json protected_paths must not be empty")
    return [_normalise(path) for path in paths]


def _missing_markers(message: str) -> list[str]:
    return [
        marker for marker in MARKERS
        if not re.search(rf"^\s*{re.escape(marker)}:\s*\S.{{3,}}\s*$", message, re.MULTILINE)
    ]


def evaluate(
    *,
    staged: bool,
    base: str | None,
    head: str,
    message_file: Path | None,
) -> tuple[int, dict[str, object], str]:
    policy_ref = "HEAD" if staged else base
    protected = _load_policy(policy_ref)
    findings: list[dict[str, object]] = []

    if staged:
        changed = _changed_paths(staged=True, base=None, head=head)
        hits = [path for path in changed if _matches(path, protected)]
        if hits:
            if message_file is None:
                missing = list(MARKERS)
            else:
                try:
                    message = message_file.read_text(encoding="utf-8")
                except OSError as exc:
                    raise ValueError(f"commit message could not be read: {type(exc).__name__}") from exc
                missing = _missing_markers(message)
            if missing:
                findings.append({
                    "commit": "INDEX",
                    "paths": hits,
                    "missing_markers": missing,
                })
    else:
        if not base:
            raise ValueError("--base is required for a commit-range check")
        for sha, message, changed in _commits(base, head):
            hits = [path for path in changed if _matches(path, protected)]
            if hits:
                missing = _missing_markers(message)
                if missing:
                    findings.append({
                        "commit": sha,
                        "paths": hits,
                        "missing_markers": missing,
                    })

    status = "FAIL" if findings else "PASS"
    result = {
        "status": status,
        "staged": staged,
        "base": base,
        "head": head,
        "protected_paths": protected,
        "findings": findings,
    }
    if findings:
        lines = ["guardrail: FAIL - protected guardrail paths changed without complete markers"]
        for finding in findings:
            lines.append(f"  {finding['commit']}: {', '.join(finding['paths'])}")
            lines.append(f"    missing: {', '.join(finding['missing_markers'])}")
        lines.append("  Required: GUARDRAIL-CHANGE, GUARDRAIL-IMPACT, GUARDRAIL-VERIFY")
        detail = "\n".join(lines)
    else:
        detail = "guardrail: PASS (no unacknowledged protected-path changes)"
    return 1 if findings else 0, result, detail


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--message-file", type=Path, help="commit message file from the commit-msg hook")
    source.add_argument("--base", help="base commit for a commit-range check")
    source.add_argument("--staged", action="store_true", help="check the staged diff without a message file")
    parser.add_argument("--head", default="HEAD", help="head commit for a commit-range check")
    parser.add_argument("--json", action="store_true", help="emit one machine-readable JSON result")
    args = parser.parse_args()

    staged = args.message_file is not None or args.staged or args.base is None
    try:
        code, result, detail = evaluate(
            staged=staged,
            base=args.base,
            head=args.head,
            message_file=args.message_file.expanduser() if args.message_file else None,
        )
    except Exception as exc:  # noqa: BLE001 - a guard must fail loudly
        code = 2
        result = {"status": "ERROR", "error": str(exc)}
        detail = f"guardrail: ERROR - {exc}"

    if args.json:
        print(json.dumps({"gate": "guardrail-integrity", **result, "exit_code": code}, ensure_ascii=False))
    else:
        print(detail)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
