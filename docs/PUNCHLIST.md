# PUNCHLIST — the single backlog of open work

**Every not-done item lives here, and only here.** STATE.md points at IDs in this file. Done items
move to [`history/punchlist-done.md`](history/punchlist-done.md), and stale `later` items to
[`history/parked.md`](history/parked.md). Formats: `plugins/punchlist/reference/formats.md`.

## Conventions

- **ID** — `P-###`, never reused, never renumbered. Next free ID: **P-007**.
- **Priority** — `now` (blocking or next up), `next` (queued), `later` (parked or nice-to-have).
  One line per item plus ≤ 3 lines of context; link out for the rest.
- **Adding** — `/punchlist:add`, or append under the right section with `punchlist next-id --bump`.
- **Closing** — move the whole item to `history/punchlist-done.md` with
  `— DONE YYYY-MM-DD (<sha>): <what shipped>`. `/punchlist:next` does this. Ship with `just release`.

---

## Features

- **P-006** · now · `/punchlist:interview` (clear items that need the owner, PM-style briefs) and
  `/punchlist:autonomous` (serial subagent loop over `:next`), plus a `needs:` item marker and a
  `punchlist queue` command. Spec: `docs/specs/2026-09-25-interview-autonomous-design.md`.

## Improvements

- **P-001** · next · End-to-end smoke of every skill through real headless invocations
  (`claude -p "/punchlist:<skill> …"`) against scratch repos, not just dry-run subagents.
- **P-003** · later · Automated skill regression suite via `claude plugin eval`, replacing hand-run
  dry-run scenarios.
- **P-004** · later · `lint` could check that `docs/README.md` (tidy's index) lists every current doc
  and that no current doc links into the archive.

## Ops / manual

- **P-005** · later · List the plugin in community Claude Code plugin marketplaces once P-001 passes.
