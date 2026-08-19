# agent-guardrails

Asked an AI coding agent to "just fix the spacing" and came back to 12 changed files?

A helper got renamed. A duplicate was "cleaned up." A retry loop that had been stable for months was simplified. The diff looks reasonable. Tests may even pass.

Then something unrelated breaks later.

`agent-guardrails` is a small Git gate for exactly that problem: **AI agents changing code that was already finished and outside the task.**

Instead of asking the model to remember another sentence in a prompt, it makes the rule executable. If a protected path is changed, the commit is refused.

No dependencies. No model API. Just Python and Git.

[한국어](docs/i18n/README.ko.md) | [Español](docs/i18n/README.es.md) | [Português](docs/i18n/README.pt-BR.md) | [中文](docs/i18n/README.zh-CN.md) | [日本語](docs/i18n/README.ja.md) | [Français](docs/i18n/README.fr.md) | [Deutsch](docs/i18n/README.de.md) | [Русский](docs/i18n/README.ru.md)

---

## 30-second test

Give your agent one small task:

```text
Fix the spacing on the settings page.
```

When it finishes:

```sh
git diff --stat
```

If you expected two files and got nine, open the other seven.

You will often find changes like:

```text
"Renamed this for clarity."
"Extracted duplicated logic."
"Removed code that appeared unused."
"Updated adjacent code for consistency."
```

All reasonable. None requested.

If your diffs already contain only what you asked for, you may not need this yet.

If they do not, keep reading.

## The problem this solves

Suppose this file has been boringly correct in production for three months:

```text
src/billing/charge.py
```

Today's task is only:

```text
Adjust invoice page spacing.
```

The agent does not know why `charge.py` looks slightly strange. It does not know which ugly branch exists because of a real outage six months ago. It sees code, not history.

So people write rules like:

```text
Do not touch this file.
```

in `AGENTS.md`, `CLAUDE.md`, prompts, comments, and project docs.

The problem is simple: documentation explains a rule. It does not enforce one.

`agent-guardrails` turns:

```text
please do not touch this
```

into:

```text
commit rejected
```

## How it works

Put finished paths in `frozen.json`:

```json
{
  "frozen": [
    {
      "label": "Billing",
      "paths": ["src/billing/charge.py"],
      "reason": "Finished, in production, and not on the roadmap.",
      "what_breaks": "Wrong math still renders a normal screen. Only the amount changes.",
      "before_you_touch": [
        "Partial refunds live in refund.py, not here.",
        "Failures roll back the entire transaction.",
        "Currency rounding is decided once at the boundary."
      ],
      "how_to_verify": "pytest tests/test_billing.py -q"
    }
  ]
}
```

Install the hook. If an agent changes that path and tries to commit, it gets stopped at the point where the context matters:

```text
$ git commit -m "invoice: tidy up rounding"

frozen: FAIL - a frozen path was changed
  src/billing/charge.py
      [Billing] Finished and in production.
      breaks -> Wrong math still renders a normal screen.
                 Only the amount changes.
        - Partial refunds live in refund.py, not here.
        - Failure rolls the whole transaction back.
        - Currency rounding is decided once at the boundary.
      verify -> pytest tests/test_billing.py -q
```

The gate is local Python. It does not call an LLM.

Normal work passes. The extra context appears only when the agent crosses a boundary.

## If the frozen file really must change

Frozen does not mean immutable forever.

A legitimate change needs three commit-message lines:

```text
UNFREEZE: src/billing/charge.py - new payment method needs a branch here
UNFREEZE-IMPACT: incorrect logic can change charged amounts
UNFREEZE-ROLLBACK: git revert <sha> then rerun pytest tests/test_billing.py
```

Miss one and the commit is refused.

Why three?

Because "why now" is not enough. Before changing proven code, you should also know **what fails if you are wrong** and **how to get back**.

If you cannot state those two things, the useful discovery is that you do not understand the change well enough yet.

## What changes in practice

### Small requests stop turning into giant diffs

```text
Request:
fix button spacing

Unexpected extras:
rename component
refactor API helper
simplify retry loop
merge type definitions
```

Scope drift becomes visible before it lands.

### Weird-looking code keeps its history

Every mature codebase has lines that look wrong but are holding something up.

`before_you_touch` puts the reason next to the failure boundary, exactly when an agent tries to cross it.

### Review gets triaged

If an overnight agent produced 34 commits and two contain `UNFREEZE`, review those two first.

The tool does not make the agent wiser. It makes exceptional changes identify themselves.

### Models can change; the rule stays

Claude today, Codex tomorrow, Gemini next week. The enforcement is in Git, not in model memory.

## Does it save tokens?

The gates themselves use **zero LLM tokens**. They are local Python scripts:

```sh
python scripts/check_frozen.py
python scripts/check_git_policy.py
python scripts/check_scope.py
```

What they can reduce is the expensive part around a bad change:

- unnecessary file exploration
- out-of-scope refactors
- code generation for those refactors
- extra tests
- regression diagnosis
- rollback work
- doing the task again

There is intentionally no "saves 37%" benchmark here. That number would depend on how often your agents drift out of scope.

This is not a token optimizer. It prevents work that never needed to exist.

## Optional task scope

`check_scope.py` can restrict a task to allowed paths.

For example:

```text
Task: settings page spacing

Allowed:
frontend/settings/**
frontend/styles/settings.css

Forbidden:
backend/**
database/**
billing/**
```

Scope is opt-in. No scope file means the check is inactive.

## It also catches abandoned Git work

AI agents create branches and worktrees, then move on.

`check_git_policy.py` does not merely count branches. It uses patch equivalence (`git cherry`) to distinguish work that is genuinely missing from `main` from work already landed through squash or rebase.

In the project this came from, that distinction turned "11 unmerged branches" into "1 branch with work that actually matters."

## Where this came from

This was not designed from a clean-room theory of agent safety.

It came from months of AI agents working on a real production codebase. Production broke 60 times. Each time, the incident was recorded as:

```text
Symptom   what it looked like
Cause     why it happened
Fix       what changed
Rule      what to do next time
```

The rules that could be enforced mechanically became these gates.

The repository includes 28 of those failure records in `FAILURE_MODES.md`.

## Install

Linux / macOS:

```sh
git clone https://github.com/produckyou-design/agent-guardrails
./agent-guardrails/install.sh /path/to/your-repo
```

Windows:

```powershell
git clone https://github.com/produckyou-design/agent-guardrails
.\agent-guardrails\install.ps1 C:\path\to\your-repo
```

Then diagnose the installation:

```sh
python scripts/doctor.py
python scripts/doctor.py --json
```

The local hook can be bypassed with `--no-verify`; CI cannot. Using both is recommended.

## Start empty

Do not freeze the whole repository.

Start with:

```json
{
  "frozen": []
}
```

The first time an agent "helpfully" edits code that was already done, add that path.

A gate that fires constantly becomes noise. Protect only the code that is actually finished and expensive to disturb.

The original project uses a small frozen set out of hundreds of paths.

## Staging discipline

The agent operating rules also reject broad staging habits such as:

```sh
git add -A
git add .
git add -u
```

Prefer naming the files you own:

```sh
git add src/thing.py tests/test_thing.py
```

An agent cannot safely assume every change in a shared working tree belongs to it.

## Verification means execution

`skill/SKILL.md` covers rules that cannot be enforced purely from a diff.

Reading code and saying "this should work" is not verification.

If a command was not run, report `NOT_RUN`. If it failed, report the failure. For visible changes, inspect the actual rendered result before calling the task done.

## Tests

```sh
python tests/test_gates.py
```

There are 16 tests. They create real temporary Git repositories, make real commits, and run the gates as separate processes instead of mocking Git behavior.

Bugs found in the gates themselves are kept as regression tests too.

If a project claims rules should be executable, its own rules should be executable first.

## Included

- `FAILURE_MODES.md` - 28 real failure records that produced these rules.
- `skill/SKILL.md` - operating rules for agents working in a guarded repository.
- `check_frozen.py` - protects finished paths.
- `check_scope.py` - optional task-level path boundaries.
- `check_git_policy.py` - finds meaningful unmerged Git work.
- `check_guardrail_integrity.py` - protects the guardrails themselves.
- `doctor.py` - read-only installation diagnostics.

## What this does not do

It does not scan secrets; use tools such as gitleaks.

It does not detect general dangerous code patterns; use tools such as semgrep.

It does not replace code review.

It does not make an AI agent write better code.

It does one narrower thing:

> It stops plausible, out-of-scope edits to already-correct code from quietly becoming normal commits.

## One-line version

This is not another prompt that says:

```text
Please do not modify existing code unnecessarily.
```

It is what happens after the agent ignores that sentence:

```text
commit rejected
```

## License

MIT. Take what is useful.