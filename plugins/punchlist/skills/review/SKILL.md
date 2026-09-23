---
name: review
description: Use when asked for a whole-codebase review, audit or health check ("how spaghettified is this", "review the codebase") in a project that has a .punchlist.yml, or when /punchlist:setup offers a first audit. Not for reviewing a single diff or PR.
argument-hint: "[focus or areas]"
---

# Whole-codebase review into `<docs>/code-review/`

Parallel read-only reviewers, one per area. Each writes one findings file. Then an index with a
generated roll-up, themes, a Fix-first table, and one umbrella PUNCHLIST item. Formats:
`../../reference/formats.md` § Code review files. Templates: `../../reference/templates/review-*.md`.

**Script:** `PL="${CLAUDE_PLUGIN_ROOT}/bin/punchlist"`. If that variable is empty, use
`<this skill's base directory>/../../bin/punchlist`. `<docs>` is `docs_dir` from `$PL config`.

## 1. Preconditions

- If `<docs>/code-review/` already has open findings (`$PL status`), ask whether to add a new dated
  review or to review only unreviewed areas. Never overwrite existing findings files. A new review
  uses fresh file numbers and area prefixes that don't collide with existing IDs.
- Record `git rev-parse --short HEAD` as the reviewed SHA.

## 2. Split into areas

Read `CLAUDE.md`, STATE's system map, and the repo tree with line counts (`git ls-files` plus
`wc -l`, excluding generated and vendored code). Choose **4–8 areas** of similar size along real
boundaries: apps/services, layers, packages. Always include one **cross-cutting** area covering
CI/tooling, test health, contract drift between components, config/secrets hygiene, and docs vs code.
Give each area:
- a number and slug (`03-api-integrations`)
- an uppercase ID prefix (`API-INT`)
- explicit paths
- 3–6 focus bullets specific to that area's risks

Also build a **do-not-flag** list from CLAUDE.md and the owner's recorded decisions: deliberate
choices a reviewer would otherwise report.

## 3. Brief and dispatch

Fill `review-brief.md` once and write it to the session's scratch area. It's shared by all
reviewers. Then dispatch one subagent per area **in a single message, in parallel, in the
background**. Each prompt is: "Read <brief path> and follow it exactly", plus the area key, prefix,
output path (`<docs>/code-review/NN-<slug>.md`), scope paths, and focus bullets. Use a capable model.
Stay within the session's subagent guideline, so merge areas if needed.

While they run, do nothing that conflicts with them. When each finishes, note its severity counts and
top items. Don't read whole files.

## 4. Index

Write `<docs>/code-review/README.md` from `review-readme.md`:
- **Files table:** file and scope only. Counts come from the generated roll-up; run
  `$PL status --write` after writing the file.
- **Strengths:** a short paragraph on what holds up.
- **Themes:** issues found by more than one reviewer, or several findings with one root cause.
  Name every member ID. Mark themes that need an owner ruling.
- **Fix first:** 8–12 rows. Order them as cheap unblockers (e.g. CI), then security, then
  correctness. For each row give the finding IDs, why it's first, and the effort. A row that needs a
  ruling says **Ruling needed** in "Why first".

## 5. Wire into the backlog

- Add one umbrella item with `$PL next-id --bump`, under a `## Code review (<date>)` section:
  `- **P-###** · now · Work the code-review Fix-first list — <docs>/code-review/README.md.`
- Findings stay in their own files. **Don't copy them into PUNCHLIST.** Promote a finding into its
  own P-item only if it's feature-sized.
- Put the umbrella at the top of STATE "Next up" unless something is blocking. Add owner rulings to
  the "Waiting on" line.
- `$PL lint`, fix every ERROR, and commit as `docs(code-review): <date> whole-codebase review
  (<N> findings)`.

## 6. Report

Give the total counts by severity, the themes as one line each (flagging rulings needed), and the
Fix-first list. Then give an honest overall-health paragraph: what's structurally sound, where
coupling or leftover code accumulates, and what to do about it. Offer to file structural
recommendations as P-items.
