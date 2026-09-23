---
name: tidy
description: Use when a project's docs, specs, plans, handoffs or notes may be stale, contradictory or scattered — after exploratory development, a rewrite or a pivot, when sessions keep building against outdated docs, after /punchlist:setup, or when asked to "clean up the docs". Works in projects with a .punchlist.yml.
argument-hint: "[path or focus]"
---

# Tidy the project's docs

Goal: every doc a future session might read is either **current**, **tracked as drifting**, or
**archived with the reason it's wrong**, and nothing is lost. Stale docs are the most dangerous
leftover in an AI-driven project, because a session reads a confident, outdated doc and builds a
design the project abandoned. Formats: `../../reference/formats.md` § Docs index, § Archive.

**Script:** `PL="${CLAUDE_PLUGIN_ROOT}/bin/punchlist"`. If that variable is empty, use
`<this skill's base directory>/../../bin/punchlist`. `<docs>` is `docs_dir` from `$PL config`.

**Precondition:** the project uses punchlist (`.punchlist.yml`, STATE, PUNCHLIST, build log). If not,
run `/punchlist:setup` first. Tidy files P-items and build-log rows, so it needs them to exist.

## Hard rules

- **Never delete, and never rewrite a doc's substance.** Allowed changes: `git mv` into the archive,
  a one-line banner, the index, link fixes, and P-items for rewrites. A rewrite is its own unit of
  work, done later through `/punchlist:next`.
- **Nothing moves before the user approves the triage table.**
- Skip vendored, generated and dependency docs (package READMEs under `node_modules`, `vendor`,
  fixtures and examples), generated or synced copies (e.g. an `AGENTS.md` that mirrors a
  `CLAUDE.md`), the punchlist-managed files (`managed`), and anything already in an archive folder.
  Record generated files in `.punchlist.yml` `docs_exclude`, and generated regions inside a doc
  (e.g. a `<laravel-boost-guidelines>` block) in `docs_ignore_tags`, so `punchlist docs` stops
  counting their references. Put that config change in the tidy commit.

## 1. Evidence

1. Run `$PL docs` for the per-folder summary. It shows where the files, the lines and the
   staleness signals are. Then run `$PL docs --under <folder>` for per-file rows in each folder that
   needs a look (`--json` for the full lists). Per file, the columns are:
   - `in`: inbound links from other docs
   - `dang`: references to missing paths, resolved forgivingly, so these are genuinely missing
   - `gone`: the subset that existed in git history, a **strong** staleness signal
   - `hist`: whether STATE or history files mention it
   - `cmts`: how many commit messages name it
2. Read the project's current truth: `CLAUDE.md`, `<docs>/STATE.md`, the build-log index table, and
   `git log --oneline -40`. These are what docs get checked against.
3. For each candidate doc, read enough to judge it: headings, its opening, and the claims about
   structure. Don't read 2,000-line plans end to end; use their dangling refs and their "Goal"/
   "Status" lines.

Signals of staleness, strongest first:
- It contradicts CLAUDE.md or the code: it describes concepts, tables or APIs that CLAUDE.md says
  were deleted, or that `grep` can't find.
- It has `gone` references: paths it describes that were deleted.
- It is old, nothing links to it (`in` 0, `hist` -), and it describes an earlier phase.

Plan checkboxes are **not** a signal, since many workflows never tick them. Age alone never makes a
doc stale; a stable doc can be old and correct.

**Batch plans and specs.** Don't judge dated plan and spec files one at a time. Group them by date
range and theme, then classify each group from the signals:
- `hist` yes or `cmts` ≥ 1 → shipped.
- Neither, but a merge or feat commit matches the topic (`git log --oneline --all | grep -i <topic>`)
  → shipped, and its build-log row is missing.
- Neither, and nothing matches → **?** (abandoned or pending).
- Shipped, but its `gone` count is high, or it builds on a model CLAUDE.md says was deleted →
  superseded.

Look at individual files only for the exceptions.

## 2. Classify every doc

Each doc gets exactly one verdict:

| Verdict | Criteria | Action |
|---|---|---|
| **current** | Accurate enough to build from | Keep; list it in the index |
| **drifting** | Its purpose and core model are still right, and specific sections are stale | Keep; a P-item names the stale sections (§ or heading, plus line refs for short docs), priority `next` (`now` if it's in STATE's Orientation); index status `drifting — P-###` |
| **superseded** | Its core model or purpose is gone: most of its structure describes deleted concepts, a replaced design, or an ended phase. This includes plans that shipped and were later deleted by a rewrite | `git mv` to `<docs>/archive/`; add an archive README row with what replaced it and what's wrong now ("shipped 2026-03-02, deleted by the 2026-03-10 rewrite") |
| **backlog** | Its content is open work (a TODO list, roadmap, unchecked plan items) | Migrate the items to PUNCHLIST (`from: <doc>`); then archive the doc or add a "Migrated" banner |
| **shipped plan/spec** | Implementation plan or spec for work that landed | Keep it in its folder; make sure the build-log index row links it. Add a row if the milestone is missing |
| **unfinished plan** | Started but not finished, still wanted | Keep it; a P-item points at it with what remains |
| **abandoned plan** | Never going to be built | Archive it: "abandoned YYYY-MM-DD: <why>" |
| **record** | A postmortem, research note, decision log or finished handoff: history people may cite | Keep in place; index status `done`. If it states decisions or facts that have since been reversed and a session could mistake it for current, add a one-line banner: `> Record as of <date>. Since changed: <what>, see <doc>.` |

**Mixed handoffs** (some items done, some open): migrate the open items to PUNCHLIST (backlog
action), then keep the doc as a **record** with the banner `> Open items moved to P-###…P-### on
<date>.`

When a verdict needs the owner's knowledge (e.g. whether a plan is abandoned or just paused), mark
it **?** and ask in the triage review. Don't guess.

## 3. Triage review — one table, wait for approval

Show a table sorted by verdict:

```
| Doc | Verdict | Evidence (1 line) | Action |
```

Then, separately: P-items to be filed (with priorities), archive moves, link fixes, and every **?**
row with its question. Wait for approval, and apply the user's edits to the table.

## 4. Apply (one commit)

1. **Archive:** `git mv` superseded and abandoned docs into `<docs>/archive/`, keeping their
   subfolders. Create or extend `<docs>/archive/README.md` using the formats.md table.
2. **Fix inbound links:** for every moved doc, update links in *current* docs to the new path, or
   remove the link and mention that it's archived. Leave links inside archived and history docs
   as they are.
3. **Backlog:** migrate items with `$PL next-id --bump` each, tagged `from:`.
4. **Drifting and unfinished:** file their P-items. Each drifting item lists the stale claims so the
   rewrite session doesn't have to rediscover them.
5. **Build log:** add missing index rows for shipped plans, marked "(row added by tidy)".
6. **Index:** write or refresh `<docs>/README.md` per formats.md, covering current, drifting and
   record docs plus a pointer to the archive.
7. **STATE Orientation:** make sure it names only current docs, and that it warns against the
   archive.
8. `$PL lint` (fix every ERROR), then re-run `$PL docs` to confirm no *current* doc has dangling
   references you introduced.
9. Commit only these files, as `docs: tidy — archive N, index M, file P-###…`, on the base branch.

## 5. Report

Give counts per verdict, the archived docs with one-line reasons, the P-items filed, and the answers
still needed. If more than a quarter of the current docs are drifting, say so plainly and suggest
rewriting the orientation docs first, since they're what every session reads.

## Re-running

Tidy is idempotent: archived docs are skipped, and existing drifting P-items are updated instead of
duplicated. Suggest re-running it after a rewrite or pivot, or when `$PL docs` shows dangling
references piling up in current docs.
