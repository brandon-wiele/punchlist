# PUNCHLIST — done

Closed items, moved out of [`../PUNCHLIST.md`](../PUNCHLIST.md) under their original section. Each is
followed by its own indented line `  — DONE YYYY-MM-DD (<sha>): <what shipped>`. Read by grep on ID only.

## Improvements

- **P-002** · next · `/punchlist:setup` **upgrade** mode (re-run with an existing `.punchlist.yml`)
  has never been exercised; test it and the managed-block re-sync.
  — DONE 2026-09-23 (no code change): exercised on a real adopted project via /punchlist:setup — block re-synced (2-line diff), text outside the markers untouched, lint clean. Also confirmed `${CLAUDE_PLUGIN_ROOT}` expands in SKILL.md at load.

## Features

- **P-006** · now · `/punchlist:interview` (clear items that need the owner, PM-style briefs) and
  `/punchlist:autonomous` (serial subagent loop over `:next`), plus a `needs:` item marker and a
  `punchlist queue` command. Spec: `docs/specs/2026-09-25-interview-autonomous-design.md`,
  plan: `docs/plans/2026-09-25-interview-autonomous.md`.
  — DONE 2026-09-25 (b9d6544): /punchlist:interview + /punchlist:autonomous, needs: marker, punchlist queue.

## Ops / manual

- **P-009** · now · Release and dogfood P-006 with the maintainer: `just release minor`,
  `/reload-plugins`, run `/punchlist:interview` on this repo, then `/punchlist:autonomous 2`
  with the maintainer saying "stop" mid-unit (checks: research subagents return every brief
  field; AskUserQuestion accepts `preview`; owner stop). Plan:
  `docs/plans/2026-09-25-interview-autonomous.md` Task 8. `needs: action` `from: P-006`
  — DONE 2026-09-26 (manual): v0.5.0 released; live /punchlist:interview run (preview accepted); owner closed it without the autonomous owner-stop run or a live research-subagent check.
