#!/usr/bin/env python3
"""Find work that got buried in branches and worktrees.

Two checks. Both of these have broken production for real.

  1  branches whose CONTENT is not on main, past the grace period
  2  worktrees left checked out outside the managed set

What matters is patch equivalence, not commit count. After a squash or rebase a
branch looks ahead of main while its content is already there. Measured on one
real repository, 10 of 11 branches were exactly that. Counting commits fills the
report with 10 harmless entries and buries the 1 that matters.

So this uses `git cherry`. Only lines starting with '+' are genuinely unmerged.

Usage:
    python scripts/check_git_policy.py
    python scripts/check_git_policy.py --list     print config and exit
"""
from __future__ import annotations

import argparse
import datetime as dt
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

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG = BASE_DIR / "git_policy.json"
MAIN_REFS = ("origin/main", "main")


def _git(args: list[str], cwd: Path = BASE_DIR) -> str:
    res = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                         text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {res.stderr.strip()}")
    return res.stdout


def _git_ok(args: list[str], cwd: Path = BASE_DIR) -> bool:
    return subprocess.run(["git", *args], cwd=str(cwd),
                          capture_output=True, text=True).returncode == 0


def load_config() -> dict:
    if not CONFIG.is_file():
        return {}
    try:
        with CONFIG.open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise RuntimeError(f"{CONFIG.name} failed to parse: {e}")


def resolve_main() -> str | None:
    """Prefer origin/main, fall back to main. None means we cannot judge."""
    for ref in MAIN_REFS:
        if _git_ok(["rev-parse", "--verify", f"{ref}^{{commit}}"]):
            return ref
    return None


def exempt_names(config: dict) -> set[str]:
    """Only exceptions with a stated reason count. One without a reason is not an exception."""
    out = set()
    for item in config.get("exempt_branches") or []:
        if isinstance(item, dict) and str(item.get("reason", "")).strip():
            out.add(item["name"])
    return out


def unmerged_branches(main_ref: str, config: dict) -> list[dict]:
    """Return branches whose content is not on main and are past the grace period."""
    grace = int(config.get("unmerged_branch_grace_days", 3))
    skip = exempt_names(config)
    now = dt.datetime.now(dt.timezone.utc)
    found = []

    refs = _git(["for-each-ref", "--format=%(refname:short)",
                 "refs/heads/", "refs/remotes/origin/"]).split()
    seen = set()
    for ref in refs:
        name = ref[len("origin/"):] if ref.startswith("origin/") else ref
        if name in ("main", "HEAD") or name in seen:
            continue
        seen.add(name)
        if name in skip:
            continue

        # Patch equivalence. Anything already merged via squash or rebase drops out here.
        try:
            cherry = _git(["cherry", main_ref, ref])
        except RuntimeError:
            continue
        unmerged = [l for l in cherry.splitlines() if l.startswith("+")]
        if not unmerged:
            continue

        # Docs-only differences cannot break production.
        changed = _git(["diff", "--name-only", f"{main_ref}...{ref}"]).splitlines()
        code = [p for p in changed
                if p.endswith((".py", ".js", ".css", ".html", ".yml", ".yaml"))]
        if not code:
            continue

        stamp = _git(["log", "-1", "--format=%cI", ref]).strip()
        try:
            age = (now - dt.datetime.fromisoformat(stamp)).days
        except ValueError:
            age = 0
        if age < grace:
            continue

        found.append({"branch": name, "commits": len(unmerged),
                      "code_files": len(code), "age_days": age})
    return found


def get_primary_repo_root() -> Path:
    try:
        common = _git(["rev-parse", "--git-common-dir"]).strip()
        common_path = Path(common).resolve()
        if common_path.name == ".git":
            return common_path.parent
    except Exception:
        pass
    return BASE_DIR.resolve()


def stray_worktrees(config: dict) -> list[str]:
    """Unmanaged worktrees. Work done in one never reaches main."""
    managed = tuple(config.get("managed_worktree_prefixes") or [])
    primary_root = get_primary_repo_root()
    out = []
    for line in _git(["worktree", "list", "--porcelain"]).splitlines():
        if not line.startswith("worktree "):
            continue
        path = Path(line[len("worktree "):].strip()).resolve()
        if path == primary_root:
            continue
        try:
            rel = path.relative_to(primary_root).as_posix() + "/"
            if any(rel.startswith(p) for p in managed):
                continue
        except ValueError:
            pass  # outside the repo, so definitely report it
        out.append(str(path))
    return out


def check() -> int:
    config = load_config()
    main_ref = resolve_main()
    if main_ref is None:
        # No basis to judge means no pass. Fail closed.
        print("git-policy: FAIL - cannot find main or origin/main, cannot judge")
        return 1

    problems = []

    stale = unmerged_branches(main_ref, config)
    grace = int(config.get("unmerged_branch_grace_days", 3))
    if stale:
        problems.append("branches whose content is not on main "
                        f"(past the {grace}-day grace period)")
        for b in stale:
            problems.append(f"    {b['branch']}  {b['commits']} unmerged commits, "
                            f"{b['code_files']} code files, {b['age_days']} days old")

    stray = stray_worktrees(config)
    if stray:
        problems.append("unmanaged worktrees are still checked out")
        for p in stray:
            problems.append(f"    {p}")

    if not problems:
        exempt = len(exempt_names(config))
        print(f"git-policy: PASS (against {main_ref}, {exempt} exception(s))")
        return 0

    print("git-policy: FAIL")
    for line in problems:
        print(f"  {line}")
    print()
    print("  A lingering branch is not a tidiness problem. Real unmerged work")
    print("  gets buried in it. Branches that are only stale references do not")
    print("  appear here. What is listed above is genuinely not on main.")
    print()
    print("  Do one of two things.")
    print("      land it     git push origin <branch>:main   (when it fast-forwards)")
    print("      exempt it   add it to exempt_branches in git_policy.json, with a reason")
    print()
    print("  An exception needs a reason. Write down what must NOT be merged from")
    print("  it as well, so the next person does not merge the whole thing.")
    print("")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="print config and exit")
    args = ap.parse_args()

    if args.list:
        config = load_config()
        print(json.dumps({k: v for k, v in config.items()
                          if not k.startswith("_")}, ensure_ascii=False, indent=2))
        return 0
    return check()


if __name__ == "__main__":
    sys.exit(main())
