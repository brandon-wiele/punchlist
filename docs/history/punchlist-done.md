# PUNCHLIST — done

Closed items, moved out of [`../PUNCHLIST.md`](../PUNCHLIST.md) under their original section. Each is
followed by its own indented line `  — DONE YYYY-MM-DD (<sha>): <what shipped>`. Read by grep on ID only.

## Improvements

- **P-002** · next · `/punchlist:setup` **upgrade** mode (re-run with an existing `.punchlist.yml`)
  has never been exercised; test it and the managed-block re-sync.
  — DONE 2026-09-23 (no code change): exercised on a real adopted project via /punchlist:setup — block re-synced (2-line diff), text outside the markers untouched, lint clean. Also confirmed `${CLAUDE_PLUGIN_ROOT}` expands in SKILL.md at load.
- **P-003** · later · Automated skill regression suite via `claude plugin eval`, replacing hand-run
  dry-run scenarios.
  — DROPPED 2026-09-26: merged into P-001 — the eval suite it proposed is now P-001's approach.
- **P-001** · next · End-to-end skill evals with `claude plugin eval`, slice 1: the harness plus
  smoke cases for add, next, handoff, brief and setup. Spec `docs/specs/2026-09-26-eval-suite-design.md`,
  plan `docs/plans/2026-09-26-eval-suite-slice-1.md` (task 1 is a spike).
  (2026-09-26: spec and plan written, absorbing P-003; remains: build slice 1)
  — DONE 2026-09-26 (manual): the owner tested the skills end to end by hand on several projects; the eval suite continues as P-014.
- **P-008** · later · `/punchlist:add` step 6 says "fix any ERROR" from `punchlist lint`, which
  can lead it to "fix" unrelated pre-existing errors (e.g. a stale snapshot); scope it to errors
  its own edit caused and report the rest, as `/punchlist:interview` now does. `from: P-006`
  — DONE 2026-09-26 (bb6a9ad): `:add` fixes only lint errors its edit caused and names the rest; dry run showed the old wording rewrote STATE.
- **P-015** · later · `/punchlist:review` (step 5) and `/punchlist:tidy` (step 8) also say "fix every
  ERROR" from `punchlist lint`, so they can rewrite a stale STATE snapshot that isn't theirs. Scope
  them the way P-008 scoped `:add` (fix what your edits caused, name the rest). `from: P-008`
  — DONE 2026-09-26 (0e58fde): review and tidy fix only lint errors their edits caused and report the rest.
- **P-007** · later · `_item_age_days` runs one `git blame` per line of an item (up to 5 per
  `later` item; compact calls it twice), and `punchlist queue` now runs after every
  `/punchlist:autonomous` unit — use one `git blame -L start,end` per item instead.
  `plugins/punchlist/lib/punchlist_core.py`. `from: P-006`
  — DONE 2026-09-26 (c087273): one blame per file (cached per line), better than one per item; lint, compact and queue each blame PUNCHLIST once.

## Features

- **P-006** · now · `/punchlist:interview` (clear items that need the owner, PM-style briefs) and
  `/punchlist:autonomous` (serial subagent loop over `:next`), plus a `needs:` item marker and a
  `punchlist queue` command. Spec: `docs/specs/2026-09-25-interview-autonomous-design.md`,
  plan: `docs/plans/2026-09-25-interview-autonomous.md`.
  — DONE 2026-09-25 (b9d6544): /punchlist:interview + /punchlist:autonomous, needs: marker, punchlist queue.
- **P-010** · now · `/punchlist:brief [N]`: a read-only, plain-language catch-up — where the project
  stands, the last N finished units grouped into themes, and what's next — backed by a new
  `punchlist recent [--limit N] [--json]` command (closed units, newest first).
  — DONE 2026-09-26 (082395b): /punchlist:brief and punchlist recent.

## Ops / manual

- **P-009** · now · Release and dogfood P-006 with the maintainer: `just release minor`,
  `/reload-plugins`, run `/punchlist:interview` on this repo, then `/punchlist:autonomous 2`
  with the maintainer saying "stop" mid-unit (checks: research subagents return every brief
  field; AskUserQuestion accepts `preview`; owner stop). Plan:
  `docs/plans/2026-09-25-interview-autonomous.md` Task 8. `needs: action` `from: P-006`
  — DONE 2026-09-26 (manual): v0.5.0 released; live /punchlist:interview run (preview accepted); owner closed it without the autonomous owner-stop run or a live research-subagent check.
- **P-012** · later · Decide whether CI runs `just eval` (the smoke eval suite): it needs an API-key
  secret and spends money on every run. Spec D1. `needs: decision` `from: P-001`
  — DONE 2026-09-26 (manual): decided — no; the eval suite stays a local `just eval`, never run in CI.
