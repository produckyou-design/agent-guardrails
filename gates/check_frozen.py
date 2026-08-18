#!/usr/bin/env python3
"""Refuse commits that touch finished code.

Protects code that is done and in production, at the source level.
The list lives in `frozen.json`.

Why this exists
---------
When several agents work in one repository, "while I am in here" edits reach
code that was already correct, and production breaks. In the project this
came from, a rule saying not to touch mobile layout sat in the docs for six
months and was violated constantly, because nothing read it. A rule nothing
enforces is not a safeguard.

What it blocks
-------------
A commit whose diff touches a frozen path fails. The freeze protects what
gets computed and fetched, not where things are placed. Keep presentation
files out of the frozen list so cosmetic work stays unblocked.


How to unfreeze
-------
Put three lines in the commit message. An empty reason is refused.

    UNFREEZE: <path or label> - why this has to change now
    UNFREEZE-IMPACT: what breaks, and how, if this is wrong
    UNFREEZE-ROLLBACK: how to undo it, with the command if possible

An unfreeze applies to that one commit only. To unfreeze permanently, remove
the entry from `frozen.json`, which shows up as its own reviewable diff.

Usage
----
    python scripts/check_frozen.py --base <commit> --head <commit>
    python scripts/check_frozen.py            # HEAD~1..HEAD
    python scripts/check_frozen.py --list     # print the frozen list and exit
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
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

BASE_DIR = Path(__file__).resolve().parent.parent
MANIFEST = BASE_DIR / "frozen.json"

# `UNFREEZE: <target> - <reason>`. Separator accepts a hyphen or an em dash.
# The reason cannot be whitespace (min 4 chars). No "why" means no unfreeze.
# The separator has to be a dash surrounded by spaces.
#
# An earlier version excluded hyphens from the target character class to stop
# it swallowing the separator. That also cut hyphens inside paths. Measured:
#
#   UNFREEZE: src/db/sync-notices.py - reason
#       -> target truncated to "src/db/sync"
#       -> matching is `t in path`, so frozen src/db/sync_orders.py unlocks too
#
# Declaring one file and silently unlocking a different one is exactly what
# this gate exists to prevent. Requiring spaces leaves hyphens inside paths
# intact and matches only the separator.
UNFREEZE_RE = re.compile(
    r"^\s*UNFREEZE:\s*(?P<target>\S[^\n]*?)\s+[—–-]{1,2}\s+(?P<reason>\S.{3,})\s*$",
    re.MULTILINE,
)

# A reason alone is not enough. It answers "why now" and says nothing about
# what happens when you are wrong, or how anyone gets back. A freeze protects
# finished work, so whoever unlocks it has to know both.
#
# Requiring all three filters out casual edits by itself. If you cannot write
# the impact and the rollback, you are not ready to unlock it.
IMPACT_RE = re.compile(r"^\s*UNFREEZE-IMPACT:\s*(?P<text>\S.{9,})\s*$", re.MULTILINE)
ROLLBACK_RE = re.compile(r"^\s*UNFREEZE-ROLLBACK:\s*(?P<text>\S.{9,})\s*$", re.MULTILINE)

# Late-declaration marker. A declaration belongs in the commit that actually
# changed the file. This line exists so a missed one is disclosed, not hidden.
LATE_RE = re.compile(r"^\s*UNFREEZE-LATE:\s*(?P<text>\S.{9,})\s*$", re.MULTILINE)


def _git(args: list[str], cwd: Path) -> str:
    res = subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {res.stderr.strip()}")
    return res.stdout


def load_manifest(path: Path = MANIFEST) -> list[dict]:
    if not path.is_file():
        # No manifest means no freeze. Pass, but say so.
        print(f"[frozen] no {path.name}, 0 frozen entries")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("frozen") or []
    for e in entries:
        if not e.get("paths") or not e.get("reason"):
            raise ValueError(f"frozen.json entry is missing paths or reason: {e.get('label')}")
    return entries


def frozen_index(entries: list[dict]) -> dict[str, dict]:
    """Map path to entry. A path is a file or a directory prefix."""
    out: dict[str, dict] = {}
    for e in entries:
        for p in e["paths"]:
            out[p.replace("\\", "/")] = e
    return out


def match_frozen(changed: list[str], index: dict[str, dict]) -> list[tuple[str, dict]]:
    hits = []
    for f in changed:
        f = f.replace("\\", "/")
        for pat, entry in index.items():
            # Exact file, or everything under it when a directory is given.
            if f == pat or (pat.endswith("/") and f.startswith(pat)):
                hits.append((f, entry))
                break
    return hits


def unfreeze_targets(messages: str) -> list[tuple[str, str]]:
    """Expand UNFREEZE declarations into a list of (target, reason).

    Targets can be comma separated. One change genuinely does touch several
    files for the same reason (restoring a producer: sync.py, build.py and
    publish.py were one feature), and listing them with commas is what a
    person writes naturally.

    Rejecting that form gives a FAIL with no explanation. The reason was
    clearly written, the gate still refused, and the gate looks broken. That
    happened once. As long as a reason is attached, listing more paths does
    not weaken the check, since each path is still named explicitly.
    """
    out = []
    matches = list(UNFREEZE_RE.finditer(messages))
    for i, m in enumerate(matches):
        # IMPACT and ROLLBACK for this declaration are searched up to the next
        # UNFREEZE line, so declarations cannot borrow each other's.
        end = matches[i + 1].start() if i + 1 < len(matches) else len(messages)
        block = messages[m.end():end]
        impact = IMPACT_RE.search(block)
        rollback = ROLLBACK_RE.search(block)
        if not (impact and rollback):
            continue  # an incomplete declaration is not a declaration
        reason = m.group("reason").strip()
        for target in m.group("target").split(","):
            target = target.strip()
            if target:
                out.append((target, reason))
    return out


def is_late(messages: str) -> bool:
    """Whether a late-declaration marker is present."""
    return bool(LATE_RE.search(messages))


def declarations_per_commit(base: str, head: str, cwd: Path = BASE_DIR) -> dict:
    """Per commit in range: {sha: (declarations, is_late)}.

    Declarations are read per commit. Pooling them across the range would let

    this work:

        1. edit a frozen file with no declaration
        2. add a later commit containing only declarations
        3. everything is retroactively legal

    A commit of exactly that shape landed once: seven lines of encoding
    changes with a message unfreezing five frozen paths at once. That change
    was legitimate, but it showed the rule could not tell "forgot, wrote it
    later" from "deliberately legalized in bulk".

    The three lines exist to make you think about impact and rollback BEFORE
    unlocking. A late declaration reverses that order, so it is tracked apart.
    """
    out = {}
    log = _git(["log", "--format=%H%x00%B%x1e", f"{base}..{head}"], cwd)
    for chunk in log.split("\x1e"):
        chunk = chunk.strip("\n")
        if not chunk.strip():
            continue
        sha, _, body = chunk.partition("\x00")
        sha = sha.strip()
        if not sha:
            continue
        out[sha] = (unfreeze_targets(body), is_late(body))
    return out


def commits_touching(path: str, base: str, head: str, cwd: Path = BASE_DIR) -> set:
    res = _git(["log", "--format=%H", f"{base}..{head}", "--", path], cwd)
    return {l.strip() for l in res.splitlines() if l.strip()}


def _covers(target: str, path: str, label: str) -> bool:
    return target == path or target == label or bool(target and target in path)


def check(base: str | None, head: str, cwd: Path = BASE_DIR) -> int:
    entries = load_manifest()
    if not entries:
        print("frozen: PASS (nothing frozen)")
        return 0

    index = frozen_index(entries)
    if base is None:
        base = f"{head}~1"

    changed = [l.strip() for l in _git(["diff", "--name-only", base, head], cwd).splitlines() if l.strip()]
    hits = match_frozen(changed, index)
    if not hits:
        print(f"frozen: PASS ({len(index)} frozen paths, {len(changed)} files changed, 0 hits)")
        return 0

    # Read declarations per commit. Pooling across the range would allow one
    # declaration-only commit to legalize everything retroactively.
    per_commit = declarations_per_commit(base, head, cwd)

    unresolved = []
    late_grants = []   # allowed via late declaration: allowed, but always shown
    granted = []
    for path, entry in hits:
        label = entry.get("label", "")
        touching = commits_touching(path, base, head, cwd)

        # 1. normal: the commit that changed the file declared it
        hit = next(((t, why) for sha in touching
                    for (t, why) in per_commit.get(sha, ([], False))[0]
                    if _covers(t, path, label)), None)
        if hit:
            granted.append(hit)
            continue

        # 2. late: declared in another commit, disclosed with UNFREEZE-LATE
        hit = next(((t, why, sha) for sha, (decls, late) in per_commit.items()
                    if late and sha not in touching
                    for (t, why) in decls if _covers(t, path, label)), None)
        if hit:
            late_grants.append((path, hit[1], hit[2]))
            continue

        unresolved.append((path, entry))

    if not unresolved:
        note = f", {len(late_grants)} late" if late_grants else ""
        print(f"frozen: PASS ({len(hits)} hit(s), allowed by UNFREEZE{note})")
        for p, why, sha in late_grants:
            print(f"  late     {p} - {why}  (declared in {sha[:12]}, not the changing commit)")
        for t, why in granted:
            print(f"  unfrozen {t} - {why}")
        return 0

    print("frozen: FAIL - a frozen path was changed")
    seen = set()
    for path, entry in unresolved:
        print(f"  {path}")
        label = entry.get("label")
        if label in seen:
            continue
        seen.add(label)
        print(f"      [{label}] {entry.get('reason')}")
        # Show why it is locked and what to watch for, right where it blocks.
        # Left only inside frozen.json, nobody opens it.
        if entry.get("what_breaks"):
            print(f"      breaks -> {entry['what_breaks']}")
        for note in entry.get("before_you_touch") or []:
            print(f"        - {note}")
        if entry.get("how_to_verify"):
            print(f"      verify -> {entry['how_to_verify']}")
    print()
    if granted:
        # A declaration that does not match is the most confusing case. The
        # reason was written, it still failed, so show what was actually read.
        print("  UNFREEZE declarations read in this range, none matching the paths above:")
        for t, _ in granted:
            print(f"      {t}")
        print()
        print("  A target must equal one of the paths above, be part of it, or be a")
        print("  label from frozen.json. List several with commas.")
        print()
    print("  If this change is genuinely needed, put these three lines in the")
    print("  commit message. Miss one and it does not count as a declaration.")
    print()
    print("      UNFREEZE: <path or label> - why this has to change now")
    print("      UNFREEZE-IMPACT: what breaks, and how, if this is wrong")
    print("      UNFREEZE-ROLLBACK: how to undo it, with the command if possible")
    print()
    print("  List several paths on the first line with commas (a.py, b.py - reason).")
    print()
    print("  The declaration has to be in the commit that actually changed the file.")
    print("  Allowing it anywhere in the range would let someone edit frozen files")
    print("  freely and then legalize it all with one declaration-only commit.")
    print()
    print("  If it is already committed and cannot be amended, disclose it:")
    print("      UNFREEZE-LATE: which commit it belongs to, and why it was missed")
    print("  That passes, but it is printed as 'late' in the PASS output.")
    print()
    print("  Why IMPACT and ROLLBACK are required: a reason only answers 'why now'.")
    print("  It does not say what happens when you are wrong, or how anyone gets")
    print("  back. If you cannot write those two, you are not ready to unlock it.")
    print()
    print("  Example:")
    print("      UNFREEZE: src/billing/charge.py - a new payment method needs a branch")
    print("      UNFREEZE-IMPACT: wrong math still renders a normal screen.")
    print("        Only the amount changes, which makes it hard to notice.")
    print("      UNFREEZE-ROLLBACK: git revert <commit>, then re-run the billing tests.")
    print("        The last known-good build is kept in staging.")
    print()
    print("  If the work can be done next to the locked path instead of inside it,")
    print("  do it there. That side is not frozen.")
    return 1


def _run(args: argparse.Namespace) -> int:
    if args.list:
        for e in load_manifest():
            print(f"[{e['label']}] {e.get('frozen_at', '')}")
            print(f"  reason: {e['reason']}")
            for p in e["paths"]:
                print(f"    - {p}")
        return 0

    try:
        return check(args.base, args.head)
    except Exception as e:  # noqa: BLE001 - a gate fails loudly, with the cause
        print(f"frozen: ERROR — {e!r}", file=sys.stderr)
        return 2


def main() -> int:
    ap = argparse.ArgumentParser(description="Refuse commits that touch finished code.")
    ap.add_argument("--base", default=None, help="base commit to compare against (default: <head>~1)")
    ap.add_argument("--head", default="HEAD", help="commit to check (default: HEAD)")
    ap.add_argument("--list", action="store_true", help="print the frozen list and exit")
    ap.add_argument("--json", action="store_true", help="emit one machine-readable JSON result")
    args = ap.parse_args()

    if not args.json:
        return _run(args)

    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = _run(args)
    print(json.dumps({
        "gate": "frozen",
        "status": "PASS" if code == 0 else "FAIL",
        "exit_code": code,
        "output": stdout.getvalue(),
        "error": stderr.getvalue(),
    }, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
