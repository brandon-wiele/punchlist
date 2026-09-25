---
name: handoff
description: Use when ending a work session, wrapping up, or before the context is cleared in a project that has a .punchlist.yml — especially after feature work, exploration or fixes done outside /punchlist:next — or when the user asks to "hand off", "update STATE", or "tidy the punchlist".
---

# End-of-session handoff

Goal: a cold session tomorrow can read STATE + PUNCHLIST and know exactly where things stand and
what to do next. Formats: `../../reference/formats.md`.

**Script:** `PL="${CLAUDE_PLUGIN_ROOT}/bin/punchlist"`. If that variable is empty, use
`<this skill's base directory>/../../bin/punchlist`. `<docs>` is `docs_dir` from `$PL config`.

## 1. Gather what this session did

- Run `git status`. Then list this session's code commits with
  `git log --oneline <snapshot-sha>..HEAD -- . ':(exclude)<docs>'`, where the snapshot SHA is the one
  in STATE's Snapshot.
- Review this conversation for work done, decisions made, things deferred, and bugs noticed.
- Read `<docs>/STATE.md` and `<docs>/PUNCHLIST.md` whole.

## 2. Apply the five handoff steps

1. **Deferred, discovered or half-done → P-items.** Get each new ID from `$PL next-id --bump`. Tag it
   `from:`, and `needs: decision|action` if only the owner can move it (formats.md criteria).
   Half-done work gets a progress note on its existing item.
2. **Finished → retire.** Only if the work's commits passed the `.punchlist.yml` gates: run them now
   if this session didn't. A failing gate means it isn't done; record that in In flight. Move the item
   to `history/punchlist-done.md` under its section heading, followed by its own line
   `  — DONE YYYY-MM-DD (<sha>): …`. For findings, set `Status: fixed <sha>`.
3. **Merged → build log.** Add an index row plus an entry of ≤ 15 lines, but only for changes to
   user-visible behavior, security or a contract. Rulings made this session go into the entry, or
   into the spec's Rulings section.
4. **STATE.** Refresh the Snapshot:
   - the date
   - the last *code* commit's SHA
   - Last shipped
   - In flight

   Order Next up as formats.md says (`now` first, then what unblocks most), naming items by ID; items tagged `needs:` stay out of it. Roll Recent milestones to the
   newest ~8. Move out anything that isn't *position*: backlog goes to PUNCHLIST, narrative to the
   build log.
5. **Mid-flight work.** If a branch or uncommitted change remains, the Snapshot's In flight must
   name:
   - the branch
   - what's done
   - the exact next command or step
   - any uncommitted state

   That line is the whole handoff for an interrupted session.

## 3. Keep it small

- `$PL status --write` if findings changed.
- `$PL compact` shows a diff that collapses closed findings and parks stale `later` items. Apply it
  with `$PL compact --apply` unless the diff parks something discussed this session. Leave those in
  place.
- `$PL lint`. Fix every ERROR. For WARNs, fix what's cheap and list the rest in the report.

## 4. Commit and report

Commit the bookkeeping as `docs(punchlist): session handoff — <one-line gist>` on the current
branch. Never commit unrelated code changes in it; if some are uncommitted, leave them and name them
in In flight.

Report in ≤ 10 lines:
1. What was recorded.
2. What was retired.
3. New P-IDs.
4. The top of Next up.
5. Anything waiting on the owner.
6. The lint result.
