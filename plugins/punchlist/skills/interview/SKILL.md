---
name: interview
description: Use when the owner wants to clear punchlist items that wait on them — decisions, code-review rulings, manual/ops tasks, or stale `later` items to triage — in a project that has a .punchlist.yml (e.g. "/punchlist:interview", "what do you need from me", "clear the deck"), or after /punchlist:autonomous stops on items that need the owner.
argument-hint: "[P-### … | decisions | actions | triage]"
---

# Interview the owner on what waits on them

Goal: every item that needs the owner gets an informed answer, recorded so a session can act on it.
Act as a product manager with a strong engineering background: do the homework, put the choice in
plain language with honest trade-offs, recommend one option, and record the answer precisely.
Formats: `../../reference/formats.md` (relative to this skill's base directory).

**Script:** `PL="${CLAUDE_PLUGIN_ROOT}/bin/punchlist"`. If that variable is empty, use
`<this skill's base directory>/../../bin/punchlist`. `<docs>` is `docs_dir` from `$PL config`.

If there's no `.punchlist.yml`, stop and suggest `/punchlist:setup`.

## 1. Preflight

Run `git status`. If any tracked file is modified, stop and say so: this skill commits its
bookkeeping on the current branch and must not tangle it with other work, including unrelated doc
edits.

## 2. Build the queue

- Run `$PL queue --json`. Take `needs` (kinds `decision`, `action`, `ruling`) and `triage`. An
  argument narrows it: specific IDs, or one group (`decisions` = decision + ruling, `actions`,
  `triage`).
- If STATE still has a legacy `**Waiting on …:**` line, treat every item it names as an owner
  candidate (below), then delete the line.
- Read `<docs>/PUNCHLIST.md` whole and look for **untagged** items only the owner can move: the
  Ops / manual section, or wording like decide, choose, confirm, approve, sign off, credentials,
  publish. Ask about those first, up to 4 per `AskUserQuestion` call, one question per item: "Does
  this need you?", with the options **Needs your decision** · **Needs you to do it** · **No — a
  session can do it**. Tag the first two answers `needs: decision` or `needs: action` and add those
  items to the queue, removing them from STATE's Next up if listed; leave the rest untouched.
- A tagged `decision` that fails the formats.md criteria for `needs: decision` stays in the queue, but
  its recommended option is **"Your call"**: you decide, record the ruling, and remove the tag.
- **Empty queue:** report "Nothing needs you — <N> items are workable." and suggest
  `/punchlist:autonomous` if N > 0. Stop.

## 3. Research before asking

For each `decision` and `ruling` entry, dispatch a **read-only** analysis subagent (the `Plan` agent
if available, otherwise general-purpose). Send them all in one message so they run in parallel. Give
each the entry's JSON, the project root and this brief:

> Research this backlog item so the owner can decide it in under a minute. Read what it links to
> (spec, plan, code, the code-review finding), its history (`git log -S` / `--grep`), and any
> PUNCHLIST item whose `from:` names it. Don't edit anything. Reply with exactly:
> - **Headline:** the decision as a plain-language question a PM would ask. No IDs, no jargon.
> - **Context:** 2–4 sentences: what exists today, what's missing or broken, who notices.
> - **Blocks:** what waits on this answer (items, features, releases), or "nothing yet".
> - **Options:** 2–3. For each: a 1–5 word label; what we'd build; engineering cost (S/M/L and
>   why); risk; how reversible it is.
> - **Recommendation:** one option, and why, in one or two sentences.
> - **After:** for each option, what happens next (what gets built, filed or unblocked).

Brief `action` and `triage` entries yourself, from the item text and the `git log` of its lines. No
subagent.

## 4. Ask in batches

Order: decisions and rulings first, the ones blocking the most work first; then actions; then
triage. Ask up to 4 questions per `AskUserQuestion` call.

Before each call, print each question's brief in chat:

```
### <Headline>
<Context> · Blocks: <Blocks>
**Recommend: <label>** — <reason>
_P-### · <section>_
```

The ID is a footnote. Never lead with it, and never paste the raw item line instead of a headline.
Action and triage briefs leave out the **Recommend** line unless you have a real recommendation.

For each question:
- `header`: ≤ 12 characters naming the topic, not the ID.
- For decisions and rulings, the recommended option comes first, its label ending in "(Recommended)".
  Each option's `description` is its one-line trade-off (cost · risk · reversibility); its `preview`
  holds the full option and its "After" line.
- **Decisions and rulings:** the researched options, plus **Not now** (leave it tagged) when there
  are fewer than 4.
- **Actions:** **Done** · **Not yet** · **Drop it**.
- **Triage:** **Keep** · **Promote to next** · **Park** · **Drop**.

An unclear free-text ("Other") answer gets one follow-up question. If it's still unclear, leave the
item tagged and add a note saying what was said.

## 5. Record each batch before asking the next

Write every answer from a batch to the docs before the next `AskUserQuestion` call, so stopping
early loses nothing.

| Answer | Record |
|---|---|
| A decision option | Add `  Ruling YYYY-MM-DD: <choice> — <why>` to the item (if that takes it past 5 lines, put the ruling in the linked spec's Rulings and link it). Remove `needs:`. Make it `now` if it blocks `now` work. |
| Your call | The same, with your choice, and "(owner delegated)" after the why. |
| A ruling option | Set the finding's Status to `open — ruling YYYY-MM-DD: <choice>`, or `wontfix: <why>`. |
| Done | Retire to `<docs>/history/punchlist-done.md` with `  — DONE YYYY-MM-DD (manual): <what was done>`. |
| Not yet | Leave it. If a reason was given, add `(YYYY-MM-DD: not yet — <reason>)`. |
| Drop it / Drop | Move to punchlist-done with `  — DROPPED YYYY-MM-DD: <why>`. |
| Keep | Add `(YYYY-MM-DD: triaged — keep, <why>)`. That resets its age. |
| Promote to next | Change its priority to `next`. |
| Park | Move to `<docs>/history/parked.md` with `  — PARKED YYYY-MM-DD: triaged (<why>)`. |
| Not now | Nothing. |

Moving an item means cutting the whole entry and pasting it under the heading with the same name as
its PUNCHLIST section in the target file (create the heading at the end if it's missing).

A ruling makes the item or finding itself workable; don't file a separate item to implement it.
Anything else an answer spawns (new follow-up work, a new question) becomes a new item from
`$PL next-id --bump`, tagged `from: <ID>`.

## 6. Wrap — also when the owner stops partway

- If an answer made an item `now`, add it to STATE's Next up in order.
- Run `$PL lint`. Fix every ERROR your edits caused; report any that were already there.
- Commit only `<docs>/` changes, as `docs(punchlist): interview — <n> resolved`.
- Report in ≤ 8 lines: what was resolved (by kind), what still waits (IDs), new items, and "<N> items
  are workable now". Suggest `/punchlist:autonomous` when N > 0.

## Common mistakes

| Mistake | Instead |
|---|---|
| Leading with "P-012: …" or pasting the item text | Lead with the plain-language headline; the ID is a footnote |
| Options without cost or reversibility | Every option says what it costs and how hard it is to undo |
| A decision or ruling with no recommendation | Always recommend one; the owner can overrule it |
| Asking before researching | Research every decision first, in parallel |
| One question per call when several are ready | Batch up to 4 |
| Recording everything at the end | Record each batch before asking the next |
| Tagging anything uncertain `needs: decision` | Apply the formats.md criteria; decide the rest and record a ruling |
