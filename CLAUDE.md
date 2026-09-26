# punchlist — agent contract

This repo is the `punchlist` Claude Code plugin: session-continuity skills plus a stdlib Python
script. It dogfoods itself, so its own backlog lives in `docs/PUNCHLIST.md`.

<!-- punchlist:begin — managed by the punchlist plugin (/punchlist:setup re-syncs this block; edit outside it) -->
## Session continuity

Future sessions start cold. **Read `docs/STATE.md` before substantive work.** These files carry
everything a session needs. Each has exactly one job, and nothing is recorded in two of them.

| File | One job | Budget |
|---|---|---|
| `docs/STATE.md` | Position: snapshot (date, last code SHA, last shipped, in flight), **next up** as P-IDs, orientation, verbs, gotchas | ≤ ~120 lines |
| `docs/PUNCHLIST.md` | **The only backlog.** Every open bug, feature, deferral, manual step and ops task, as `P-###` items | 1–4 lines per item |
| `docs/history/build-log.md` | What shipped: an index row plus one entry per merge, linking spec/plan | ≤ 15 lines per entry |
| `docs/history/punchlist-done.md` · `parked.md` | Closed items · stale `later` items | read by grep only |

Only STATE and PUNCHLIST are read whole. Everything else is looked up by ID. Code-review findings
(if any) live in `docs/code-review/` with a `Status:` line that is updated in place. Counts come
from `punchlist status`, never typed by hand. Rulings go into the spec or the build-log entry, never
STATE.

**Handoff — before ending any session that changed code or priorities** (`/punchlist:handoff`):
1. Anything deferred, discovered or half-done becomes a PUNCHLIST item with a new ID. "Recorded in
   the spec" isn't enough: if a future session should act on it, it needs an ID.
2. Anything finished moves its item to `punchlist-done.md` with `— DONE <date> (<sha>): …`.
3. Anything merged gets a build-log index row plus a short entry.
4. Refresh STATE's Snapshot, Next up and Recent milestones.
5. Work still mid-flight on a branch goes in STATE's Snapshot: the branch, what's done, the exact
   next step, and any uncommitted state.

Workflow skills: `/punchlist:next [P-###|finding-ID]` works one backlog unit end to end ·
`/punchlist:autonomous [max]` works units unattended, one at a time ·
`/punchlist:interview` clears items waiting on the owner · `/punchlist:brief` catches you up ·
`/punchlist:add` captures an item · `/punchlist:handoff` closes a session · `/punchlist:review`
audits the codebase · `/punchlist:tidy` triages stale docs (archive, index, rewrite P-items).
**Don't build from anything in `docs/archive/`.**

## Planning weight — size the process to the change

Pick the lightest process that fits. **Slicing is not a default.**
- **Small** (a bug fix, a tweak, a contained change): no spec or plan doc. Do it with tests.
- **Medium** (touches a couple of subsystems, ≤ ~15 tasks): one spec (skip it if the design is
  obvious) plus one plan, on one branch, merged once.
- **Large:** split into slices **only** when the parts ship independently and each leaves the base
  branch coherent, or when one plan is too big to review in one pass. Say why in the spec.

Whatever the size, plan up front and drive through to done. Stop only for a genuine fork you can't
resolve from the spec or code; record everything else as a ruling and keep going. Never push; the maintainer publishes with `just publish`.
<!-- punchlist:end -->

## Repo rules

1. **`just check` before every commit.** `just release` is the only way the plugin version changes.
2. **`reference/formats.md` is normative.** A format change updates, in the same commit: formats.md,
   the parser in `lib/punchlist_core.py`, its tests, and every skill and template that writes that
   format.
3. **The script stays stdlib-only** (Python ≥ 3.9) and never writes without an explicit flag
   (`--write`, `--bump`, `--apply`).
4. **Test first for script changes.** For skill wording changes, run a dry-run scenario with and
   without the change; see `superpowers:writing-skills`.
5. **No project-specific assumptions in skills or script.** Anything that differs per project belongs
   in `.punchlist.yml`.
