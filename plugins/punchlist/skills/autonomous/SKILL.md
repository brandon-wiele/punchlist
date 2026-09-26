---
name: autonomous
description: Use when asked to work through the punchlist / backlog unattended — "run autonomously", "grind the backlog", "keep doing /punchlist:next until done" — in a project that has a .punchlist.yml. Works units one at a time through subagents until nothing workable is left, a unit fails, or only items that need the owner remain.
argument-hint: "[max-units]"
---

# Work the backlog unattended

You are the orchestrator. Subagents do the work, one `/punchlist:next` unit each, **strictly one at a
time**: every unit merges to the base branch and rewrites PUNCHLIST, STATE and the ID counter, so two
at once would collide. You never read or write code. Your context holds queue JSON, unit reports and
one review. Formats: `../../reference/formats.md` (relative to this skill's base directory).

**Script:** `PL="${CLAUDE_PLUGIN_ROOT}/bin/punchlist"`. If that variable is empty, use
`<this skill's base directory>/../../bin/punchlist`. `<docs>` and `base_branch` come from
`$PL config`. The argument is the maximum number of units; the default is 10.

If there's no `.punchlist.yml`, stop and suggest `/punchlist:setup`.

## 1. Preflight — stop on any failure and say which

- `git status`: you're on `base_branch` and no tracked files are modified.
- `$PL lint` has no ERROR. Every unit's retire runs lint, so an existing error would fail them all.
- `$PL queue --json` has at least one `workable` entry. If not, report the `needs` and `triage`
  counts, suggest `/punchlist:interview` if either is non-zero, and stop.
- Record `START=$(git rev-parse --short HEAD)`.
- Print one line: `Autonomous run: up to <max> units, starting with <ID> — <text>.` Add: "Units run
  gates and git commands; if this session asks before running commands, the run waits for you." Then
  proceed. Don't ask for confirmation.

## 2. The loop — one unit at a time

1. Run `$PL queue --json` and take the first `workable` entry. If that ID has already been dispatched
   twice this run, stop: it isn't converging.
2. Dispatch **one** general-purpose subagent **in the background** with the prompt below, then wait
   for its completion notification. Dispatch nothing else in the meantime.

   > Work one punchlist unit in `<project root>`: invoke the `punchlist:next` skill with argument
   > `<ID>` and follow it exactly, through merge and bookkeeping. Rules for this run: never ask the
   > user anything — if the unit needs the owner, tag it `needs:` as the skill says, commit the
   > bookkeeping and stop; if a gate fails, don't retire, merge or switch branches — leave the work on
   > the unit's branch and reply `outcome: failed`; never push, whatever `push:` says. Reply with only
   > these lines:
   > outcome: done | partial | split | skipped | failed
   > id: <ID>
   > code_sha: <sha or ->
   > bookkeeping_sha: <sha or ->
   > gates: pass | fail — <which and why>
   > new_items: <P-IDs or ->
   > needs_you: <IDs with one line each, or ->
   > notes: <≤ 3 lines>

3. Run the checks in §3, then go back to step 1.

While a unit runs, the owner may message you. If they say to stop, let the unit finish, run the
checks, and stop with the reason "stopped by owner". Answer anything else from what you already know;
don't dispatch anything new.

## 3. Check after every unit — any failure stops the run

- `git branch --show-current` prints `base_branch`.
- `git status --porcelain --untracked-files=no` prints nothing.
- `$PL lint` has no ERROR.
- `outcome` isn't `failed`, and `gates` doesn't start with `fail`.

On a failure, stop. Don't clean up, stash, switch branches or retry: the owner decides. Skip §5 step 1
and go to the review and report.

## 4. Stop conditions

- No `workable` entries are left.
- `max-units` units have run.
- A check in §3 failed.
- The next ID would be dispatched a third time.
- The owner asked to stop.

## 5. Wrap

1. **Only if the last checks passed:** run `$PL compact`. Apply it with `$PL compact --apply` unless
   it parks an item this run touched. Run `$PL lint`. If anything changed, commit it as
   `docs(punchlist): autonomous run — <n> units`.
2. **Review the run.** If `git log --oneline START..HEAD -- . ':(exclude)<docs>'` lists any commit,
   dispatch one read-only reviewer subagent (use `superpowers:requesting-code-review` if it's
   available) with:
   > Review `git diff <START>..HEAD` in `<project root>`, unit by unit. Units: <one line each: ID —
   > item text — code_sha>. For each unit, reply `<ID>: fine` or `<ID>: look at this — <why>
   > (<file:line>)`. Look for correctness bugs, changes outside the item's scope, and tests that don't
   > exercise the change. Don't edit anything.

   The review is advisory. It never fixes, reverts or stops anything.
3. If this session has a push-notification tool, send one line:
   `punchlist: <n> units done — stopped: <reason>`.

## 6. Report — this is the whole output

```
Autonomous run — <n> units, stopped: <reason>

| Unit | Outcome | Code | Review |
|---|---|---|---|
| P-### <short text> | done | abc1234 | fine |

New items: P-### …
Review before publishing: git log --oneline <START>..HEAD — nothing was pushed.
<N> items need you — run /punchlist:interview
```

After a failure, add the failed unit's report, the branch it left, and the exact next step. Leave out
the `needs` line when nothing needs the owner.

## Common mistakes

| Mistake | Instead |
|---|---|
| Two units at once | Strictly serial; wait for each completion before the next dispatch |
| Reading code, or finishing a unit yourself | Subagents work; you pick, check and report |
| `/punchlist:handoff` after each unit | `:next` already retires and refreshes STATE; you run compact and lint once at the end |
| Cleaning up after a failed unit | Stop and report; the owner decides |
| Pushing | Never, whatever `push:` says |
| Working `later` items | Only `workable` entries; `later` items come back through `/punchlist:interview` triage |
| Asking the owner mid-run | Talk to the owner only in the preflight line and the report |
