---
name: add
description: Use when the user wants to capture a bug, idea, follow-up, chore or manual task into the backlog/punchlist of a project that has a .punchlist.yml (e.g. "/punchlist:add export button 500s", "add that to the punchlist").
argument-hint: "<what to capture>"
---

# Capture a punchlist item

**Script:** `PL="${CLAUDE_PLUGIN_ROOT}/bin/punchlist"`. If that variable is empty, use
`<this skill's base directory>/../../bin/punchlist`. `<docs>` is `docs_dir` from `$PL config`.

1. Read `<docs>/PUNCHLIST.md` whole. **Check for duplicates.** If an existing item already covers the
   request, don't add a new one. Tell the user the existing ID, and extend its text if the new detail
   helps.
2. Classify:
   - **Section:** use the standard sections (formats.md: Bugs · Features · Improvements · Follow-ups
     from shipped work · Ops / manual), creating one if it doesn't exist yet. "Works but should work
     better" is Improvements; "works wrong" is Bugs.
   - **Priority:** `now` if it blocks current work or the user says it's urgent; `later` if it's
     nice-to-have or explicitly parked; otherwise `next`.
   - **`from:`:** set it if the request came out of a specific item, finding or feature.
3. `$PL next-id --bump` gives the ID and advances the counter.
4. Append the item at the end of its section. Write one line saying what and why, plus up to 3
   indented context lines (file paths, links). Keep it concrete enough for a cold session to act on:
   what is wrong or wanted, and where. If the premise doesn't hold yet (e.g. there's no UI to add a
   dialog to), say that instead of pretending. If an add is abandoned after `--bump`, the burned ID
   stays unused; never reuse it.
5. If it's `now` and belongs ahead of STATE's current "Next up" head, add it to "Next up". If only the
   owner can do it, add it to the "Waiting on" line.
6. `$PL lint`; fix any ERROR. If the working tree has no other changes, commit as
   `docs(punchlist): add P-### <short>` (for several items, `add P-###, P-### …`). Otherwise leave the
   edit uncommitted and say so, so it isn't tangled into someone's in-progress work.

Reply with one line: `P-### · <priority> · <section> — <text>`. If you judged it a duplicate, say
which ID it duplicates.

Several items at once: repeat steps 2–4 for each, then report them as a list.
