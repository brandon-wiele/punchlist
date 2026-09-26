# Build log — shipped milestones (newest first)

> Companion to [`../STATE.md`](../STATE.md). STATE says where we are; this file says how we got here.
> Read the **index table** first and open entries by grep. Releases are tagged `vX.Y.Z`.

## Index

| Date | Milestone | Merge | Spec / plan |
|---|---|---|---|
| 2026-09-25 | Interview + autonomous skills | `b9d6544` | `docs/specs/2026-09-25-interview-autonomous-design.md` · `docs/plans/2026-09-25-interview-autonomous.md` |
| 2026-09-23 | v0.4.0 — first public release | `v0.4.0` | `docs/design.md` |

## Entries

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
