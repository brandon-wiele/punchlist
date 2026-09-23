# STATE — where the build is and what's next

> **The session-start doc.** Read this, then pick work from [`PUNCHLIST.md`](PUNCHLIST.md). This file
> is *position only*: no backlog (PUNCHLIST) and no build narrative
> ([`history/build-log.md`](history/build-log.md)). Keep it under ~{{state_lines}} lines.

## Snapshot — {{date}}

- **Branch:** `{{base_branch}}` @ `{{sha}}`, {{tree_state}}. {{push_note}}
- **Last shipped:** {{last_shipped}}
- **In flight:** {{in_flight}}
- **Environment:** {{environment}}

## Next up

In priority order. Details live on the PUNCHLIST item.

1. {{next_1}}

**Waiting on {{owner}}:** {{waiting}}

## Orientation (read before substantive work)

1. `CLAUDE.md` — the agent contract.
{{orientation}}

## Where things are (system map)

| Area | Lives in | Notes |
|---|---|---|
{{system_map}}

## Verbs

{{verbs}}

## Gotchas that cost sessions time

{{gotchas}}

## Recent milestones (last ~8 — full index in [`history/build-log.md`](history/build-log.md))

{{milestones}}

## Maintaining this file

Refresh **Snapshot** (date, last *code* commit SHA, last shipped, in flight), reorder **Next up** by
PUNCHLIST ID, and roll **Recent milestones** to the newest ~8 at the end of any session that merged
work or changed priorities. `/punchlist:handoff` does this. Never add backlog, rulings or narrative
here.
