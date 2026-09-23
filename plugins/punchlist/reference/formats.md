# punchlist formats (normative)

Every skill and the `punchlist` script follow this file. `<docs>` is `docs_dir` from `.punchlist.yml`
(default `docs`). The script parses these shapes exactly, so keep them.

## Files and their one job

| File | Job | Read how |
|---|---|---|
| `<docs>/STATE.md` | Position: snapshot, next up (as P-IDs), orientation, system map, verbs, gotchas, recent milestones | **Whole**, every session |
| `<docs>/PUNCHLIST.md` | The only backlog. Every open bug, feature, deferral, manual step, ops task | **Whole**, every session |
| `<docs>/history/build-log.md` | What shipped: index table + one ≤15-line entry per merge | Index table first; entries by grep |
| `<docs>/history/punchlist-done.md` | Closed P-items | By grep on ID only |
| `<docs>/history/parked.md` | Stale `later` items moved out of PUNCHLIST (not rejected, just cold) | By grep; re-promote by moving back |
| `<docs>/code-review/README.md` | Review index: generated roll-up, themes, Fix-first table | Whole when working review items |
| `<docs>/code-review/NN-<area>.md` | Findings for one area | By grep on finding ID only |
| `<docs>/README.md` | Docs index: every current doc, its role and status (written by `/punchlist:tidy`) | When looking for a doc |
| `<docs>/archive/` + its `README.md` | Superseded docs, and why each is wrong | Only when researching history |

Nothing is recorded in two of these. Design detail lives in specs/plans; rulings go in the spec or
the build-log entry, never STATE.

## STATE.md

Required sections, in order: `## Snapshot — YYYY-MM-DD`, `## Next up`, `## Orientation`,
then project-specific sections (system map, verbs, gotchas), then `## Recent milestones`
(newest ~8) and `## Maintaining this file`.

The snapshot's first bullet carries the SHA the script checks:

```
- **Branch:** `master` @ `abc1234`, clean. …
```

The SHA is the **last code commit** (bookkeeping/doc commits after it don't count; pointing at a later
docs-only commit is tolerated). `lint` errors if
a commit touching anything outside `<docs>/`, `.punchlist.yml` and `CLAUDE.md` files landed after it.
Other bullets: `**Last shipped:**`, `**In flight:**` (branch, what's done, the exact next step,
uncommitted state — or "nothing"), `**Environment:**`.

`## Next up` is a numbered list whose entries lead with P-IDs, in the order to do them: `now` items
first, then whichever `next` item unblocks the most. When nothing is `now`, list the top `next`
items. Follow it with `**Waiting on <owner>:** P-…` for items only the owner can do. `lint` errors if
Next up names a done item.

## PUNCHLIST.md

```
- **ID** — `P-###`, never reused, never renumbered. Next free ID: **P-012**.
```

That counter line must exist once. Items are grouped under `## <Section>` headings. The standard set,
in order, is Bugs · Features · Improvements · Follow-ups from shipped work · Ops / manual · Code review
(<date>). Omit empty sections, and add a project-specific section only when none fits. An item:

```
- **P-007** · next · One line saying what and why. `from: P-003`
  Up to 3 continuation lines indented two spaces, linking out for detail.
```

- Priority is exactly one of `now` (blocking or next up), `next` (queued), `later` (parked or nice to have).
- `from:` names the item or feature that spawned a deferral.
- Partly done: add a progress note `(YYYY-MM-DD: <what's done> <sha or "uncommitted">; <what remains>)`.
- An item is ≤ 5 lines in total (`lint` warns above that). Link out instead of growing it.
- An item must be actionable by a cold session: say what's wrong or wanted and where. If the premise
  is conditional (e.g. "once there's a UI"), say so.
- An **umbrella** item points at a list worked row by row (e.g. a code-review Fix-first table). It
  retires only when its last row closes.

## history/punchlist-done.md

Closing an item: **cut** the whole entry from PUNCHLIST, paste it under the `## ` heading with the
same name as its PUNCHLIST section (create the heading at the end of the file if missing), keep its
format, and add this as **its own line, indented two spaces**, after the item's last line:

```
  — DONE 2026-09-23 (abc1234): one line on what shipped.
```

The SHA is the commit that did the work.

## history/parked.md

Same as done, but the suffix line is `  — PARKED YYYY-MM-DD: stale (no change in N days)`. To revive an item,
move it back to PUNCHLIST with its original ID.

## history/build-log.md

An index table at the top (newest first):

```
| Date | Milestone | Merge | Spec / plan |
|---|---|---|---|
| 2026-09-23 | Feature name | `abc1234` | `specs/…` |
```

Then `## Entries` with one entry per merge, each **≤ 15 lines** from its `### ` heading:

```
### 2026-09-23 — Feature — merged `abc1234`
spec `…` · plan `…`
- **Why:** the problem, in one or two sentences.
- **What shipped:** the 3–6 load-bearing facts (entry points, tables, flags).
- **Rulings:** decisions made during the build that aren't in the spec.
- **Deferred:** → P-### (IDs only).
- **Verification:** gates run; what isn't verified yet.
```

"Merged" means it landed on the base branch, whether by merge or by direct commit. Log a unit when it
changed user-visible behavior, a security property or a contract. Small bug fixes, pure refactors,
test-only changes, docs and dead-code removal skip the build log: their record is the DONE line.
For history with no merge commits, the Merge column holds the representative commit.

## Code review files

A finding, while open:

```
### API-001 · high · Short title
- **Where:** `path/file.ts:123`
- **Category:** correctness | security | tenancy | contract-drift | reliability | performance | maintainability | test-gap | dead-code
- **Confidence:** confirmed | plausible
- **Status:** open
- **Problem:** …
- **Failure scenario:** …
- **Suggested fix:** …
- **Effort:** S | M | L
```

- Severity is one of `critical`, `high`, `medium`, `low`, `nit`.
- IDs are `<AREA>-###`, where AREA is uppercase letters, digits and hyphens. They are stable and
  never reused.
- The Status value starts with one of:
  - `open` (optionally `open — <note>`, e.g. a recorded ruling)
  - `needs-ruling: <question>`
  - `fixed <sha>`
  - `wontfix: <why>`
  - `dup of <ID>`

  The first two are open; the last three are closed.
- **Collapsed** (after close, by `punchlist compact`): the whole finding becomes one line and its body
  is removed. Git keeps the text.
  ```
  ### API-001 · high · Short title — fixed abc1234
  ```

The review README has a roll-up between markers that only `punchlist status --write` edits:

```
<!-- punchlist:status:begin -->
…generated table…
<!-- punchlist:status:end -->
```

A Fix-first table follows, with columns `| # | Finding(s) | Why first | Effort |`. When every finding
in a row is closed, replace the `#` cell with `✅` and append ` — fixed <sha(s)>` to the "Why first"
cell.

## Docs index — `<docs>/README.md`

It opens with a one-paragraph orientation that points at STATE.md, then sections as needed:
**Session continuity** (the managed files), **Reference** (current design/architecture docs),
**Specs & plans** (the folders, not each file), **Topic handoffs & checklists**, and **Archive**. Each
table row is `| [doc](path) | what it covers | status |`, where status is one of:
- `current`
- `open — P-###` (a live checklist or handoff whose work is tracked)
- `done` (kept as a record)
- `drifting — P-###` (known-stale; rewrite tracked)

Only docs that a future session might read are listed. Plans and specs are covered by the build-log
index, not listed one by one.

## Archive — `<docs>/archive/README.md`

Starts with **"Superseded. Do not derive scope or code from anything here."** followed by a table:
`| Doc | Archived | Superseded by | What's wrong with it now |`. The last column is concrete, e.g.
"describes the plugin-registry model removed in the 2026-06 rewrite". Archived docs are moved with `git mv`
and never deleted or edited, apart from an optional one-line banner.

## .punchlist.yml

```yaml
docs_dir: docs
base_branch: main
branch_prefix: punchlist/
push: never            # never | allowed
owner: the maintainer  # who "Waiting on" means
build_log_since: 2026-09-23   # entries dated before this are exempt from the length budget
gates:
  - run: npm test
  - run: composer test
    when: app/**       # optional glob: run only if the diff touches it
docs_exclude:          # whole files `punchlist docs` skips: generated mirrors, vendored docs
  - apps/*/AGENTS.md
docs_ignore_tags:      # <tag>…</tag> regions skipped as generated vendor text (default below)
  - laravel-boost-guidelines
budgets:
  state_lines: 120
  punchlist_lines: 250
  build_log_entry_lines: 15
  stale_later_days: 60
```

The config uses a YAML subset: scalars, nested maps, and lists of scalars or maps. Two-space indents,
`#` comments, no anchors, and no multi-line strings.
