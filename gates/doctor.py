#!/usr/bin/env python3
"""Read-only installation and configuration diagnostic for agent-guardrails."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


REQUIRED_GATES = (
    "check_frozen.py",
    "check_git_policy.py",
    "check_scope.py",
    "check_guardrail_integrity.py",
)
REQUIRED_CONFIGS = ("frozen.json", "git_policy.json", "guardrail_policy.json")
DEFAULT_REPO = Path(__file__).resolve().parents[1]


def _git_hooks(repo: Path) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--git-path", "hooks"],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode == 0:
        value = Path(result.stdout.strip())
        return value if value.is_absolute() else (repo / value).resolve()
    return repo / ".git" / "hooks"


def _check_json(path: Path, *, required_keys: tuple[str, ...]) -> tuple[str, str]:
    if not path.is_file():
        return "FAIL", f"missing {path.name}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return "FAIL", f"invalid {path.name}: {type(exc).__name__}"
    missing = [key for key in required_keys if key not in data]
    if missing:
        return "FAIL", f"{path.name} missing: {', '.join(missing)}"
    return "PASS", f"{path.name} is valid"


def inspect_repo(repo: Path) -> dict[str, object]:
    repo = repo.resolve()
    script_dir = repo / "scripts" if (repo / "scripts" / "check_frozen.py").is_file() else repo / "gates"
    checks: list[dict[str, str]] = []

    for name in REQUIRED_GATES:
        path = script_dir / name
        checks.append({
            "name": f"gate:{name}",
            "status": "PASS" if path.is_file() else "FAIL",
            "detail": str(path),
        })

    for name in REQUIRED_CONFIGS:
        required = {
            "frozen.json": ("version", "frozen"),
            "git_policy.json": (),
            "guardrail_policy.json": ("version", "protected_paths"),
        }[name]
        status, detail = _check_json(repo / name, required_keys=required)
        if status == "PASS" and name == "guardrail_policy.json":
            try:
                policy = json.loads((repo / name).read_text(encoding="utf-8"))
                if not isinstance(policy.get("protected_paths"), list) or not policy["protected_paths"]:
                    status, detail = "FAIL", "guardrail_policy.json protected_paths is empty"
            except (OSError, json.JSONDecodeError, AttributeError):
                status, detail = "FAIL", "guardrail_policy.json is not an object"
        checks.append({"name": f"config:{name}", "status": status, "detail": detail})

    hooks = _git_hooks(repo)
    for name, required_text in (
        ("pre-commit", ("check_frozen.py", "check_git_policy.py", "check_scope.py")),
        ("commit-msg", ("check_guardrail_integrity.py",)),
    ):
        path = hooks / name
        if not path.is_file():
            checks.append({"name": f"hook:{name}", "status": "FAIL", "detail": f"missing {path}"})
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        missing = [needle for needle in required_text if needle not in text]
        checks.append({
            "name": f"hook:{name}",
            "status": "PASS" if not missing else "FAIL",
            "detail": str(path) if not missing else f"missing: {', '.join(missing)}",
        })

    scope = repo / ".agent-guardrails" / "scope.json"
    if scope.is_file():
        status, detail = _check_json(scope, required_keys=("version",))
        checks.append({"name": "scope", "status": status, "detail": detail})
    else:
        checks.append({
            "name": "scope",
            "status": "INFO",
            "detail": "no active scope file; scope gate is opt-in",
        })

    workflows = list((repo / ".github" / "workflows").glob("*.y*ml")) if (repo / ".github" / "workflows").is_dir() else []
    has_integrity_ci = any(
        "check_guardrail_integrity.py" in path.read_text(encoding="utf-8", errors="replace")
        for path in workflows
    )
    checks.append({
        "name": "ci:guardrail-integrity",
        "status": "PASS" if has_integrity_ci else "INFO",
        "detail": "workflow found" if has_integrity_ci else "no workflow found; local hooks still protect commits",
    })

    status = "FAIL" if any(check["status"] == "FAIL" for check in checks) else "PASS"
    return {"doctor": "agent-guardrails", "status": status, "repo": str(repo), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO, help="installed repository path (default: repository containing this script)")
    parser.add_argument("--json", action="store_true", help="emit one machine-readable JSON result")
    args = parser.parse_args()
    try:
        result = inspect_repo(args.repo)
    except Exception as exc:  # noqa: BLE001 - diagnostics must explain failures
        result = {"doctor": "agent-guardrails", "status": "ERROR", "error": str(exc)}
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"doctor: {result['status']}")
        for check in result.get("checks", []):
            print(f"[{check['status']}] {check['name']}: {check['detail']}")
        if result.get("error"):
            print(f"[ERROR] {result['error']}", file=sys.stderr)
    return 1 if result["status"] in {"FAIL", "ERROR"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
