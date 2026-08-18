# agent-guardrails

Two gates that refuse a commit when your AI agent edits code that was already
finished. Not documentation. Code that runs and says no.

[한국어](docs/i18n/README.ko.md) | [Español](docs/i18n/README.es.md) | [Português](docs/i18n/README.pt-BR.md) | [中文](docs/i18n/README.zh-CN.md) | [日本語](docs/i18n/README.ja.md) | [Français](docs/i18n/README.fr.md) | [Deutsch](docs/i18n/README.de.md) | [Русский](docs/i18n/README.ru.md)

---

## The thing nobody tells you about AI coding agents

They do not usually break production by writing bad code.

They break it by touching something that was already finished, in a way that
looks completely normal in review, and that no test covers because the code was
working and nobody thought to write one.

Here is what that actually looks like. Every one of these shipped.

**The deploy succeeded. The screen did not change.**
CSS got edited. New HTML went out. Browsers kept using the cached old CSS. The
pipeline was green. The logs were clean. The site was wrong. This is the worst
kind of failure, because the success signal fires.

**The push succeeded. The deploy never ran.**
Commit exists. It is on GitHub. The deploy workflow was manual, so nothing
happened. "Pushed" and "live" got counted as the same event for two days.

**A feature was live, and its code was on no branch.**
The consumer shipped. The producer never did. The screen kept reading a file
that nothing was writing anymore, and served the last good copy until it aged
out.

**The safety rule had been in the docs for six months.**
"Do not touch mobile layout." Written down, agreed on, sitting in the rules file
every agent reads. Nothing enforced it. It was violated constantly, by every
agent, including the ones that had just read the sentence.

That last one is the whole reason this repo exists.

> A rule that nothing reads is not a safeguard. It is a note that looks like one.

## What this is

Two Python files. Standard library only. No model, no API, no service, no
dependencies to install.

```
check_frozen.py       353 lines   lock code that is done
check_git_policy.py   223 lines   find work that got buried
```

They come from one real project where AI agents shipped production code for
months and broke it 60 times. Each break got written down, and the ones that
could become code became these gates. This repo ships the two that generalise,
plus the 27 incidents behind them.

## check_frozen.py, lock code that is done

You mark paths as finished. Editing them fails the commit.

This is the one that changes how agents behave. An agent asked to "fix the
spacing on the invoice page" will happily refactor the tax calculation on its
way there, because the tax code is right next to it and looks improvable. It is
not being careless. It has no way to know that code took three weeks and two
outages to get right.

Now it does.

## check_git_policy.py, find work that got buried

Branches that never merged. Worktrees left checked out. Agents create these
constantly, then move on, and real work sits in them until everyone forgets.

This does not just list branches. It uses patch-equivalence to separate branches
whose content genuinely is not on main from ones that are merely stale
references. In the project this came from, that turned "11 unmerged branches"
into "1 that actually matters."

## The part worth stealing even if you use nothing else

Freezing code is easy. The hard question is how anyone unfreezes it, because the
answer "ask a human" does not survive contact with an agent working at 3am.

Here is what works. To touch a frozen path, the commit message has to carry
three lines:

```
UNFREEZE: src/billing/charge.py - new payment method needs a branch here
UNFREEZE-IMPACT: wrong math still renders a normal screen, only amounts change
UNFREEZE-ROLLBACK: git revert <sha>, then re-run pytest tests/test_billing.py
```

Miss one and the commit is refused.

Why three and not one? A reason only answers "why now." It does not answer what
happens when you are wrong, or how anyone gets back. Those are the two questions
that matter at 3am, and they are exactly the two that get skipped.

The point is not the paperwork. **If you cannot write the impact and the
rollback, you are not ready to unlock it, and you just found that out yourself
instead of finding out in production.** That judgment falls out of the three
lines by itself, which is why it works on agents as well as it works on people.

## What actually gets better

**You stop reviewing everything.**
Your agent made 34 commits overnight. Two of them carry UNFREEZE lines. Those
are the two you read first. The gate did not make the agent more careful. It
made the agent tell you where it stepped off the path.

**"Fix the spacing" stops coming back with 12 changed files.**
You asked for one thing. The diff has that thing, plus a refactor of the tax
code, plus a cleanup of a retry loop that only exists because an upstream API is
flaky. The agent is not being sloppy. It cannot tell which strange code is
strange for a reason. Now the strange code says so, at the moment it gets
touched.

**The load-bearing workaround stops getting improved.**
Every codebase has a line that looks wrong and is holding something up. Somebody
tidies it roughly once a quarter, and it breaks in a way nobody connects to the
tidying. `before_you_touch` is the sign nailed to that fence, and it shows up in
the terminal, not in a file nobody opens.

**You can go to sleep.**
Not because the agent got careful. Because the worst thing it can do while you
are gone is now bounded by a list you wrote while you were awake.

**The rule stops depending on somebody remembering it.**
"Do not touch mobile layout" is advice. A commit that will not go through is
information. The difference is not politeness. One of them works at 3am, on a
model that has never met you, on its first minute in your repository.

## What this does not do

It does not measure how much better anything gets. There is no benchmark table
in this README because there is no honest way to build one, and a made-up table
would be worth less than the two scripts.

It does not scan for secrets or unsafe patterns. gitleaks and semgrep already do
that better than anything shipped here would. This does the thing they do not.

It does not make an agent write better code. It makes a wrong change visible
before it ships. Those are different problems and this only handles the second.

It does not replace review. It removes the class of mistake review is worst at
catching: the small, plausible, adjacent edit to something that was already
correct.

## Install

```sh
git clone https://github.com/produckyou-design/agent-guardrails
./agent-guardrails/install.sh /path/to/your-repo
```

Windows:

```powershell
.\agent-guardrails\install.ps1 C:\path\to\your-repo
```

Or copy the two files into your `scripts/` by hand, drop in the pre-commit hook,
and add `.github/workflows/gates.yml`. Local hooks can be bypassed with
`--no-verify`, the CI job cannot, so run both.

Start with an empty frozen list. Add the first path the day an agent edits
something you thought was finished. You will not have to wait long.

## Writing a freeze entry that holds

A path with no reason gets unlocked by whoever needs it next. What makes a
freeze hold is `what_breaks`, because the person unlocking has to know what they
are risking.

```json
{
  "label": "Billing",
  "paths": ["src/billing/charge.py"],
  "reason": "Finished and in production. Not on any roadmap.",
  "what_breaks": "Wrong math still renders a normal screen. Only the amount changes.",
  "before_you_touch": [
    "Partial refunds live in refund.py, not here.",
    "Failure rolls the whole transaction back. Do not weaken that."
  ],
  "how_to_verify": "pytest tests/test_billing.py -q"
}
```

`before_you_touch` is where the outages go. Every line in it should be something
that was learned the expensive way.

All of it shows up at the moment the commit is refused, which is the only moment
anyone reads it.

## Do not freeze everything

If the freeze covers the whole repo, the gate becomes the boy who cried wolf,
and real violations get ignored along with the noise. Leave the paths your
roadmap is about to touch wide open.

The project this came from freezes 19 paths out of several hundred.

## Tests

```sh
python tests/test_gates.py
```

16 tests. They build a real git repository in a temp directory, make real
commits, and run the gates as subprocesses. Nothing is mocked, because what is
being tested is how the gates read git.

They also cover the bugs that got found the expensive way, including the one
where declaring `src/db/sync-notices.py` silently unlocked `src/db/sync_orders.py`
because a regex ate the hyphen.

A repo that argues verification has to be executable should be able to prove its
own. Weaken the three-line rule and 3 tests fail. Break the hyphen handling and
the path test fails. Try it.

## Also here

`FAILURE_MODES.md` has the 27 incidents these gates came from, in the format
that made them useful:

```
Symptom   what it looked like
Cause     why it happened
Fix       what changed
Rule      what to do from now on
```

One test for whether an incident belongs in that file: **if I do not write this
down, will I do it again?** If yes it goes in, even when nothing broke. The
things that repeat are almost never the dramatic outages. They are the small
loops you walk into every single time.

`skill/SKILL.md` is the agent-facing half, the operating rules that pair with
the gates. Gates catch what can be checked mechanically. The skill covers the
rest, like reporting honestly on verification you actually ran.

## License

MIT. Take what is useful, drop the rest.
