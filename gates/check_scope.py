#!/usr/bin/env python3
"""Refuse commits that leave the declared task scope.

The scope gate is opt-in. Create `.agent-guardrails/scope.json` (or pass
`--scope`) for a contained task. The pre-commit hook checks the staged diff;
CI can check a commit range with `--base` and `--head`.
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
DEFAULT_SCOPE = ROOT / ".agent-guardrails" / "scope.json"


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


def _changed_paths(*, staged: bool, base: str | None, head: str) -> list[str]:
    args = ["diff", "--name-status", "-z", "--diff-filter=ACDMRTUXB"]
    if staged:
        args.append("--cached")
    else:
        if not base:
            raise ValueError("--base is required when checking a commit range")
        args.append(f"{base}..{head}")
    tokens = _git(args).split("\0")
    paths: list[str] = []
    index = 0
    while index < len(tokens):
        status = tokens[index]
        index += 1
        if not status:
            continue
        count = 2 if status[0] in {"R", "C"} else 1
        for path in tokens[index:index + count]:
            if path:
                paths.append(_normalise(path))
        index += count
    return sorted(set(paths))


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


def _string_list(value: object, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{field} must be a list of non-empty strings")
    return [_normalise(item) for item in value]


def _load_scope(path: Path) -> dict[str, list[str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"scope file could not be read: {type(exc).__name__}") from exc
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("scope file must be an object with version=1")
    allowed = _string_list(data.get("allowed_paths"), "allowed_paths")
    forbidden = _string_list(data.get("forbidden_paths"), "forbidden_paths")
    ignored = _string_list(data.get("ignored_paths"), "ignored_paths")
    if not allowed and not forbidden:
        raise ValueError("scope file needs allowed_paths or forbidden_paths")
    return {"allowed_paths": allowed, "forbidden_paths": forbidden, "ignored_paths": ignored}


def evaluate(
    scope_path: Path,
    *,
    staged: bool,
    base: str | None,
    head: str,
) -> tuple[int, dict[str, object], str]:
    if not scope_path.is_file():
        detail = "scope: INACTIVE - no scope file; pass --scope or create .agent-guardrails/scope.json"
        return 0, {"status": "INACTIVE", "scope_file": str(scope_path), "changed_paths": []}, detail

    scope = _load_scope(scope_path)
    changed = _changed_paths(staged=staged, base=base, head=head)
    ignored = set(scope["ignored_paths"])
    scope_name = _normalise(str(scope_path.relative_to(ROOT))) if scope_path.is_relative_to(ROOT) else str(scope_path)
    ignored.add(scope_name)
    considered = [path for path in changed if not _matches(path, list(ignored))]
    forbidden = [path for path in considered if _matches(path, scope["forbidden_paths"])]
    outside = [
        path for path in considered
        if scope["allowed_paths"] and not _matches(path, scope["allowed_paths"])
    ]
    violations = sorted(set(forbidden + outside))
    status = "FAIL" if violations else "PASS"
    result = {
        "status": status,
        "scope_file": str(scope_path),
        "staged": staged,
        "base": base,
        "head": head,
        "changed_paths": changed,
        "ignored_paths": sorted(set(changed) - set(considered)),
        "forbidden_paths": forbidden,
        "outside_allowed_paths": outside,
        "violations": violations,
    }
    if violations:
        detail = "scope: FAIL - changed paths outside the declared task scope\n" + "\n".join(
            f"  {path}" for path in violations
        )
    else:
        detail = f"scope: PASS ({len(considered)} in-scope path(s), {len(changed)} changed path(s))"
    return 1 if violations else 0, result, detail


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scope",
        type=Path,
        default=Path(os.environ.get("AGENT_GUARDRAILS_SCOPE") or DEFAULT_SCOPE),
        help="scope JSON path (default: AGENT_GUARDRAILS_SCOPE or .agent-guardrails/scope.json)",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--staged", action="store_true", help="check the staged diff (default)")
    source.add_argument("--base", help="base commit for a commit-range check")
    parser.add_argument("--head", default="HEAD", help="head commit for a commit-range check")
    parser.add_argument("--json", action="store_true", help="emit one machine-readable JSON result")
    args = parser.parse_args()

    scope_path = args.scope.expanduser()
    if not scope_path.is_absolute():
        scope_path = (ROOT / scope_path).resolve()
    staged = not bool(args.base)
    try:
        code, result, detail = evaluate(
            scope_path,
            staged=staged,
            base=args.base,
            head=args.head,
        )
    except Exception as exc:  # noqa: BLE001 - a guard must fail loudly
        code = 2
        result = {"status": "ERROR", "scope_file": str(scope_path), "error": str(exc)}
        detail = f"scope: ERROR - {exc}"

    if args.json:
        print(json.dumps({"gate": "scope", **result, "exit_code": code}, ensure_ascii=False))
    else:
        print(detail)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
