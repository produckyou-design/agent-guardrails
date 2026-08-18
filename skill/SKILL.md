---
name: agent-guardrails
description: "Operating rules for an agent working in a repository that has guardrail gates installed. Use when committing, when reporting on work, when a gate refuses a commit, and when deciding whether something is finished. Covers what the gates check, how to unfreeze a locked path, what counts as verification, and how to report on it honestly."
---

# Working in a guarded repository

This repository runs gates that can refuse your commit. They are not advice.
They read the staged diff and the commit message and they exit non-zero.

Read this before your first commit here.

## What runs on every commit

```
check_frozen.py       edits to paths marked finished
check_git_policy.py   unmerged branches, stray worktrees
```

Run them yourself before committing. A gate that stops you at commit time has
already cost you the context you had ten minutes ago.

## Staging

Name the files you are committing.

```sh
git add src/thing.py tests/test_thing.py     # yes
git add -A                                    # refused
git add -u                                    # refused
```

Other work may be in progress in this tree. "Everything that changed" is not a
set you control.

Never use `git reset --hard`, `git clean`, `git stash`, `git rebase`, or force
push without being asked to. Recovering someone else's uncommitted work is not
possible, and you will not know it was there.

## Frozen paths

`frozen.json` lists code that is finished. Editing it fails the commit.

Before you decide the freeze is in your way, read the entry. It carries
`what_breaks` and `before_you_touch`, and those exist because the failure they
describe already happened once.

Very often the right move is not to unfreeze. If the entry says partial refunds
live in a different file, then your change belongs in that file.

### If you genuinely have to unfreeze

Put three lines in the commit message:

```
UNFREEZE: <path or label> - why this has to change now
UNFREEZE-IMPACT: what breaks, and how, if this is wrong
UNFREEZE-ROLLBACK: how to undo it, with the command if possible
```

Miss one and the commit is refused.

**If you cannot write the impact and the rollback, stop.** That is not a
formatting problem, it is the gate telling you something true. You do not
understand this code well enough to change it yet. Go read `how_to_verify` in
the entry and run it first.

Do not weaken a freeze entry to get past the gate. Do not delete a path from
`frozen.json` as part of a change to that path. Either of those turns the
safeguard back into a note.

## What counts as verification

Running a check counts. Reading code and concluding it should work does not.

- Do not write that you ran something you did not run.
- Do not write that something passed when it failed.
- If you could not run a check, write NOT_RUN and say why. Never write PASS.
- Capture exit codes before any pipe. `cmd | tail` then checking the last exit
  status gives you `tail`'s status, which is almost always zero.

### For anything with a visible result

A green gate is not a working screen. Gates read files, not rendered output.
If your change alters what a user sees, look at it in a browser, at the widths
and in the themes the project supports, before you call it done.

### Added a test?

Break it on purpose once. Revert the fix, confirm the test fails, restore the
fix, confirm it passes. A test you have never seen fail is not evidence that
anything works.

## Before calling something finished

Four questions. Most incomplete work fails one of them.

```
Producer    is the code that creates this data in the main branch
Consumer    is the code that uses it shipped in the same deploy
Wiring      do the config, secrets, and env vars reach it where it runs
Reproduces  does it come back from scratch, or only from a file you made by hand
```

The common failure is a shipped consumer with no producer. The screen works,
because it is reading the last file something wrote before it stopped running.

## Push is not deploy

Pushing puts a commit on the remote. It may not put anything in front of users.
Find out how this project deploys, and confirm from the live response, with a
cache-busting query, before you write that something is live.

## The commit message is the report

Include:

- **What and why.** The reasoning the diff cannot show.
- **What you did not do**, and why. Scope you dropped, checks you skipped.
- **The four completeness questions**, answered.

Whoever reviews this will re-run your checks themselves. Numbers you claim will
be compared against numbers they measure. Claiming a passing result you did not
observe is the fastest way to make everything else you wrote worthless.

## When you get something wrong

If you went in a wrong direction, worked from a false assumption, or changed
approach halfway, add an entry to `FAILURE_MODES.md`:

```
Symptom   what it looked like
Cause     why it happened
Fix       what changed
Rule      what to do from now on
```

Write it even when nothing broke. The test is: **if I do not write this down,
will I do it again?** Skip it if nothing happened. Do not pad the file.

## When you are blocked

Do not guess. Write what is blocked and why, and stop that item. Move to the
next one if there is one.

"I could not verify this" is a report. "This is probably fine" is not.
