# PUNCHLIST — the single backlog of open work

**Every not-done item lives here, and only here.** STATE.md points at IDs in this file. Done items
move to [`history/punchlist-done.md`](history/punchlist-done.md), and stale `later` items to
[`history/parked.md`](history/parked.md). Formats: `plugins/punchlist/reference/formats.md`.

## Conventions

- **ID** — `P-###`, never reused, never renumbered. Next free ID: **P-011**.
- **Priority** — `now` (blocking or next up), `next` (queued), `later` (parked or nice-to-have).
  One line per item plus ≤ 3 lines of context; link out for the rest.
- **Adding** — `/punchlist:add`, or append under the right section with `punchlist next-id --bump`.
- **Waiting on the owner** — tag the item `` `needs: decision` `` or `` `needs: action` ``
  (formats.md has the criteria). `/punchlist:interview` clears them; sessions skip them.
- **Closing** — move the whole item to `history/punchlist-done.md` with
  `— DONE YYYY-MM-DD (<sha>): <what shipped>`. `/punchlist:next` does this. Ship with `just release`.

---

## Features

- **P-010** · now · `/punchlist:brief [N]`: a read-only, plain-language catch-up — where the project
  stands, the last N finished units grouped into themes, and what's next — backed by a new
  `punchlist recent [--limit N] [--json]` command (closed units, newest first).

## Improvements

- **P-001** · next · End-to-end smoke of every skill through real headless invocations
  (`claude -p "/punchlist:<skill> …"`) against scratch repos, not just dry-run subagents.
- **P-003** · later · Automated skill regression suite via `claude plugin eval`, replacing hand-run
  dry-run scenarios.
- **P-004** · later · `lint` could check that `docs/README.md` (tidy's index) lists every current doc
  and that no current doc links into the archive.
- **P-007** · later · `_item_age_days` runs one `git blame` per line of an item (up to 5 per
  `later` item; compact calls it twice), and `punchlist queue` now runs after every
  `/punchlist:autonomous` unit — use one `git blame -L start,end` per item instead.
  `plugins/punchlist/lib/punchlist_core.py`. `from: P-006`
- **P-008** · later · `/punchlist:add` step 6 says "fix any ERROR" from `punchlist lint`, which
  can lead it to "fix" unrelated pre-existing errors (e.g. a stale snapshot); scope it to errors
  its own edit caused and report the rest, as `/punchlist:interview` now does. `from: P-006`

## Ops / manual

- **P-005** · later · List the plugin in community Claude Code plugin marketplaces once P-001 passes.
  `needs: action`
