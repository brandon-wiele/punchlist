# `/punchlist:interview` + `/punchlist:autonomous` — design

P-006 · 2026-09-25 · Size: medium (one spec, one plan, one branch, merged once)

## Why

Two gaps in the loop between the owner and the sessions:

1. **Items that need the owner pile up and read cryptically.** A session reports "P-012 needs you"
   with a terse line; the owner has to reconstruct the context before they can answer. Nothing
   collects these items or presents them well, so they sit.
2. **Working the backlog needs a human to re-invoke `/punchlist:next` per unit.** Everything an agent
   can do alone should run unattended until only owner items remain.

The two skills are complementary: `:autonomous` works until only owner items remain and hands over
to `:interview`; `:interview` turns owner items back into workable ones for the next `:autonomous`.

## Components

### 1. The `needs:` marker (format change)

A backtick tag on a P-item, like `from:`:

```
- **P-012** · next · Pick the CLI login provider: device-code flow or browser redirect. `needs: decision`
```

- Kinds: **`decision`** (the owner answers a question) and **`action`** (only the owner can do it).
  The question or task is the item text. At most one marker per item.
- **The marker is the only record** that an item waits on the owner. STATE's `**Waiting on <owner>:**`
  line is removed from the format, the template and this repo (ruling R1).
- Code-review findings keep their own `Status: needs-ruling: <question>`; they are not also tagged.

**When to tag `needs: decision` (strict — goes in formats.md).** Only when at least one holds:
the owner has said the decision is theirs ("we need to decide …"); a product/UX fork the spec and
code don't settle; a choice that is expensive to reverse (data model, public format, published
interface, supported platforms or versions); a change to a contract documented in CLAUDE.md;
spending money or touching external accounts; anything externally visible (publishing, messaging
people). Otherwise the session decides, records a ruling, and keeps going — as CLAUDE.md § Planning
weight already says.

**`needs: action`** — the owner must physically do it: credentials, publishing, account setup,
live/manual checks against production or hardware.

**Other format additions**

- Ruling on an item: a continuation line `  Ruling YYYY-MM-DD: <answer> — <why>`. If the item would
  exceed 5 lines, the ruling goes in the linked spec's Rulings section and the item links to it.
- Owner-done manual task: `  — DONE YYYY-MM-DD (manual): …` (no commit did the work).
- Dropped item: moved to `history/punchlist-done.md` with `  — DROPPED YYYY-MM-DD: <why>`. The ID is
  retired for good (R7).
- Triaged-and-kept item: a progress-style note `(YYYY-MM-DD: triaged — keep, <why>)`, which also
  resets its age.
- Config: `budgets.triage_after_days` (default 30). `owner` keeps its meaning ("who `needs:` items
  wait on").

### 2. Script: `needs` parsing, `punchlist queue`, lint rules (stdlib, TDD)

- `parse_punchlist` records `needs` on each item: the list of kinds from `` `needs: <kind>` `` tags
  anywhere in the item's span (empty when untagged), so lint can see duplicates.
- **`punchlist queue [--json]`** — the single source of pick order, used by `:next`, `:autonomous`
  and `:interview`. Read-only.
  - `workable`: open items with no `needs:`, in `:next`'s order — STATE Next up entries (listed
    order), then `now` items, then `next` items, both in PUNCHLIST order; deduplicated. `later`
    items are never workable (R5).
  - `needs`: items with a `needs:` marker (`kind` = decision | action), plus findings whose Status is
    `needs-ruling:` (`kind` = ruling, with `file` and `question`).
  - `triage`: untagged `later` items unchanged for more than `triage_after_days` (same git-blame age
    as `compact`), with `age_days`.
  - Each entry carries `id`, `priority`, `section`, `text` (item lines joined). Plain output is a
    short human list per group.
- **lint**
  - ERROR: unknown `needs:` kind; more than one `needs:` marker on an item.
  - WARN: a legacy `**Waiting on` line in STATE ("tag those items `needs:` and remove the line").
  - WARN: Next up lists an item that has a `needs:` marker (sessions will skip it).
- The `(manual)` DONE and `DROPPED` lines need no parser change (`parse_done_ids` keys off the item
  line); tests assert they count as closed.

### 3. `/punchlist:interview`

1. **Preflight.** `.punchlist.yml` exists; no uncommitted tracked changes (it commits bookkeeping on
   the current branch, like `:handoff`).
2. **Queue.** `$PL queue --json` → `needs` + `triage`. Then read PUNCHLIST whole for untagged items
   that look owner-only (Ops / manual section; decide/confirm/choose wording) and ask once, as a
   multi-select, which really need the owner; tag those. Tagged items that fail the strict criteria
   are offered back with "Your call" as the recommended option.
3. **Empty queue** → report "nothing needs you; N workable items" and suggest `:autonomous`. Stop.
4. **Research in parallel.** For each `decision` and `ruling` entry, dispatch a read-only subagent
   (Explore) that reads the linked spec, code, finding and relevant git history and returns a brief:
   - **Headline** in plain language (the P-ID is a footnote, never the headline).
   - **Why it's blocked** and what it holds up (items with `from:` pointing at it, Next up position).
   - **2–3 options**, each with engineering cost, risk and reversibility.
   - **Recommendation** and the reason.
   - **What happens next** for each option (what gets unblocked, what gets filed).
   `action` and `triage` entries are briefed inline from the item and `git log` — no subagent.
5. **Ask in batches.** Decisions and rulings first, most-blocking first. Up to 4 questions per
   `AskUserQuestion` call, each preceded in chat by its brief. Per question: recommended option first
   and labelled "(Recommended)"; `description` holds the one-line trade-off, `preview` the detail;
   a "Not now" option leaves the item tagged. Action options: Done · Not yet · Drop it. Triage
   options: Keep · Promote to next · Park · Drop. Free-text answers ("Other") that are unclear get one
   follow-up; still unclear → leave tagged with a note.
6. **Record.** Decision → ruling line, remove the marker, adjust priority. Ruling → finding Status
   `open — ruling YYYY-MM-DD: …` or `wontfix: …`. Action done → retire with `(manual)`. Drop →
   `DROPPED`. Park → `history/parked.md` with `— PARKED YYYY-MM-DD: triaged (<why>)`. Promote →
   change priority. Keep → triage note. Items that became `now` go into STATE Next up in order.
7. **Wrap.** `$PL lint` (fix ERRORs) → one commit `docs(punchlist): interview — <n> resolved`.
   Report: resolved, still open, and how many items are now workable — suggest `:autonomous` if any.
   Answers are written to the docs as each batch comes back, so if the owner stops partway, the wrap
   still runs and commits what was resolved; unanswered items stay tagged.

### 4. `/punchlist:autonomous [max-units]`

1. **Preflight.** `.punchlist.yml` exists; on `base_branch`; no uncommitted tracked changes;
   `$PL lint` has no ERROR (a pre-existing error would fail every unit's retire). Any failure → stop
   and say why. Print one line of plan (queue head, cap) and a note that an unattended run stalls on
   permission prompts for gates and git unless the session auto-approves them. Don't ask; proceed.
   Record the start SHA (`git rev-parse --short HEAD`) for the review and the report.
2. **Loop, serially (R3).** `$PL queue --json` → first `workable` entry. None → stop. Dispatch one
   general-purpose subagent **in the background** and wait for its completion before doing anything
   else — still one unit at a time, but the owner can talk to the orchestrator mid-run (R9):
   > Invoke the `punchlist:next` skill with argument `<ID>` in `<root>` and follow it exactly. Never
   > ask the user anything; if the unit needs the owner, tag it `needs:` as the skill says and stop.
   > Never push, whatever `push:` says. Reply only with: `outcome` (done | partial | split | skipped
   > | failed), `id`, `code_sha`, `bookkeeping_sha`, `gates`, `new_items`, `needs_you`, `notes`
   > (≤ 3 lines).

   Subagents run `:next` only — no per-unit `:handoff` (R2). If the owner says to stop, let the
   running unit finish and pass its checks, then stop with reason "stopped by owner".
3. **Check after every unit.** On `base_branch`; no uncommitted tracked changes; `$PL lint` has no
   ERROR; `outcome` isn't `failed`. Any failure → **stop the run** (R4); report the subagent's
   report, the branch left behind and the exact next step. Never clean up or stash.
4. **Stop conditions.** Workable queue empty · only `needs:` items remain · `max-units` reached
   (default 10) · a check fails · the same ID is dispatched a third time in one run (not converging)
   · the owner asks to stop.
5. **Wrap.** `$PL compact` and apply it unless it parks an item touched this run; `$PL lint`; commit
   `docs(punchlist): autonomous run — <n> units` if anything changed.
6. **Review the run (R10).** If any unit committed code, dispatch one read-only reviewer subagent over
   `<start-sha>..HEAD` with the list of units and their item text. It returns, per unit, "fine" or
   "look at this: <why, file:line>" — correctness, scope creep, or tests that don't exercise the
   change. It doesn't fix, revert or stop anything; its verdicts go in the report. Use
   `superpowers:requesting-code-review` if available, otherwise a plain review prompt.
7. **Report.** One row per unit (ID, outcome, SHAs, review verdict), new P-IDs, stop reason, the
   commit range to review before publishing (`<start-sha>..HEAD`), and — if `needs` is non-empty —
   "N items need you — run `/punchlist:interview`". **Never pushes, whatever `push:` says (R8).**
   If the session has a notification tool, send a one-line notice when the run stops.

The orchestrator never reads code; its context holds only queue JSON, unit reports and the review.

### 5. Changes to existing skills and docs

- **`:next`** — pick order comes from `$PL queue` (umbrella/finding rules unchanged). When it skips an
  owner-only unit, it tags it `needs: <kind>` with the question stated plainly, applying the strict
  criteria; otherwise it decides and records a ruling. Given an ID that carries `needs:`, it stops and
  says so.
- **`:add`** — tags owner-only items `needs:` (replaces "add it to the Waiting on line").
- **`:handoff`** — drops the Waiting-on step; deferred owner items get `needs:`; report item 5 comes
  from `$PL queue`.
- **`:review`** — replace its Waiting-on reference with `needs-ruling:` / `needs:`.
- **`:setup`** — template STATE loses the Waiting-on line; template `.punchlist.yml` gains
  `triage_after_days`. Upgrade (§6) migrates a legacy Waiting-on line: tag each listed item `needs:`
  (decision or action, by judgment) and remove the line.
- **Docs** — formats.md (all of §1, queue semantics), README skills + script tables, `design.md`
  skills table, `claude-md-block.md` skills line, this repo's CLAUDE.md skills line and STATE system
  map.
- The version bump is `just release`, after merge — not part of this branch.

## Rulings

- **R1** — The `needs:` marker is the single source; STATE's Waiting-on line is dropped (not
  script-rendered). `punchlist queue` answers "what's waiting on me".
- **R2** — `:autonomous` subagents run `:next` only. `:next` already does handoff steps 1–4; a
  per-unit `:handoff` would double bookkeeping and could park items mid-run.
- **R3** — Serial only. Every `:next` merges to base and rewrites PUNCHLIST/STATE/counter;
  parallel units would conflict on nearly every merge.
- **R4** — Any failed check stops the run; the orchestrator never repairs state unattended.
- **R5** — `later` items are never worked autonomously; `:interview` triage promotes them.
- **R6** — Two marker kinds only (`decision`, `action`). Findings keep `needs-ruling:`.
- **R7** — Dropped items go to punchlist-done with `DROPPED`; their IDs stay retired.
- **R8** — `:autonomous` never pushes, even with `push: allowed`. Unattended work is reviewed by the
  owner before it leaves the machine; the report gives the range.
- **R9** — Units are dispatched in the background but strictly one at a time, so the owner can stop
  a run between units without killing a unit mid-merge.
- **R10** — One review per run, not per unit: it points the owner's review at the units that need
  it, at the cost of one agent. It is advisory and never blocks or reverts.

## Testing

- **Script (TDD, `tests/test_punchlist.py`):** needs parsing; lint (unknown kind, duplicate marker,
  legacy Waiting-on, Next up lists a needs item); `queue` ordering (Next up → now → next, dedupe,
  excludes `later` and `needs`), `needs` group including needs-ruling findings, `triage` with an
  injected age function, JSON shape; `(manual)` and `DROPPED` lines count as closed.
- **Spike, before the plan — passed 2026-09-25.** A general-purpose subagent has the Skill tool,
  loaded `punchlist:next`, and sees every `punchlist:*` skill. It loaded the **installed** copy
  (`~/.claude/plugins/cache/punchlist/punchlist/0.4.0/…`), so subagents only see skill changes after
  `just release` + `/reload-plugins`. Dry runs therefore load skills from the checkout, not the
  installed plugin.
- **Skill dry runs (baseline vs with-skill, per `superpowers:writing-skills`)** against a scratch repo
  holding two small workable items, two `decision` items, one `action`, one `needs-ruling` finding and
  one stale `later` item:
  - `:interview` — briefs lead with plain language, give options with trade-offs and a
    recommendation; answers are recorded in the right format; lint is clean; one commit.
  - `:autonomous` — works both workable items serially, stops on `needs:`, reviews the range, doesn't
    push under `push: allowed`, suggests `:interview`; a second scenario with a failing gate stops at
    that unit and leaves the branch; a third where the owner says "stop" mid-run stops after the
    current unit.
  - `:interview` stopped after the first batch still commits the answers given.
  - `:next`, `:add`, `:handoff` — owner items are tagged with `needs:`, and no Waiting-on line is
    written.
- `just check` passes.
- **Acceptance — dogfood on this repo.** After the legacy Waiting-on migration, run `:interview`
  against this repo's own backlog: P-005 (list in marketplaces once P-001 passes) is a real
  `needs: action` item, and the stale `later` items are real triage candidates.

## Out of scope

Parallel units; model selection per unit; headless `claude -p` driving (P-001 covers headless smoke);
script-rendered Waiting-on line.
