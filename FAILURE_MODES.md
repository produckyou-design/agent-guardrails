# Failure modes

Incidents that produced the gates in this repo, rewritten so they apply outside
the project they came from.

The format is four lines, and the fourth is the only one that matters later:

```
Symptom   what it looked like
Cause     why it happened
Fix       what changed
Rule      what to do from now on
```

One test for whether something belongs here: **if I do not write this down, will
I do it again?** If yes it goes in, even when nothing broke. The entries that
earn their keep are almost never the dramatic outages. They are the small loops
you walk into every single time.

---

## 1. The deploy succeeded and users saw nothing

**Symptom** CSS and JS changes shipped. The pipeline was green. Every user kept
seeing the old design, for hours.

**Cause** New HTML went out referencing asset URLs that had not changed, so
browsers and CDNs kept serving cached copies of the old files.

**Fix** A gate that fails the commit when CSS or JS changed but the asset
version stamp did not.

**Rule** Any cached artifact needs a version in its URL, and the step that
bumps it belongs in the gates, not in a checklist. This is the worst class of
bug because the success signal fires. Nothing tells you.

## 2. Local state got reported as live

**Symptom** A report said a feature was working. It was working on the machine
that wrote the report, and nowhere else.

**Cause** The check ran against a local server. Nobody fetched the public URL.

**Rule** Local verification is not deployment verification. Say which one you
did. If you did not fetch the public URL with a cache-busting query, you do not
get to write "deployed."

## 3. `git add -A` swept in someone else's work

**Symptom** A commit contained files from a different task, including a
half-finished change that broke production.

**Cause** Several agents working in one tree. One of them staged everything.

**Fix** `git add -A` and `git add -u` added to the forbidden pattern list.

**Rule** Name the files you are committing. In a shared tree, "everything that
changed" is not a set you control.

## 4. A test pinned an exact value and blocked an equivalent change

**Symptom** A correct refactor failed a test that asserted an exact pixel value
that was not the point of the test.

**Cause** The test froze an implementation detail instead of the property that
mattered.

**Rule** Assert the property, not the value. `height >= 24` and a comment saying
why, not `height == 44`. A test that fails on a change that does not change
behavior will be deleted by the next person, and then you have no test at all.

## 5. The host returned 200 and HTML for files that did not exist

**Symptom** A check for whether a data file had deployed passed. The file was
not there.

**Cause** The static host serves the SPA fallback page for unknown paths, with
status 200.

**Rule** Existence checks must validate content, not status. Parse it, or check
the content type, or look for a field you expect. A 200 means the server
answered, not that it answered with your file.

## 6. A proxy metric produced a wrong conclusion

**Symptom** A performance fix was declared successful because the pipeline got
faster.

**Cause** The metric that got measured was not the metric the user experiences.

**Rule** Measure the thing you claim improved. If you cannot measure it, say
that, and say what you measured instead.

## 7. A hypothesis got stated as a diagnosis

**Symptom** A cause was reported confidently, a fix shipped, and the problem
came back.

**Cause** The first plausible explanation was accepted without ruling out
alternatives.

**Rule** Write at least three candidate causes before choosing one, and write
the evidence that eliminated each. If a cause survives only because you did not
look for others, it has not survived anything.

## 8. Verification ran outside the range where the rule applies

**Symptom** A mobile layout rule was verified at a desktop width and passed.
Mobile was broken.

**Cause** The check did not run in the conditions the rule was about.

**Rule** Verify inside the range the rule governs. For anything responsive that
means every breakpoint, and it means both themes if you have themes.

## 9. The verification tool was measuring nothing

**Symptom** A screen check had passed every run for weeks. The selector it read
had been renamed and it was silently matching zero elements.

**Cause** The tool treated "found nothing" as "found nothing wrong."

**Rule** Any check that can match zero things must fail when it matches zero
things. Assert the count before asserting the contents.

## 10. Negative verification was skipped, so the test proved nothing

**Symptom** A regression test was added alongside a fix. Both looked fine. The
test also passed with the fix reverted.

**Cause** Nobody checked that the test could fail.

**Fix** Revert the fix, watch the test fail, restore the fix, watch it pass.

**Rule** A test you have never seen fail is not evidence. Two minutes of
negative verification is the difference between a regression test and a
decoration.

## 11. The cause was found and the fix was never made

**Symptom** An investigation ended with a clear root cause written up. Weeks
later the same bug was reported.

**Cause** "Diagnosed" got filed as "resolved."

**Rule** Diagnosis and repair are separate states. If you only diagnosed it, say
so in those words, and leave the item open.

## 12. Another tool's summary got treated as a conclusion

**Symptom** A decision was made on a summary that turned out to describe
something else.

**Cause** Nobody opened the raw output.

**Rule** Summaries are pointers to evidence, not evidence. Open the underlying
data before you build on it. This applies to summaries produced by other agents
most of all.

## 13. A search for non-ASCII text found nothing and the wrong conclusion followed

**Symptom** A string was reported absent from the codebase. It was there.

**Cause** Shell encoding mismatch between the terminal and the files.

**Rule** Absence of a search hit is not absence of the string until you have
proved your search can find a string you know is there. Search for a known
control string first.

## 14. A setting was declared and nothing ever read it

**Symptom** A rule lived in the project docs for six months and was violated
constantly, by people and agents who had read it.

**Cause** No code read the setting. Nothing could fail because of it.

**Fix** A gate that reads the config and fails the commit.

**Rule** A rule nothing enforces is not a safeguard, it is a note that looks
like one. When you write a rule, decide in the same sitting what reads it. If
the answer is "people, carefully," you have not written a rule.

## 15. Two deploy paths were looking at different commits

**Symptom** A fix appeared live, then disappeared, then came back.

**Cause** Two workflows could both publish. They resolved different refs.
Whichever ran last won.

**Rule** One path to production. If there has to be a second, it must
reach the same ref, and something must check that it did.

## 16. A live feature had its code on no branch

**Symptom** A working feature was in production. The code that produced its
data was not on the main branch, or any branch.

**Cause** The consumer shipped, the producer never merged. The screen kept
reading the last file the producer wrote before it stopped running.

**Fix** A gate that surfaces branches whose content is genuinely not on main,
using patch-equivalence rather than branch names.

**Rule** For any feature, check four things before calling it done: the
producer, the consumer, the wiring between them, and whether it reproduces from
scratch. Most "it works but nobody knows why" traces to a missing producer.

## 17. No completion marker, so the same item got picked up forever

**Symptom** An automated loop spent forty minutes reworking a task that was
already finished.

**Cause** The task list had no way to say "done." Each run picked the top item.

**Rule** If something reads a work list, that list needs a completion state that
the reader understands. When a loop keeps redoing work, suspect the input before
you suspect the worker.

## 18. The auditor audited its own output

**Symptom** An automated review loop produced a stream of commits that reviewed
the previous commit in the stream.

**Cause** The reviewer wrote its results into the same place it read work from.

**Rule** Keep the log separate from the queue. Anything that writes where it
reads will eventually read what it wrote.

## 19. Self-shutdown as a default meant silent death

**Symptom** A recurring job stopped and nobody noticed for forty minutes.

**Cause** It was allowed to disable itself when it thought there was nothing to
do. Failures get logged. "Never woke up" does not.

**Rule** Stopping is a human decision. Make the quiet path noisy: a job that
does nothing should still say so.

## 20. An assumption about the execution environment failed silently

**Symptom** A script reported success and had done nothing.

**Cause** Quoting, argument handling, and stream redirection behaved differently
in the shell it actually ran in.

**Rule** "It works on my shell" is a hypothesis. Verify a script in the
environment that will run it, and make it fail loudly when its assumptions do
not hold.

## 21. An invented acceptance criterion rejected good work

**Symptom** A review failed a correct change against a criterion the task never
had.

**Cause** The reviewer decided what "done" meant instead of reading what had
been asked.

**Rule** Acceptance criteria come from the request, not from the reviewer. Before
you reject something, quote the requirement you are measuring against. If you
cannot find one to quote, you invented it.

## 22. Push was mistaken for deploy

**Symptom** A fix was reported live for two days. It had never been deployed.

**Cause** The deploy workflow needed a manual trigger. Pushing did nothing.

**Rule** Push and deploy are separate events. Confirm deployment from the live
response, not from the commit log or a green workflow.

## 23. The freeze gate ignored commits that had already reached main

**Symptom** A frozen path was modified without a declaration and the gate stayed
green.

**Cause** The gate only examined recent local commits. Anything already pushed
was invisible to it.

**Rule** A gate has to define its range explicitly, and the range has to cover
everything that has not been reviewed yet. A gate with an implicit window has a
blind spot in exactly the direction things escape.

## 24. The work order lagged the code and already-finished work got re-requested

**Symptom** An agent implemented a feature that already existed.

**Cause** The task document had not been updated when the work shipped.

**Rule** Update the work list in the same commit that finishes the work. A task
document that lags the code is worse than no document, because it is confidently
wrong.

## 25. A shell read-and-rewrite destroyed non-ASCII files

**Symptom** Korean text in several files turned into replacement characters.

**Cause** Reading and rewriting files through shell utilities that assumed the
system codepage.

**Rule** Do not round-trip files through shell text tools when the content is
not plain ASCII. Use a tool where you set the encoding explicitly, and check the
file after.

## 26. An exit code read through a pipe was the pipe's

**Symptom** A failing gate was reported as passing.

**Cause** `command | tail` followed by a check on the last exit status. That
status belongs to `tail`, which succeeds almost always.

**Rule** Capture the exit code of the command you care about, before any pipe.
This one is worth a gate of its own if your reports are automated.

## 27. A backup in the system temp directory quietly vanished

**Symptom** A database backup taken before a risky migration was gone when it
was needed.

**Cause** It was written to the system temp directory, which the OS cleans.

**Rule** Backups live inside the project, and you verify the backup exists and
parses before you start the operation it protects.

## 28. The shipped template and our own config were the same file

**Symptom** The first CI run on this repository failed. The gate could not find
`scripts/check_frozen.py`.

**Cause** One workflow file served two purposes: the template users copy, which
expects the gates in `scripts/`, and this repository's own CI, where they live
in `gates/`. Both could not be right, and the one that was wrong was the one
nobody here ever ran.

**Fix** Split them. `examples/workflow.yml` is the template. `.github/workflows/ci.yml`
runs the gates on this repository from their real location, and runs the tests.

**Rule** A file that is both an example and a live config will drift, and the
example is the half that rots, because nothing executes it. Keep the copy people
take separate from the copy you run, and run yours.

## 29. The installed diagnostic inspected the caller's directory

**Symptom** `doctor.py` was run from outside the target repository and reported
missing configs and hooks even though installation had succeeded.

**Cause** The diagnostic defaulted to `Path.cwd()` instead of the repository
that contained the installed script.

**Fix** The default repository is now derived from the script location, with
`--repo` still available for an explicit target.

**Rule** An installed diagnostic must derive its default target from its own
location, not from the shell directory that happened to invoke it.

## 30. The hook checked the previous commit, so the violating commit passed

**Symptom** A frozen file was committed without any UNFREEZE declaration. The
pre-commit hook was installed and ran the frozen gate on every commit - and
still let it through. The next commit, which touched nothing frozen, got
blocked instead.

**Cause** The pre-commit hook called `check_frozen.py` with no arguments. The
gate's default range is `HEAD~1..HEAD`: a range of commits that already exist.
At pre-commit time the current commit does not exist yet, so the gate examined
the previous one. Measured in the origin project on 2026-08-20.

**Fix** Split by what each hook can actually see. pre-commit judges what needs
no message (hook integrity, task scope) plus an advisory `--staged --brief`
notice; commit-msg runs `check_frozen.py --staged --message-file`, where the
message - and with it the declaration - exists.

**Rule** Wire a gate to the moment its inputs exist. A verdict that needs the
commit message cannot happen before there is one, and a staged check that runs
against an existing range checks history, not this change.

## 31. Diff context lines were read as declarations

**Symptom** Committing a file whose content merely contained the marker strings
(`UNFREEZE: ...`, `GUARDRAIL-CHANGE: ...`) passed both message gates, although
nobody had declared anything in the commit message.

**Cause** With `git commit -v`, git hands the commit-msg hook the uncleaned
message file: comment lines, then the whole verbose diff below the scissors
line (`# ------------------------ >8 ------------------------`). Diff context
lines carry one leading space, and `^\s*MARKER:` matches that space. The
protected policy file itself contains marker names, making it the easiest
carrier. Measured in the origin project on 2026-08-20.

**Fix** Both gates strip exactly what git strips before storing the message:
everything from the scissors line down, and every `#` comment line. Range-based
checks read `git log %B`, which is already cleaned - only the hook path needed
the fix.

**Rule** Parse input the way the receiver will store it, not the way it is
handed over. Anything a gate reads raw from a template or a diff can be planted,
and a rule that can be satisfied by planting text protects nothing.
