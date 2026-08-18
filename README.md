# agent-guardrails

A tool that refuses a commit when your AI coding agent edits code that was
already finished. It is two Python files with no dependencies to install.

[한국어](docs/i18n/README.ko.md) | [Español](docs/i18n/README.es.md) | [Português](docs/i18n/README.pt-BR.md) | [中文](docs/i18n/README.zh-CN.md) | [日本語](docs/i18n/README.ja.md) | [Français](docs/i18n/README.fr.md) | [Deutsch](docs/i18n/README.de.md) | [Русский](docs/i18n/README.ru.md)

---

## What problem this solves

When you hand code to an AI agent, the trouble usually does not come from the
new code it writes. It comes from the code it touches on the way.

Say you ask it to fix the spacing on the invoice page. It will often tidy up the
tax calculation sitting right next to it as well. This is not carelessness. The
agent has no way of knowing why that code looks the way it does, or what it took
to get there. And a change like that does not look wrong in review. There is no
test covering it either, because the code was working and nobody thought to
write one.

You can write "do not touch this file" in your project documentation. It does
not hold. In the project this came from, that rule sat in the docs for six
months and was broken constantly, including by agents that had just read the
sentence, because no code ever checked it.

This tool turns that rule into **something that actually runs**.

## How it works

You list the finished paths in `frozen.json`.

```json
{
  "frozen": [
    {
      "label": "Billing",
      "paths": ["src/billing/charge.py"],
      "reason": "Finished and running in production. Not on any roadmap.",
      "what_breaks": "Wrong math still renders a normal screen. Only the amount changes.",
      "before_you_touch": [
        "Partial refunds are handled in refund.py, not here.",
        "A failure rolls the whole transaction back. Do not weaken that."
      ],
      "how_to_verify": "pytest tests/test_billing.py -q"
    }
  ]
}
```

Then you install the pre-commit hook, and any commit that edits those paths is
refused. When that happens, everything you wrote above is printed in the
terminal: why it is locked, what breaks if you get it wrong, and what you need to
know before touching it. It appears **at the moment someone is blocked**, rather
than sitting in a file nobody opens.

### If you genuinely need to change it

Put three lines in the commit message.

```
UNFREEZE: src/billing/charge.py - the new payment method needs a branch here
UNFREEZE-IMPACT: wrong math still renders a normal screen, only the amount changes
UNFREEZE-ROLLBACK: git revert <sha>, then re-run pytest tests/test_billing.py
```

If any of the three is missing, the commit is refused.

Why three lines instead of one? Because a reason only answers "why change this
now." It does not say what happens if you are wrong, or how anyone gets back to
where they were. Those two are what actually matter, and those two are exactly
what gets left out.

**If you cannot write the impact and the rollback, you are not ready to change
that code yet.** And you find that out now instead of finding it out in
production. The point is not to make you fill in a form. It is that the judgment
comes out of writing the three lines.

## What gets better

**You stop reading every commit.** Say your agent made 34 commits overnight. Two
of them carry UNFREEZE lines. Those are the two you read first. The agent did
not become more careful; it now marks where it went outside the scope you gave
it.

**"Fix the spacing" stops coming back as twelve changed files.** You asked for
one thing, and the diff also contains a refactor of the tax calculation and a
cleanup of a retry loop that only exists because an upstream API is unreliable.
That happens less.

**The load-bearing workaround stops getting tidied up.** Every codebase has a
line that looks wrong but is holding something together. Every few months
somebody cleans it up, and later something breaks in a way nobody connects back
to the cleanup. `before_you_touch` is the warning sign posted at that spot.

**The rule no longer depends on somebody remembering it.** "Do not touch mobile
layout" is advice. A commit that will not go through is information. The second
one works at 3am, with a model that has never seen you, in its first minute in
your repository.

## The second tool

`check_git_policy.py` finds unmerged branches and worktrees that were left
checked out.

A lingering branch is not the problem in itself. The problem is that **real
unmerged work gets buried in it**. Agents create branches and worktrees and then
move on to the next task, so these pile up.

It does not simply list branches. It uses patch equivalence (`git cherry`) to
tell branches whose content genuinely is not on main apart from branches that
were already merged through a squash or a rebase. In the project this came from,
that distinction turned "11 unmerged branches" into "1 that actually matters."

## Where this came from

It came out of a real project where AI agents wrote production code for months.
Along the way the live site broke 60 times. Each time, what happened and what to
do differently got written down, and the rules that could be turned into code
became these gates.

This repository ships the two that apply outside that project, along with the 28
incidents behind them. Those are in `FAILURE_MODES.md`.

## Install

```sh
git clone https://github.com/produckyou-design/agent-guardrails
./agent-guardrails/install.sh /path/to/your-repo
```

Windows:

```powershell
.\agent-guardrails\install.ps1 C:\path\to\your-repo
```

To do it by hand, copy `gates/*.py` into your project's `scripts/`, put
`hooks/pre-commit` in `.git/hooks/`, and copy `examples/workflow.yml` into
`.github/workflows/`.

A local hook can be skipped with `--no-verify`, but the CI job cannot. It is
worth having both.

**Start with an empty frozen list.** Add the first path on the day an agent edits
a file you thought was finished.

## Do not freeze everything

If the freeze covers the whole repository, the gate goes off constantly, and
then real violations get ignored along with the noise. Leave the paths you are
about to work on open.

The project this came from keeps 19 paths frozen out of several hundred.

## What this tool does not do

**It does not measure how much anything improves.** There is no benchmark table
in this README because there is no honest way to produce one.

**It does not scan for secrets or unsafe code patterns.** gitleaks and semgrep
do that far better. This tool covers a problem they do not.

**It does not make the agent write better code.** It only makes a wrong change
visible before it ships.

**It does not replace code review.** It filters out the one thing review is
worst at catching: a small, plausible edit to code that was already correct.

## Tests

```sh
python tests/test_gates.py
```

There are 16. They create a real git repository in a temporary directory, make
real commits, and run the gates as separate processes. Nothing is mocked,
because what is being tested is how the gates read git.

Bugs that were learned the expensive way are in there too. For example,
declaring `src/db/sync-notices.py` used to silently unlock
`src/db/sync_orders.py`, because a regular expression was eating the hyphen.

A repository arguing that verification has to be executable should be able to
demonstrate its own. Loosen the three-line rule and 3 tests fail. Break the
hyphen handling and the path test fails. Try it yourself.

## What else is here

**`FAILURE_MODES.md`** contains the 28 incidents these gates came from. Each one
is four lines.

```
Symptom   what it looked like
Cause     why it happened
Fix       what changed
Rule      what to do from now on
```

There is one test for whether something belongs in that file: **if I do not
write this down, will I do it again?** If the answer is yes, it goes in, even
when nothing broke. What repeats is rarely a dramatic outage. It is the same
small thing you trip over every time.

**`skill/SKILL.md`** holds the operating rules an agent reads. The gates only
catch what can be checked mechanically. This covers the rest, such as reporting
only the verification you actually ran.

## License

MIT. Take whatever is useful.
