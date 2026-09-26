---
name: next
description: Use when asked to work the next backlog / punchlist item, act on a specific P-### item or code-review finding ID, or pick up where the last session left off, in a project that has a .punchlist.yml.
argument-hint: "[P-### | finding-ID]"
---

# Work the next punchlist item

One invocation = **one unit of work**, from pick through merge and bookkeeping. The formats are in
`../../reference/formats.md` (relative to this skill's base directory); follow them exactly, because
a script parses them.

**Script:** `PL="${CLAUDE_PLUGIN_ROOT}/bin/punchlist"`. If that variable is empty, use
`<this skill's base directory>/../../bin/punchlist`. Run `$PL config` first: it gives `docs_dir`,
`base_branch`, `branch_prefix`, `push`, `owner`, `gates`. `<docs>` below means `docs_dir`.

If there's no `.punchlist.yml`, stop and suggest `/punchlist:setup`.

## 1. Orient

Read `<docs>/STATE.md` and `<docs>/PUNCHLIST.md` whole. For a code-review unit, also read
`<docs>/code-review/README.md` and grep the finding by ID. **Don't read history files or other
review files whole.**

Run `git status` and `git log --oneline -5`. If tracked files are modified or you're not on
`base_branch`, stop and report it. Unrelated untracked files are fine.

## 2. Pick the unit

| Situation | The unit is |
|---|---|
| Argument given | That item or finding. If it carries `needs:`, or only the owner can do it, say so and stop. |
| No argument | The first `workable` entry of `$PL queue --json` (Next up, then `now`, then `next`; items tagged `needs:` and `later` items are excluded) |
| The item is an **umbrella** (points at a code-review Fix-first table) | The first Fix-first row whose findings aren't all closed |
| Only the owner can do it (formats.md § `needs:` criteria) | **Skip it**: tag it `needs: decision` or `needs: action`, stating the question or task plainly in the item; name it in the report; move on |
| A choice comes up that doesn't meet those criteria | Decide it, record `Ruling YYYY-MM-DD: …` on the item (or in the spec's Rulings), keep going |
| A finding is `needs-ruling:`, or the fix would change a documented contract in CLAUDE.md | Skip it; set its Status to `needs-ruling: <question>` if it isn't already; put the question in the report |

State the pick and why in one line, then proceed. Don't ask for confirmation.

## 3. Size it, then do it

Follow CLAUDE.md § Planning weight: small → no spec or plan; medium → a short plan. If the code
shows the unit is **large** (more than one session, or more than ~15 tasks), don't start it. Write or
refine its spec/plan, file the pieces as new P-items if useful, and report. That counts as the unit.

- Branch: `git switch -c <branch_prefix><id>-<slug>` from `base_branch`.
- For a code-review finding, **re-read the cited code first**. It may already be fixed or be wrong;
  if so, set the Status (`fixed <sha>` / `wontfix: <why>`) and pick again.
- Use TDD (`superpowers:test-driven-development` if available); for bugs, debug systematically.
- Never run destructive or irreversible commands the project's CLAUDE.md forbids. Push only if
  `push: allowed`.
- **Gates:** run every `gates[].run`. An entry with `when: <glob>` runs only if the branch diff
  touches a matching path. All must pass before committing. If a gate fails for unrelated reasons,
  report it; don't paper over it.
- If the fix changes how developers work (a gate now needs a service, a new env var, a new command),
  do it and call it out under "Needs you".
- Commit with the ID in the message: `fix(area): … (<ID>)`.

## 4. Retire it — a separate bookkeeping commit on the same branch

Record the SHA of the last code commit (`git rev-parse --short HEAD`). Then:

- **Resolved P-item:** cut the whole entry from PUNCHLIST and paste it into
  `<docs>/history/punchlist-done.md` under the heading with the same name as its PUNCHLIST section
  (create the heading at the end of the file if missing). Add the line
  `  — DONE YYYY-MM-DD (<sha>): <one line>` right after it.
- **Code-review finding:** set its `- **Status:**` to `fixed <sha>`, using the commit that fixed
  *that* finding. When every finding in a Fix-first row is closed, set that row's `#` cell to `✅`
  and append ` — fixed <sha(s)>` to "Why first".
- **Umbrella item:** stays in PUNCHLIST until its last row closes, with no progress notes there.
  When the last row closes, retire it like any P-item.
- **Partly done:** leave it open and add `(YYYY-MM-DD: <done> <sha or "uncommitted">; <remains>)`.
- **Anything discovered, deferred, or needing the owner:** create a new item with
  `$PL next-id --bump`, put it in the right section, and tag it `from: <this ID>`, plus
  `needs: <kind>` if only the owner can move it.
- **STATE.md:** refresh the Snapshot with the last *code* commit's SHA (later bookkeeping commits
  don't count), plus Last shipped and In flight. Update "Next up" if its head changed.
- **Build log + Recent milestones:** only if the unit changed user-visible behavior, a security
  property, or a contract. Add a build-log index row plus an entry of ≤ 15 lines, and roll STATE's
  milestones.
- If findings changed: `$PL status --write`.
- Run `$PL lint` and fix every ERROR before committing. Commit as `docs(punchlist): …`.

Then `git switch <base_branch> && git merge --ff-only <branch>` and delete the branch. Push only if
`push: allowed`.

## 5. Report — this is the whole output

1. **Did:** the ID, what changed, and the SHAs.
2. **Verified:** the gates and their results, plus anything that can't be verified locally.
3. **Retired / updated:** which bookkeeping entries moved or changed.
4. **Needs you:** items tagged `needs:` or `needs-ruling:` this unit, and new P-items filed.
5. **Next:** what the next invocation would pick.

## Common mistakes

| Mistake | Instead |
|---|---|
| Doing several items in one invocation | One unit, then report |
| Asking "continue?" or "what counts as done?" | The rules above answer it |
| `<sha>` placeholders, or retiring before the gates pass | Commit the code first, then write the real SHA |
| Deleting a done item | Move it to punchlist-done with the DONE line |
| Typing counts into the README by hand | `$PL status --write` |
| Reading the whole build log or every review file | Look up by ID |
