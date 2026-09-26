# STATE — where the build is and what's next

> **The session-start doc.** Read this, then pick work from [`PUNCHLIST.md`](PUNCHLIST.md). This file
> is *position only*: no backlog (PUNCHLIST) and no build narrative
> ([`history/build-log.md`](history/build-log.md)). Keep it under ~120 lines.

## Snapshot — 2026-09-26

- **Branch:** `main` @ `eb4b4f8`, clean. Sessions never push; the maintainer runs `just publish`.
- **Last shipped:** v0.7.3 (directory URLs, README Privacy), v0.7.2 (plugin icon) and v0.7.1 (author, marketplace owner and LICENSE now
  Brandon Wiele) on v0.7.0 — lint checks the docs index and archive links, faster item ages, `:add`/
  `:review`/`:tidy` fix only lint errors they caused, README rewritten for adopters, directory-ready
  plugin metadata. Released locally, not yet published (`just publish`).
- **In flight:** nothing active. The eval-suite work in progress is parked on branch
  `punchlist/P-001-eval-slice-1` (six cases written, none run); P-014 picks it up.
- **Environment:** installed locally as `punchlist@punchlist`. Installs are cached per version (see Verbs).

## Next up

In priority order. Details live on the PUNCHLIST item. Items tagged `needs:` aren't listed here —
see `punchlist queue`.

Nothing is workable: everything left is `later` or waits on the owner — see `punchlist queue`.

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
| Skills | `plugins/punchlist/skills/{setup,next,autonomous,interview,brief,add,handoff,review,tidy}/SKILL.md` | Script fallback path: `<skill dir>/../../bin/punchlist` |
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
  `just release`, restart the session: `/reload-plugins` refreshes the plugin but doesn't register
  skills added in the new version.
- Skill wording changes need a before/after dry-run scenario (baseline vs with-skill).
- Subagents load the installed plugin, not this checkout. To dry-run changed skill text, tell the
  agent to read and follow the checkout's SKILL.md and set PL to the checkout's bin/punchlist.

## Recent milestones (last ~8 — full index in [`history/build-log.md`](history/build-log.md))

- 2026-09-26 — v0.7.0: lint checks the docs index and archive links (P-004), README for adopters
- 2026-09-26 — P-010: /punchlist:brief, a plain-language catch-up, and `punchlist recent` (v0.6.0)
- 2026-09-25 — P-006: /punchlist:interview and /punchlist:autonomous, needs: marker, punchlist queue (v0.5.0)
- 2026-09-23 — v0.4.0, first public release

## Maintaining this file

Refresh **Snapshot**, **Next up** and **Recent milestones** at the end of any session that merged
work or changed priorities (`/punchlist:handoff`). Never add backlog, rulings or narrative here.
