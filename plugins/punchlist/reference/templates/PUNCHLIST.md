# PUNCHLIST — the single backlog of open work

**Every not-done item lives here, and only here.** STATE.md points at IDs in this file. Done items
move to [`history/punchlist-done.md`](history/punchlist-done.md), and stale `later` items to
[`history/parked.md`](history/parked.md). Formats: the punchlist plugin's `reference/formats.md`.

## Conventions

- **ID** — `P-###`, never reused, never renumbered. Next free ID: **{{next_id}}**.
- **Priority** — `now` (blocking or next up), `next` (queued), `later` (parked or nice-to-have).
  One line per item plus ≤ 3 lines of context; link out for the rest.
- **Adding** — `/punchlist:add`, or append under the right section with `punchlist next-id --bump`.
  Deferrals from shipped work get their own item, tagged `from:`.
- **Waiting on the owner** — tag the item `` `needs: decision` `` or `` `needs: action` ``
  (formats.md has the criteria). `/punchlist:interview` clears them; sessions skip them.
- **Closing** — move the whole item to `history/punchlist-done.md` with
  `— DONE YYYY-MM-DD (<sha>): <what shipped>`. `/punchlist:next` does this.

---

{{sections}}
