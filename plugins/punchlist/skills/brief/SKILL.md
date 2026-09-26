---
name: brief
description: Use when the owner wants to catch up on a project that has a .punchlist.yml — "brief me", "where are we", "what did we do last time", "catch me up", or coming back after a break. A read-only, plain-language overview of where the project stands, what was built recently, and what's next.
argument-hint: "[N units]"
---

# Brief the owner

Goal: someone coming back after a day or a month understands, in one read, where the project
stands, what got built lately and why it matters, and what happens next. Write for a smart owner
who hasn't been in the code: plain language, full sentences, no walls of IDs or SHAs. This skill is
**read-only**: it writes nothing and commits nothing. Formats: `../../reference/formats.md`
(relative to this skill's base directory).

**Script:** `PL="${CLAUDE_PLUGIN_ROOT}/bin/punchlist"`. If that variable is empty, use
`<this skill's base directory>/../../bin/punchlist`. `<docs>` is `docs_dir` from `$PL config`.
The argument is how many finished units to cover; the default is 5.

If there's no `.punchlist.yml`, stop and suggest `/punchlist:setup`.

## 1. Gather — quietly, don't narrate it

- `$PL config`. Read `<docs>/STATE.md` whole, and the opening paragraph of the project's README (or
  of CLAUDE.md, if there's no README) for what the project is.
- `$PL recent --json --limit <N>`: the last N finished units, newest first. A unit is a backlog item
  closed as done, or a code-review finding marked fixed.
- For each unit with a `sha`, grep `<docs>/history/build-log.md` for that SHA. If an entry mentions
  it, read that entry: its **Why** and **What shipped** are your best source. Otherwise use the
  unit's `text` and `note`; if they're too thin to explain, `git show --stat <sha>`.
- Take the newest unit that has a `sha` (units done by hand have none):
  `git log --oneline <sha>..HEAD -- . ':(exclude)<docs>'` lists code changes since then that belong
  to no unit. If no unit has a `sha`, skip this.
- `$PL queue --json` for what's workable, what needs the owner, and what's due for triage. The first
  `workable` entry is what `/punchlist:next` would pick. For the top workable items, skim the spec or
  plan they link to, if any, to judge their size.
- `git status --short`, the current branch, `$PL lint` (just the counts), and the latest release
  tag (`git describe --tags --abbrev=0`) if the project uses tags.

## 2. Write the brief

Three short sections under plain headings, roughly 250–450 words in all. Use full sentences. IDs appear
only as footnotes in parentheses, like "(P-006)", never as the subject of a sentence. Leave SHAs out
unless the owner has to act on one.

**Where things stand.** Two to four sentences. What the project is, in a line. The latest release
and whether it's published, if STATE says. What's mid-flight: explain STATE's In flight, don't paste
it. Anything unhealthy: uncommitted changes, lint errors, being on a branch other than the base
branch.

**What we built lately.** Group the N units into one to three themes by what they served (say,
"Letting the backlog run itself"), not by ID. For each theme, write a short paragraph: what exists
now that didn't before, and why it matters to the owner, with the units as footnotes. Call out
anything that shipped with a caveat, such as a DONE note saying what wasn't verified. If there are
code changes since the newest unit, add one line: "Also changed since then: …" in plain words. If
there are no finished units yet, say so and summarize the recent git history instead.

**What's next.** The top one to three workable items: what each is, in plain terms, and roughly how
big. Say which one `/punchlist:next` would pick. Then what's waiting on the owner (a count and a
one-line headline each), with a pointer to `/punchlist:interview` if anything is. Then how many items
are due for triage, if any. If nothing is workable and nothing waits on the owner, say the backlog
is clear.

End with one line suggesting the next command to run.

## Common mistakes

| Mistake | Instead |
|---|---|
| Pasting STATE lines or item text | Rewrite it in plain language |
| Leading with IDs or SHAs | Lead with what happened; IDs are footnotes |
| One bullet per unit or commit | Group units into a few themes |
| Terse fragments | Full sentences that someone returning cold can follow |
| Judging by eye what waits on the owner | Use `queue`'s `needs` group; it reads the markers exactly |
| Guessing at progress the docs and git don't show | Report only what the sources show; say when something is unclear |
| Editing docs, tagging items or committing | Read-only: suggest the command that would do it instead |
