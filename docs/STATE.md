# STATE — where the build is and what's next

> **The session-start doc.** Read this, then pick work from [`PUNCHLIST.md`](PUNCHLIST.md). This file
> is *position only*: no backlog (PUNCHLIST) and no build narrative
> ([`history/build-log.md`](history/build-log.md)). Keep it under ~120 lines.

## Snapshot — 2026-09-23

- **Branch:** `main` @ `c50c669`, clean. Sessions never push; the maintainer runs `just publish`.
- **Last shipped:** v0.4.0, the first public release.
- **In flight:** nothing.
- **Environment:** installed locally as `punchlist@punchlist`. Installs are cached per version (see Verbs).

## Next up

In priority order. Details live on the PUNCHLIST item.

1. P-001 — end-to-end skill smoke via real headless invocations.

## Orientation (read before substantive work)

1. `CLAUDE.md` — the agent contract for this repo.
2. [`design.md`](design.md) — what the plugin is and why.
3. `plugins/punchlist/reference/formats.md` — **normative** document formats. The script parses them
   and the skills follow them, so change them together.

## Where things are (system map)

| Area | Lives in | Notes |
|---|---|---|
| Plugin manifest | `plugins/punchlist/.claude-plugin/plugin.json` | `version` is bumped only by `just release` |
| Marketplace | `.claude-plugin/marketplace.json` | Name `punchlist` |
| Skills | `plugins/punchlist/skills/{setup,next,add,handoff,review,tidy}/SKILL.md` | Script fallback path: `<skill dir>/../../bin/punchlist` |
| Script | `plugins/punchlist/bin/punchlist` → `lib/punchlist_core.py` | Stdlib-only Python ≥ 3.9 |
| Formats + templates | `plugins/punchlist/reference/` | `formats.md` is normative |
| Tests | `tests/test_punchlist.py` | Throwaway git-repo fixtures; CI runs them on 3.9 and 3.13 |

## Verbs

- `just check` — tests plus manifest validation (the gate).
- `just release [patch|minor|major|X.Y.Z]` — checks, bumps the version, commits, tags, reinstalls
  locally and refreshes this snapshot. Needs a clean tree.
- `just publish` — pushes `main` and tags to GitHub (maintainer only).
- `just install` — first-time local install from this checkout.
- `plugins/punchlist/bin/punchlist --root <project> <cmd>` — run the script against any project.

## Gotchas that cost sessions time

- Installs are cached **per version**, so an unreleased change never reaches sessions. After
  `just release`, restart or run `/reload-plugins`.
- Skill wording changes need a before/after dry-run scenario (baseline vs with-skill).

## Recent milestones (last ~8 — full index in [`history/build-log.md`](history/build-log.md))

- 2026-09-23 — v0.4.0, first public release

## Maintaining this file

Refresh **Snapshot**, **Next up** and **Recent milestones** at the end of any session that merged
work or changed priorities (`/punchlist:handoff`). Never add backlog, rulings or narrative here.
