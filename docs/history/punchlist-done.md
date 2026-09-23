# PUNCHLIST — done

Closed items, moved out of [`../PUNCHLIST.md`](../PUNCHLIST.md) under their original section. Each is
followed by its own indented line `  — DONE YYYY-MM-DD (<sha>): <what shipped>`. Read by grep on ID only.

## Improvements

- **P-002** · next · `/punchlist:setup` **upgrade** mode (re-run with an existing `.punchlist.yml`)
  has never been exercised; test it and the managed-block re-sync.
  — DONE 2026-09-23 (no code change): exercised on a real adopted project via /punchlist:setup — block re-synced (2-line diff), text outside the markers untouched, lint clean. Also confirmed `${CLAUDE_PLUGIN_ROOT}` expands in SKILL.md at load.
