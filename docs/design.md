# punchlist — design

_2026-09-23._

## Problem

Long-running, exploratory projects driven by many AI sessions lose the thread: nobody knows where the
build is, what's next, what was deferred, or what already shipped. This plugin packages a system of lean living documents and strict handoff rules so any project can
adopt it in one command, and so its maintenance is mostly mechanical.

## Principles

1. **One job per file, one home per item.** An item's status lives in exactly one place. There is
   no separate ledger; a second copy would drift.
2. **Hot vs cold.** Only `STATE.md` and `PUNCHLIST.md` are read whole every session. Everything else
   is cold and read by ID lookup (grep), never whole.
3. **Counts are computed, never typed.** A script derives every open/done number.
4. **Budgets are checked, not hoped for.** `lint` enforces sizes and consistency; `compact` shrinks
   what's closed.
5. **Sessions act; the plugin supplies the rules.** Skills carry the procedure; the project carries
   only a small config.

## Components

| Component | Role |
|---|---|
| `.punchlist.yml` (project root) | Per-project config: docs dir, base branch, branch prefix, push policy, owner, gate commands (optionally path-conditional), budgets |
| `reference/formats.md` | The single normative definition of every document format, ID scheme, status vocabulary and read rule |
| `reference/templates/` | Starting files that setup copies in: STATE, PUNCHLIST, build-log, punchlist-done, parked, the CLAUDE.md block, the review README, and the reviewer brief |
| `bin/punchlist` | Python 3 (stdlib only) CLI: `status`, `lint`, `next-id`, `compact`, `config`, `docs` |
| `skills/setup` | Scaffold a new project or seed an existing one from its repo; idempotent re-run upgrades the managed CLAUDE.md block and adds missing files |
| `skills/next` | Work one backlog unit end to end: pick → build → gates → merge → retire |
| `skills/handoff` | End-of-session routine + lint + compact |
| `skills/review` | Parallel whole-codebase review into `code-review/`, with generated roll-up and an umbrella P-item |
| `skills/add` | Quick capture of a backlog item |
| `skills/tidy` | Triage existing docs (current / drifting / superseded / backlog / plans) against the code; archive with reasons, index, rewrite P-items. Evidence from `punchlist docs` |

## Managed CLAUDE.md block

Setup inserts the Session-continuity and Planning-weight rules into the project's `CLAUDE.md`
between `<!-- punchlist:begin -->` and `<!-- punchlist:end -->`. A re-run replaces only that block.
Project-specific rules stay outside it.

## Script contract

- `punchlist config` — print the resolved config (defaults filled) as JSON.
- `punchlist status [--write]` — counts: P-items open by priority/section, done; findings open/closed
  per file and severity. `--write` rewrites the roll-up between
  `<!-- punchlist:status:begin -->`/`end` in `code-review/README.md`.
- `punchlist next-id [--bump]` — the next free P-ID; `--bump` increments the counter in PUNCHLIST.md.
- `punchlist lint` — `ERROR`/`WARN` lines with file:line; exit 1 on any ERROR. Checks: STATE and
  PUNCHLIST line budgets; build-log entry length; STATE snapshot SHA exists and no code commits
  landed after it; P-ID both open and done; duplicate P-IDs; counter ≤ max ID; invalid finding status;
  `later` items older than the stale threshold (WARN); Next up naming a done item; malformed items;
  items over 5 lines (WARN); a snapshot claiming `clean` while *code* is uncommitted (WARN).
- `punchlist docs [--under P] [--json]` — evidence for tidy: per-folder summary or per-file rows: lines,
  last change, inbound links, dangling refs (forgivingly resolved) and the subset that existed in git
  history, whether history files mention it, commit-message mentions.
- `punchlist compact [--apply]` — collapse closed findings to one heading line; move stale `later`
  items to `history/parked.md`. Prints a unified diff; writes only with `--apply`.

Config parsing uses a small YAML subset (scalars, nested maps, lists of scalars/maps) so the tool has
no dependencies.

## Testing

Unit tests for the script against fixture docs (`tests/`). Skills are tested by dry-run subagent
scenarios against scratch repos (baseline without skill vs with skill), then by piloting it on a
large, long-running project.

## Out of scope

Hosted services; GitHub-issue sync (setup imports issues once, as seed
material); non-git projects.
