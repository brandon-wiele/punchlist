# PUNCHLIST — the single backlog of open work

**Every not-done item lives here, and only here.** STATE.md points at IDs in this file. Done items
move to [`history/punchlist-done.md`](history/punchlist-done.md), and stale `later` items to
[`history/parked.md`](history/parked.md). Formats: `plugins/punchlist/reference/formats.md`.

## Conventions

- **ID** — `P-###`, never reused, never renumbered. Next free ID: **P-016**.
- **Priority** — `now` (blocking or next up), `next` (queued), `later` (parked or nice-to-have).
  One line per item plus ≤ 3 lines of context; link out for the rest.
- **Adding** — `/punchlist:add`, or append under the right section with `punchlist next-id --bump`.
- **Waiting on the owner** — tag the item `` `needs: decision` `` or `` `needs: action` ``
  (formats.md has the criteria). `/punchlist:interview` clears them; sessions skip them.
- **Closing** — move the whole item to `history/punchlist-done.md` with
  `— DONE YYYY-MM-DD (<sha>): <what shipped>`. `/punchlist:next` does this. Ship with `just release`.

---

## Improvements

- **P-011** · later · Eval suite slice 2, after P-014: cases for setup upgrade, tidy, interview,
  autonomous (`slow`) and review (`slow`). Spec `docs/specs/2026-09-26-eval-suite-design.md`. `from: P-001`
- **P-013** · later · Once the eval smoke suite runs and passes (P-014): replace CLAUDE.md rule 4's
  hand-run dry runs with `just eval`, and match `docs/design.md` Testing. `from: P-001`
  Ruling 2026-09-26: yes, switch rule 4 to `just eval` — the owner's call on a contract change.

## Ops / manual

- **P-014** · later · Get the eval smoke suite running. Here `claude plugin eval` refuses Bash-granting
  runs: `~/.docker` holds a symlink its sandbox can't exclude. Fix that (`find ~/.docker -type l`), then
  finish branch `punchlist/P-001-eval-slice-1` from plan task 1 (spike; six cases written, unrun).
  `needs: action` `from: P-001`
- **P-005** · later · List the plugin in community Claude Code plugin marketplaces once P-001 passes.
  `needs: action`
