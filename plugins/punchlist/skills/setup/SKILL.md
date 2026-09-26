---
name: setup
description: Use when adding the punchlist / STATE / session-continuity system to a project (new or existing), when a project lacks handoff docs or a backlog and sessions keep losing the thread, or to upgrade a project already using the punchlist plugin.
argument-hint: "[docs dir]"
---

# Set up session-continuity docs in a project

Result: `.punchlist.yml`, `<docs>/STATE.md`, `<docs>/PUNCHLIST.md`,
`<docs>/history/{build-log,punchlist-done}.md`, and the managed block in `CLAUDE.md`. All of it
follows `../../reference/formats.md`, built from `../../reference/templates/`.

**Script:** `PL="${CLAUDE_PLUGIN_ROOT}/bin/punchlist"`. If that variable is empty, use
`<this skill's base directory>/../../bin/punchlist`.

## 1. Detect the mode

The project must be a git repo; for a brand-new folder, offer `git init`. Then:

| Found | Mode |
|---|---|
| `.punchlist.yml` exists | **Upgrade**: go to §6 |
| A STATE/PUNCHLIST-style pair already exists (any names; e.g. a `STATE.md` plus a backlog doc with IDs) | **Adopt**: normalize to the formats and keep the content (§4b) |
| An existing codebase with history or docs | **Seed**: build the docs from the repo (§4a) |
| An empty or near-empty repo | **New**: templates plus a short interview (§4c) |

## 2. Config — one confirmation, not an interview

Detect first, then confirm everything in **one** question:
- **docs_dir:** an existing `docs/` or `documentation/`, whichever has real content (prefer `docs/`
  if both do), else `docs`.
- **base_branch:** the **integration** branch, where finished work merges. That isn't necessarily the
  default or production branch. With a develop/master (or main/release) flow, it's the develop side.
  Check `git symbolic-ref refs/remotes/origin/HEAD`, `gh repo view --json defaultBranchRef`, the
  current branch, and the CI/deploy workflows. If pushing a branch triggers a release, it is **not**
  the base branch. Ask when it's ambiguous.
- **owner:** `git config user.name`.
- **push:** `never` unless the user says otherwise.
- **gates:** the project's real checks, from `justfile`, `Makefile`, `package.json` scripts,
  `composer.json`, `pyproject.toml`/`tox.ini`, `Cargo.toml`, `go.mod`, and CI workflows. Prefer what
  CI runs, but if CI runs no tests, derive the gates from the scripts. Every gate must be
  **non-interactive and terminating**: no watch mode, and pass `--watchAll=false`, `CI=1` and so on.
  Add a `when:` glob for a gate that only matters to one sub-app. **Run each proposed gate once.** A
  gate that fails on the current tree still goes in, but file the failure as a P-item. A gate that
  can't run here (a missing tool) goes in the report.
- **Project CLAUDE.md rules** such as "run X before committing" also belong in gates. Check that those
  commands are correct, and file a P-item for any that are wrong.

Write `.punchlist.yml` from `templates/punchlist.yml`, with `build_log_since` set to today. If the repo
has generated agent-doc mirrors (e.g. an `AGENTS.md` next to a `CLAUDE.md` with the same body) or
vendor-generated blocks in docs, add them to `docs_exclude` / `docs_ignore_tags`.

## 3. Read the project (Seed and Adopt)

Look at these as they exist; don't dump whole files:
- README and CLAUDE.md
- the docs tree (headings only)
- `git log --oneline -30`, and `git log --merges --format='%h %ad %s' --date=short -60`
- tags
- CI config
- a top-level tree with line counts

Backlog sources:
- `git status`: uncommitted or untracked work, which becomes an Ops / manual item
- branches and worktrees not merged into the base branch, which become Ops / manual items to land or
  delete
- TODO/ROADMAP/NOTES/BACKLOG-style files
- checklists in docs (`[ ]`)
- `TODO|FIXME|HACK|XXX` comments: count and cluster them, don't list each one
- open GitHub issues via `gh issue list --state open --limit 50 --json number,title,labels`, if `gh`
  is authenticated

## 4a. Seed: draft the docs

- **PUNCHLIST:**
  - Sections: the standard set from formats.md, omitting empty ones.
  - One item per real piece of work. Cluster code TODOs by theme or file into a few items with file
    refs.
  - Each item names its source: `from: TODO.md` or `from: #123` for migrated items, and
    `from: setup scan` for items found by inspecting the repo.
  - Items only the owner can move (a decision, credentials, publishing, a manual check) get
    `needs: decision` or `needs: action` (formats.md criteria).
  - Priorities: `now` only for what is clearly blocking or in progress. Old or speculative items are
    `later`.
  - IDs start at P-001.
- **Build log:**
  - An index table only: one row per merge, newest first, capped at ~40 rows. With a linear history
    (few real merges), make one row per feature cluster: consecutive commits on one theme, using the
    last commit as the Merge SHA. Skip "Merge branch …" noise.
  - No full entries for history. Pre-existing work stays out of the budget.
- **punchlist-done:** the template header.
- **STATE:**
  - Snapshot from git: the SHA is the last code commit (a merge commit is fine). If the tree is
    dirty, write `dirty (<what>)` instead of `clean`, and name it in In flight.
  - Next up: the top `now` items, or the top `next` items if nothing is `now`.
  - Orientation: the existing docs that matter, in reading order, with any "superseded; don't
    derive from" warnings the project already has.
  - A system map from the tree.
  - Verbs from the gates and scripts.
  - Recent milestones from the newest index rows.

## 4b. Adopt: normalize what exists

Keep every item and every piece of history; change only the shape.
- Map existing IDs onto `P-###` if they're already numbered and unique; otherwise assign new ones.
- Add the counter line and put priorities into now/next/later.
- Rename or move files to the standard paths only with the user's OK. Otherwise set `docs_dir` and
  keep the names, as long as the script can find them at `<docs>/STATE.md` and so on.
- Existing handoff or continuity prose in CLAUDE.md is **replaced** by the managed block (§5). Show
  the diff.

## 4c. New: minimal and honest

Fill the templates with what's known. Ask at most two questions: a one-line purpose, and the first 1–3
things to build, which become the first P-items. Leave the system map and gotchas as short
placeholders that the first sessions fill in.

## 5. Show, then write

Show the user:
- the proposed `.punchlist.yml`, with each gate's trial-run result
- a STATE preview (Snapshot + Next up)
- the PUNCHLIST sections and item counts, with a sample
- the build-log row count
- the CLAUDE.md change, noting that the block adds **workflow rules** as well as continuity rules:
  Planning weight (slicing is opt-in, drive to done, stop only for real forks). The user may ask to
  drop that half. If so, delete the `## Planning weight` part inside the block and note
  `planning_rules: false` in `.punchlist.yml`, so upgrades keep it out.

**Wait for approval.** Then:
- Write the files. Insert `templates/claude-md-block.md` into `CLAUDE.md` (create the file if it's
  missing), replacing `{{docs}}`, `{{state_lines}}` and `{{push_rule}}`. `{{push_rule}}` is either
  "Never push; <owner> pushes." or "Push after merging.". Placement: after the H1 and its first
  paragraph, or directly after the H1 if a heading follows it immediately, or at the top of a new
  file. Leave project-specific rules outside the markers untouched.
- Old backlog files that were fully migrated: don't delete them. Add a first line
  `> Migrated to <docs>/PUNCHLIST.md on <date>; kept for reference.`, and only with the user's OK.
- Run `$PL lint` and fix every ERROR.
- Commit **only the files setup wrote** (never unrelated dirty or untracked files) as
  `docs(punchlist): adopt punchlist continuity docs`, on the base branch. Setup only writes docs and
  config.

## 6. Upgrade (re-run)

- Replace the content between `<!-- punchlist:begin -->` and `<!-- punchlist:end -->` with the current
  template. Keep the project's docs path and push rule, and honor `planning_rules: false`.
- Create any standard file that's missing.
- **Legacy `**Waiting on …:**` line in STATE** (the format before `needs:`): tag each item it names
  `needs: decision` or `needs: action` in PUNCHLIST, by what the item asks of the owner, then delete
  the line. `lint` warns until it's gone.
- Report config keys whose defaults have changed.
- `$PL lint`, then commit as `docs(punchlist): upgrade punchlist block`.

## 7. Report and offer the review

Report what was created or changed, the item counts, the top of Next up, and the lint result. Then,
for Seed and Adopt, **offer** the two follow-ups. Don't run either unasked.
- **`/punchlist:tidy`**, offered first when the project has more than a handful of docs, specs or
  plans: "Some of these docs may be stale. Tidy checks each one against the code, archives
  superseded ones with the reason, and files rewrites as P-items. You approve the table before
  anything moves."
- **`/punchlist:review`**: "A whole-codebase review would give the punchlist a real starting audit.
  It runs parallel read-only reviewers and takes a while."

Setup itself never archives or rewrites existing docs. It only reads them, links the current ones
from Orientation, and migrates backlog-style files.
