# Build log — shipped milestones (newest first)

> Companion to [`../STATE.md`](../STATE.md). STATE says where we are; this file says how we got here.
> Read the **index table** first and open entries by grep. Releases are tagged `vX.Y.Z`.

## Index

| Date | Milestone | Merge | Spec / plan |
|---|---|---|---|
| 2026-10-26 | Subagent use left to the model | `1bb0625` | none (small) |
| 2026-10-14 | Related issues are folded in, not filed | `639350c` | none (small; P-016) |
| 2026-09-26 | Lint checks the docs index and archive links | `3d83f3d` | none (small) |
| 2026-09-26 | Brief skill | `082395b` | design agreed in session (no spec) |
| 2026-09-25 | Interview + autonomous skills | `b9d6544` | `docs/specs/2026-09-25-interview-autonomous-design.md` · `docs/plans/2026-09-25-interview-autonomous.md` |
| 2026-09-23 | v0.4.0 — first public release | `v0.4.0` | `docs/design.md` |

## Entries

### 2026-10-26 — Subagent use left to the model — merged `1bb0625`
no spec (small)
- **Why:** current models don't need to be told when to delegate. The skills hard-wired it:
  `:autonomous` made the session an orchestrator that never read code, `:interview` sent research to
  parallel `Plan` agents, and `:review` sent one background subagent per area.
- **What shipped:** those three skills, the review templates, `:setup` and the README no longer steer
  toward or away from subagents. Each says how to run the work is the model's call. The unit rules in
  `:autonomous` read the same inline or delegated, and ending a unit returns to the loop.
- **Rulings:** keep the correctness constraints (strictly serial units, read-only reviews and research).
- **Verification:** `just check`, plus a read-through for leftover steering and steps that only work in
  one mode. No with/without dry run.

### 2026-10-14 — Related issues are folded in, not filed — merged `639350c`
no spec (small; P-016)
- **Why:** in three adopting projects' transcripts, agents filed nine items for work that belonged to
  the unit (the same bug in sibling code, gaps in their own fix, regressions they caused), citing
  "one unit", "pre-existing" and the handoff rule. The owner pushed most back, and chose "now" whenever asked.
- **What shipped:** `:next` §3 says what belongs to a unit and folds it in; related work that would
  make the unit large is asked about (interactive) or filed `now` (unattended). Reports gain "Folded
  in" and a reason per filed item. The CLAUDE.md block gets the rule; its handoff step is end-of-session
  only. `:autonomous` marks units unattended; `:handoff` marks filed items that belong to the session.
- **Rulings:** ask before folding in large related work (owner); the managed block changes too, so
  adopters get it on the next `/punchlist:setup` re-run (owner). A flaky unrelated test that fails a
  gate doesn't belong to the unit.
- **Verification:** dry runs, current vs new text: sibling bug folded 4/5 → 5/5; large related work
  asked 0/5 → 5/5; unrelated issues filed 5/5 → 5/5; own-fix gap folded 5/5 → 3/3; unattended
  large work filed `now` with a reason 3/3.

### 2026-09-26 — Lint checks the docs index and archive links — merged `3d83f3d`
no spec (small; P-004)
- **Why:** `/punchlist:tidy` writes a docs index, but nothing noticed when it went stale or when a
  current doc sent readers into the archive.
- **What shipped:** once `<docs>/README.md` exists, `punchlist lint` WARNs about any doc the index
  doesn't link, directly or through a linked folder, and about any doc outside the archive and
  `history/` that links to a file inside the archive. No new config.
- **Rulings:** folder links cover their contents (a `specs/` row covers every spec); the index and
  the history files may link into the archive; naming the archive folder isn't a link to a file.
- **Verification:** 3 new tests, 54 in all on 3.9 and 3.13.

### 2026-09-26 — Brief skill — merged `082395b`
design agreed in session; no spec or plan (small)
- **Why:** coming back to a project needed a readable catch-up; STATE is terse position, not a story.
- **What shipped:** `/punchlist:brief [N]` (read-only: where things stand, the last N finished units
  grouped into themes, what's next); `punchlist recent [--limit N] [--json]` — done items and fixed
  findings, newest first, dated by the DONE date and the closing commit (two git calls in total).
- **Rulings:** "lately" = the last N finished units, not a time window (owner's choice); DROPPED
  items are excluded; "also changed since" anchors on the newest unit that has a commit.
- **Verification:** 48 tests on 3.9 and 3.13. Dry run on this repo: the no-skill brief said nothing
  waited on the owner (P-005 did); the skill's first run missed changes since a hand-done unit, so the
  anchor, the pick rule and a word budget were fixed, and the re-run was clean.

### 2026-09-25 — Interview + autonomous skills — merged `b9d6544`
spec `docs/specs/2026-09-25-interview-autonomous-design.md` · plan `docs/plans/2026-09-25-interview-autonomous.md`
- **Why:** items that need the owner piled up and read cryptically; working the backlog needed re-invoking `:next` per unit.
- **What shipped:** `/punchlist:interview`; `/punchlist:autonomous`; the `needs: decision|action` marker replacing STATE's Waiting-on line (parser, lint, formats, templates, add/next/handoff/review/setup); `punchlist queue [--json]` as the one pick order; item age spans the whole item; `budgets.triage_after_days` (30).
- **Rulings:** R1–R11 in the spec (Waiting-on dropped; `:next` only per unit; serial; stop on failure; `later` never autonomous; two kinds; DROPPED; never push; background serial units; one advisory run review; progress-based convergence). The autonomous report shows only the code SHA per unit (bookkeeping SHAs are in the range).
- **Deferred:** → P-007, P-008, P-009.
- **Verification:** `just check` (44 tests, Python 3.9 + 3.13); baseline-vs-checkout dry runs of add/next/handoff/interview (incl. stop-early) and autonomous happy path, failing gate and umbrella; wording fixed from the dry runs (W1–W4) and the final review. Pending live (Task 8): owner stop mid-run, parallel research subagents, AskUserQuestion `preview`.

### 2026-09-23 — v0.4.0, first public release — tag `v0.4.0`
design `docs/design.md`
- **What shipped:** six skills (`setup`, `next`, `add`, `handoff`, `review`, `tidy`); the normative
  formats reference and templates; the stdlib `punchlist` script (`config`, `status`, `next-id`,
  `lint`, `compact`, `docs`) with 27 unit tests; a `justfile` for check/release/publish.
- **Verification:** unit tests plus dry-run scenario tests (baseline vs with-skill) for every skill,
  and a pilot on a large, long-running project.
