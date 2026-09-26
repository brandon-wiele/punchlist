# `/punchlist:interview` + `/punchlist:autonomous` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship two skills — `:interview` (clear items waiting on the owner, PM-style) and
`:autonomous` (serial subagent loop over `:next`) — on top of a `needs:` item marker and a
`punchlist queue` command.

**Architecture:** The `needs:` marker is a PUNCHLIST format change: parser, lint, formats.md,
templates and every skill that writes items change in one commit. `punchlist queue` becomes the
single pick order that `:next`, `:interview` and `:autonomous` all read. The two new skills are
Markdown procedures; `:autonomous` orchestrates background subagents strictly one at a time.

**Tech Stack:** Python ≥ 3.9 stdlib (`plugins/punchlist/lib/punchlist_core.py`, CLI
`plugins/punchlist/bin/punchlist`), `unittest`, Claude Code skills (`SKILL.md`), `just`.

**Spec:** `docs/specs/2026-09-25-interview-autonomous-design.md` — read it first; rulings R1–R10
there are binding.

## Global Constraints

- The script stays **stdlib-only, Python ≥ 3.9**, and never writes without an explicit flag. `queue` is read-only.
- **`reference/formats.md` is normative.** A format change updates, **in the same commit**:
  formats.md, the parser, its tests, and every skill and template that writes that format (repo rule 2).
- **Test first** for script changes (repo rule 4). Tests: `python3 -m unittest discover -s tests`;
  one class: `python3 -m unittest discover -s tests -k <ClassName>`.
- **`just check` before every commit.** Never push. Never change the plugin version except via `just release` (Task 8).
- Commit messages carry `(P-006)` and end with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Marker kinds: exactly `decision` and `action`. Findings keep `Status: needs-ruling: <question>`.
- Defaults: `budgets.triage_after_days: 30`; `stale_later_days` stays 60; `:autonomous` max units 10;
  an ID may be dispatched at most twice per run.
- `AskUserQuestion` limits: ≤ 4 questions per call, 2–4 options each, `header` ≤ 12 characters.
- An item is ≤ 5 lines in total.
- Match the surrounding style: explicit names, early returns, comments only at non-obvious decisions.

## File map

| File | Change | Task |
|---|---|---|
| `plugins/punchlist/lib/punchlist_core.py` | `_next_up_lines`, `_item_age_days` (T1); `needs` parsing, lint rules, `triage_after_days` (T2); `_item_text`, `_next_up_ids`, `queue()` (T3) | 1–3 |
| `plugins/punchlist/bin/punchlist` | `queue [--json]` subcommand | 3 |
| `tests/test_punchlist.py` | new test classes per task | 1–3 |
| `plugins/punchlist/reference/formats.md` | item age (T1); `needs:`, closing lines, config (T2); pick order (T3) | 1–3 |
| `plugins/punchlist/reference/templates/{STATE.md,punchlist.yml,claude-md-block.md}` | drop Waiting-on, add budget (T2); skills line (T4, T5) | 2, 4, 5 |
| `plugins/punchlist/skills/{add,next,handoff,review,setup}/SKILL.md` | write `needs:` (T2); `:next` pick via queue (T3); handoff report (T4) | 2–4 |
| `plugins/punchlist/skills/interview/SKILL.md` | new | 4 |
| `plugins/punchlist/skills/autonomous/SKILL.md` | new | 5 |
| `README.md`, `docs/design.md`, `CLAUDE.md` | tables and skills line | 1–5 |
| `docs/STATE.md`, `.punchlist.yml` | migrate off Waiting-on (T2); retire bookkeeping (T7) | 2, 7 |

---

### Task 1: Item age spans the whole item; share Next-up parsing

A triage "keep" note (a continuation line) must make a `later` item fresh again, so an item's age
becomes the newest change to *any* of its lines. Pure prep plus that one behavior change.

**Files:**
- Modify: `plugins/punchlist/lib/punchlist_core.py` (parsing section, git helpers, `lint`, `compact`)
- Modify: `plugins/punchlist/reference/formats.md` (PUNCHLIST item bullets)
- Modify: `docs/design.md` (script contract, lint bullet)
- Test: `tests/test_punchlist.py`

**Interfaces:**
- Produces: `_next_up_lines(state_text: str) -> list[tuple[int, str]]` — 0-based line number and text of
  each line in STATE's `## Next up` section, heading excluded; `[]` if no section.
- Produces: `_item_age_days(age_days: Callable, path: Path, item: dict) -> int` — min of
  `age_days(path, line)` over `range(item["start"], item["end"])`.

- [ ] **Step 1: Write the failing test** — add after `class CompactTest`:

```python
class ItemAgeTest(unittest.TestCase):
    def test_a_recent_note_on_a_later_item_keeps_it_from_going_stale(self):
        punchlist = PUNCHLIST.replace(
            "- **P-003** · later · Dark mode.\n",
            "- **P-003** · later · Dark mode.\n  (2026-09-20: triaged — keep, users asked)\n",
        )
        fixture = ProjectFixture(punchlist=punchlist, config="budgets:\n  stale_later_days: 30\n")
        try:
            item = next(i for i in core.parse_punchlist(punchlist)["items"] if i["id"] == "P-003")
            ages = lambda _path, line: 90 if line == item["start"] else 2
            changes = core.compact(fixture.root, age_days=ages, today="2026-09-23")
            self.assertNotIn(str(Path("docs/PUNCHLIST.md")), changes)
            found = core.lint(fixture.root, age_days=ages)
            self.assertFalse(any("stale" in message for _lv, _p, _l, message in found))
        finally:
            fixture.close()
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `python3 -m unittest discover -s tests -k ItemAgeTest`
Expected: FAIL — `'docs/PUNCHLIST.md' unexpectedly found` (compact parks P-003 on its first line's age).

- [ ] **Step 3: Implement**

In the parsing section, after `parse_done_ids`, add:

```python
def _next_up_lines(state_text: str) -> list:
    """(0-based line number, line) for each line of STATE's `## Next up` section, heading excluded."""
    lines = state_text.splitlines()
    heading = next((n for n, line in enumerate(lines) if line.startswith("## Next up")), None)
    if heading is None:
        return []
    end = next((n for n in range(heading + 1, len(lines)) if lines[n].startswith("## ")), len(lines))
    return [(number, lines[number]) for number in range(heading + 1, end)]
```

In the git helpers section, after `blame_age_days`, add:

```python
def _item_age_days(age_days: Callable, path: Path, item: dict) -> int:
    """Days since any line of the item last changed, so a fresh note or ruling makes the item fresh."""
    return min(age_days(path, line) for line in range(item["start"], item["end"]))
```

In `lint`, replace

```python
                age = age_days(punchlist, item["start"])
```

with

```python
                age = _item_age_days(age_days, punchlist, item)
```

and replace the Next-up block

```python
    if state.exists() and punchlist.exists():
        state_lines = state.read_text().splitlines()
        heading = next((n for n, line in enumerate(state_lines) if line.startswith("## Next up")), None)
        if heading is not None:
            end = next((n for n in range(heading + 1, len(state_lines)) if state_lines[n].startswith("## ")), len(state_lines))
            for number in range(heading + 1, end):
                line = state_lines[number]
                if line.startswith("**Waiting on"):
                    continue
                for match in ANY_ID_RE.finditer(line):
                    item_id = f"P-{match.group(1)}"
                    if item_id in done_ids and item_id not in open_ids:
                        add("ERROR", state, number + 1, f"Next up lists {item_id}, which is done — refresh Next up")
                    elif item_id not in open_ids:
                        add("WARN", state, number + 1, f"Next up lists {item_id}, which isn't an open PUNCHLIST item")
```

with

```python
    if state.exists() and punchlist.exists():
        for number, line in _next_up_lines(state.read_text()):
            if line.startswith("**Waiting on"):
                continue
            for match in ANY_ID_RE.finditer(line):
                item_id = f"P-{match.group(1)}"
                if item_id in done_ids and item_id not in open_ids:
                    add("ERROR", state, number + 1, f"Next up lists {item_id}, which is done — refresh Next up")
                elif item_id not in open_ids:
                    add("WARN", state, number + 1, f"Next up lists {item_id}, which isn't an open PUNCHLIST item")
```

In `compact`, replace

```python
        stale = [i for i in parsed["items"] if i["priority"] == "later" and age_days(punchlist, i["start"]) > config["budgets"]["stale_later_days"]]
```

with

```python
        stale = [i for i in parsed["items"] if i["priority"] == "later" and _item_age_days(age_days, punchlist, i) > config["budgets"]["stale_later_days"]]
```

and replace `days = age_days(punchlist, item["start"])` with `days = _item_age_days(age_days, punchlist, item)`.

- [ ] **Step 4: Docs** — in `plugins/punchlist/reference/formats.md`, after the bullet
  `- An item is ≤ 5 lines in total (\`lint\` warns above that). Link out instead of growing it.` add:

```
- An item's **age** is the time since *any* of its lines last changed (git blame). `later` items
  older than `stale_later_days` are stale.
```

  In `docs/design.md`, replace `` `later` items older than the stale threshold (WARN) `` with
  `` `later` items whose newest line is older than the stale threshold (WARN) ``.

- [ ] **Step 5: Run all tests — expect PASS**

Run: `python3 -m unittest discover -s tests`
Expected: all pass (the existing stale tests use a constant age, so they still hold).

- [ ] **Step 6: Commit**

```bash
just check
git add plugins/punchlist/lib/punchlist_core.py plugins/punchlist/reference/formats.md docs/design.md tests/test_punchlist.py
git commit -m "refactor(script): item age spans the whole item; share Next-up parsing (P-006)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: The `needs:` marker — one format-change commit

Parser, lint, config default, formats.md, templates, and every skill that writes items or the
Waiting-on line, plus migrating this repo off its Waiting-on line. **One commit** (rule 2).

**Files:**
- Modify: `plugins/punchlist/lib/punchlist_core.py` (constants, `DEFAULT_CONFIG`, `parse_punchlist`, `lint`)
- Modify: `plugins/punchlist/reference/formats.md`
- Modify: `plugins/punchlist/reference/templates/STATE.md`, `plugins/punchlist/reference/templates/punchlist.yml`
- Modify: `plugins/punchlist/skills/{add,next,handoff,review,setup}/SKILL.md`
- Modify: `docs/STATE.md`, `.punchlist.yml`, `docs/design.md`
- Test: `tests/test_punchlist.py`

**Interfaces:**
- Consumes: `_next_up_lines` (Task 1).
- Produces: every parsed item has `item["needs"]: list[str]` — the kinds in `` `needs: <kind>` `` tags
  anywhere in the item's span, in order (`[]` when untagged). `NEEDS_KINDS = ("decision", "action")`.
- Produces: `load_config(root)["budgets"]["triage_after_days"]` defaults to `30`.

- [ ] **Step 1: Write the failing tests** — add this fixture after `STATE_TMPL`:

```python
NEEDS_PUNCHLIST = textwrap.dedent(
    """\
    # PUNCHLIST

    - **ID** — `P-###`, never reused, never renumbered. Next free ID: **P-010**.

    ## Bugs

    - **P-001** · now · Login email never sends.

    ## Features

    - **P-002** · next · Export to CSV.
    - **P-005** · next · Pick the CSV delimiter for EU locales. `needs: decision`
    - **P-003** · later · Dark mode.

    ## Ops / manual

    - **P-006** · next · Rotate the SMTP credentials in production. `needs: action`
    """
)
```

In `YamlSubsetTest.test_config_defaults_fill_missing_keys`, add after the `push` assertion:

```python
            self.assertEqual(config["budgets"]["triage_after_days"], 30)
```

In `ParsingTest`, add:

```python
    def test_needs_marker_is_parsed_from_anywhere_in_the_item(self):
        text = NEEDS_PUNCHLIST.replace("Export to CSV.\n", "Export to CSV.\n  Blocked on the format question. `needs: decision`\n")
        items = {item["id"]: item for item in core.parse_punchlist(text)["items"]}
        self.assertEqual(items["P-001"]["needs"], [])
        self.assertEqual(items["P-002"]["needs"], ["decision"])  # marker on a continuation line
        self.assertEqual(items["P-005"]["needs"], ["decision"])
        self.assertEqual(items["P-006"]["needs"], ["action"])

    def test_manual_and_dropped_lines_count_as_closed(self):
        done = DONE + (
            "- **P-007** · later · Publish to the marketplace.\n  — DONE 2026-09-25 (manual): listed.\n"
            "- **P-008** · later · Old idea.\n  — DROPPED 2026-09-25: superseded by P-002.\n"
        )
        self.assertEqual(core.parse_done_ids(done), {"P-004", "P-007", "P-008"})
```

Add a class after `LintConsistencyTest`:

```python
class NeedsLintTest(unittest.TestCase):
    def lint_messages(self, fixture):
        return [(level, m) for level, _p, _l, m in core.lint(fixture.root, age_days=lambda *_: 0)]

    def test_valid_markers_are_clean(self):
        fixture = ProjectFixture(punchlist=NEEDS_PUNCHLIST)
        try:
            self.assertEqual([m for _level, m in self.lint_messages(fixture) if "needs" in m], [])
        finally:
            fixture.close()

    def test_unknown_kind_and_two_markers_are_errors(self):
        punchlist = NEEDS_PUNCHLIST.replace("`needs: action`", "`needs: approval`").replace(
            "Export to CSV.", "Export to CSV. `needs: decision` `needs: action`"
        )
        fixture = ProjectFixture(punchlist=punchlist)
        try:
            errors = [m for level, m in self.lint_messages(fixture) if level == "ERROR"]
            self.assertTrue(any("P-006" in m and "approval" in m for m in errors))
            self.assertTrue(any("P-002" in m and "2 `needs:` markers" in m for m in errors))
        finally:
            fixture.close()

    def test_legacy_waiting_on_line_and_next_up_naming_a_needs_item_warn(self):
        fixture = ProjectFixture(punchlist=NEEDS_PUNCHLIST)
        try:
            state = fixture.root / "docs" / "STATE.md"
            state.write_text(state.read_text().replace("1. P-001", "1. P-001\n2. P-005\n\n**Waiting on maintainer:** P-006"))
            warnings = [m for level, m in self.lint_messages(fixture) if level == "WARN"]
            self.assertTrue(any("Waiting on" in m for m in warnings))
            self.assertTrue(any("P-005" in m and "needs" in m for m in warnings))
            self.assertFalse(any("Next up lists P-006" in m for m in warnings))  # the legacy line isn't read as Next up
        finally:
            fixture.close()
```

- [ ] **Step 2: Run them — expect FAIL**

Run: `python3 -m unittest discover -s tests -k Needs -k Parsing -k YamlSubset`
Expected: FAIL — `KeyError: 'triage_after_days'`, `KeyError: 'needs'`, and the lint assertions.
(`test_manual_and_dropped_lines_count_as_closed` already passes: it pins behavior formats.md now relies on.)

- [ ] **Step 3: Implement the script**

Add under `SEVERITIES`:

```python
NEEDS_KINDS = ("decision", "action")
```

Add under `ANY_ID_RE`:

```python
NEEDS_RE = re.compile(r"`needs: ([^`]*)`")
```

In `DEFAULT_CONFIG["budgets"]`, after `"stale_later_days": 60,` add:

```python
        "triage_after_days": 30,
```

In `parse_punchlist`, replace the span-trimming loop

```python
    # An item's span ends at its last non-blank line.
    for item in items:
        while item["end"] > item["start"] + 1 and not lines[item["end"] - 1].strip():
            item["end"] -= 1
```

with

```python
    # An item's span ends at its last non-blank line.
    for item in items:
        while item["end"] > item["start"] + 1 and not lines[item["end"] - 1].strip():
            item["end"] -= 1
        item["needs"] = [kind.strip() for kind in NEEDS_RE.findall("".join(lines[item["start"] : item["end"]]))]
```

In `lint`, inside `for item in parsed["items"]:`, directly after `open_ids[item["id"]] = item`, add:

```python
            for kind in item["needs"]:
                if kind not in NEEDS_KINDS:
                    add("ERROR", punchlist, item["start"] + 1, f"{item['id']}: unknown `needs:` kind '{kind}' — use one of {', '.join(NEEDS_KINDS)}")
            if len(item["needs"]) > 1:
                add("ERROR", punchlist, item["start"] + 1, f"{item['id']} has {len(item['needs'])} `needs:` markers — keep one")
```

Replace the Next-up block from Task 1 with:

```python
    if state.exists() and punchlist.exists():
        state_text = state.read_text()
        for number, line in enumerate(state_text.splitlines()):
            if line.startswith("**Waiting on"):
                add("WARN", state, number + 1, "legacy 'Waiting on' line — tag those items `needs: decision|action` in PUNCHLIST and delete the line")
        for number, line in _next_up_lines(state_text):
            if line.startswith("**Waiting on"):
                continue
            for match in ANY_ID_RE.finditer(line):
                item_id = f"P-{match.group(1)}"
                if item_id in done_ids and item_id not in open_ids:
                    add("ERROR", state, number + 1, f"Next up lists {item_id}, which is done — refresh Next up")
                elif item_id not in open_ids:
                    add("WARN", state, number + 1, f"Next up lists {item_id}, which isn't an open PUNCHLIST item")
                elif open_ids[item_id]["needs"]:
                    add("WARN", state, number + 1, f"Next up lists {item_id}, which needs the owner (`needs: {open_ids[item_id]['needs'][0]}`) — sessions will skip it")
```

- [ ] **Step 4: Run all tests — expect PASS**

Run: `python3 -m unittest discover -s tests`
Expected: all pass.

- [ ] **Step 5: formats.md**

Replace

```
items. Follow it with `**Waiting on <owner>:** P-…` for items only the owner can do. `lint` errors if
Next up names a done item.
```

with

```
items. Items waiting on the owner aren't listed here: their `needs:` marker in PUNCHLIST is the only
record. `lint` errors if Next up names a done item, and warns if it names a `needs:` item or if STATE
still has a `**Waiting on …:**` line (the older format).
```

After the umbrella bullet (`- An **umbrella** item points at … retires only when its last row closes.`) add:

```

### `needs:` — items waiting on the owner

- `` `needs: decision` `` — the owner must answer a question, which the item text states plainly.
  Tag it **only** when at least one holds: a product/UX fork the spec and code don't settle; a choice
  that is expensive to reverse (data model, public format, published interface); a change to a
  contract documented in CLAUDE.md; spending money or touching external accounts; anything externally
  visible (publishing, messaging people). Otherwise the session decides, records a ruling and keeps
  going.
- `` `needs: action` `` — only the owner can do it: credentials, publishing, account setup, live or
  manual checks against production or hardware.
- At most one marker per item, anywhere in it; `lint` errors on two, or on any other kind. The marker
  is the only record that an item waits on the owner. Code-review findings use
  `Status: needs-ruling:` instead.
- A ruling recorded on an item is a continuation line `  Ruling YYYY-MM-DD: <answer> — <why>`. If that
  would take the item past 5 lines, put the ruling in the linked spec's Rulings and link it.
- A triaged-and-kept `later` item gets `(YYYY-MM-DD: triaged — keep, <why>)`, which resets its age.
```

After `The SHA is the commit that did the work.` add:

```

Two other closing lines go in the same place:
- `  — DONE YYYY-MM-DD (manual): …` when the owner did the work and no commit did.
- `  — DROPPED YYYY-MM-DD: <why>` when it won't be done. The ID stays retired.
```

Replace

```
Same as done, but the suffix line is `  — PARKED YYYY-MM-DD: stale (no change in N days)`. To revive an item,
move it back to PUNCHLIST with its original ID.
```

with

```
Same as done, but the suffix line is `  — PARKED YYYY-MM-DD: stale (no change in N days)`, or
`  — PARKED YYYY-MM-DD: triaged (<why>)` when the owner parked it. To revive an item, move it back to
PUNCHLIST with its original ID.
```

After `  The first two are open; the last three are closed.` add:

```
  An owner's answer to a `needs-ruling:` question makes it `open — ruling YYYY-MM-DD: <answer>` or
  `wontfix: <why>`.
```

In the `.punchlist.yml` block, replace `owner: the maintainer  # who "Waiting on" means` with
`owner: the maintainer  # who needs: items wait on`, and after `  stale_later_days: 60` add
`  triage_after_days: 30   # untagged later items older than this are due for triage`.

- [ ] **Step 6: Templates and this repo**

- `plugins/punchlist/reference/templates/STATE.md`: delete the line `**Waiting on {{owner}}:** {{waiting}}`
  and the blank line before it.
- `plugins/punchlist/reference/templates/punchlist.yml`: `owner: {{owner}}       # who needs: items wait on`;
  after `  stale_later_days: 60` add `  triage_after_days: 30`.
- `docs/STATE.md`: delete `**Waiting on maintainer:** nothing.` and the blank line before it.
- `.punchlist.yml`: `owner: maintainer      # who needs: items wait on`.
- `docs/design.md`, script-contract lint bullet: replace
  `a snapshot claiming \`clean\` while *code* is uncommitted (WARN).` with
  `a snapshot claiming \`clean\` while *code* is uncommitted (WARN); an unknown or doubled \`needs:\` marker; Next up naming a \`needs:\` item (WARN); a leftover \`Waiting on\` line (WARN).`

- [ ] **Step 7: Skills that write items**

`plugins/punchlist/skills/add/SKILL.md` — replace

```
5. If it's `now` and belongs ahead of STATE's current "Next up" head, add it to "Next up". If only the
   owner can do it, add it to the "Waiting on" line.
```

with

```
5. If only the owner can move it, tag it `needs: decision` or `needs: action` (formats.md § `needs:`
   has the criteria) and keep it out of Next up. Otherwise, if it's `now` and belongs ahead of STATE's
   current "Next up" head, add it to "Next up".
```

`plugins/punchlist/skills/next/SKILL.md` — replace the rows

```
| Argument given | That item or finding. If only the owner can do it, say so and stop. |
```
```
| Only the owner can do it (a decision, ops, credentials, a live/manual check, a ruling) | **Skip it**, name it in the report, move on |
| A finding is `needs-ruling:`, or the fix would change a documented contract in CLAUDE.md | Skip it; put the question in the report |
```

with

```
| Argument given | That item or finding. If it carries `needs:`, or only the owner can do it, say so and stop. |
```
```
| Only the owner can do it (formats.md § `needs:` criteria) | **Skip it**: tag it `needs: decision` or `needs: action`, stating the question or task plainly in the item; name it in the report; move on |
| A choice comes up that doesn't meet those criteria | Decide it, record `Ruling YYYY-MM-DD: …` on the item (or in the spec's Rulings), keep going |
| A finding is `needs-ruling:`, or the fix would change a documented contract in CLAUDE.md | Skip it; set its Status to `needs-ruling: <question>` if it isn't already; put the question in the report |
```

and replace

```
- **Anything discovered, deferred, or needing the owner:** create a new item with
  `$PL next-id --bump`, put it in the right section, and tag it `from: <this ID>`.
```

with

```
- **Anything discovered, deferred, or needing the owner:** create a new item with
  `$PL next-id --bump`, put it in the right section, and tag it `from: <this ID>`, plus
  `needs: <kind>` if only the owner can move it.
```

and replace `4. **Needs you:** skipped owner items, open rulings, and new P-items filed.` with
`4. **Needs you:** items tagged \`needs:\` or \`needs-ruling:\` this unit, and new P-items filed.`

`plugins/punchlist/skills/handoff/SKILL.md` — replace

```
1. **Deferred, discovered or half-done → P-items.** Get each new ID from `$PL next-id --bump`. Tag it
   `from:`. Half-done work gets a progress note on its existing item.
```

with

```
1. **Deferred, discovered or half-done → P-items.** Get each new ID from `$PL next-id --bump`. Tag it
   `from:`, and `needs: decision|action` if only the owner can move it (formats.md criteria).
   Half-done work gets a progress note on its existing item.
```

and replace `naming items by ID. Update the "Waiting on" line. Roll` with
`naming items by ID; items tagged \`needs:\` stay out of it. Roll`.

`plugins/punchlist/skills/review/SKILL.md` — replace

```
- Put the umbrella at the top of STATE "Next up" unless something is blocking. Add owner rulings to
  the "Waiting on" line.
```

with

```
- Put the umbrella at the top of STATE "Next up" unless something is blocking. Findings that need an
  owner ruling carry `Status: needs-ruling: <question>`; that status is the record, so don't list
  them in STATE.
```

`plugins/punchlist/skills/setup/SKILL.md` §6 — after `- Create any standard file that's missing.` add:

```
- **Legacy `**Waiting on …:**` line in STATE** (the format before `needs:`): tag each item it names
  `needs: decision` or `needs: action` in PUNCHLIST, by what the item asks of the owner, then delete
  the line. `lint` warns until it's gone.
```

- [ ] **Step 8: Verify and commit (one commit)**

```bash
grep -rnI "Waiting on" plugins README.md docs/design.md docs/STATE.md | grep -v "formats.md\|setup/SKILL.md\|punchlist_core.py\|design.md"
```

Expected: no output. The excluded files mention the line only to describe the legacy format.

```bash
just check
plugins/punchlist/bin/punchlist lint
git add -A plugins tests docs/STATE.md docs/design.md .punchlist.yml
git commit -m "feat(format): needs: marker replaces the Waiting-on line (P-006)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `lint: 0 error(s), 0 warning(s)`.

---

### Task 3: `punchlist queue` — the one pick order

**Files:**
- Modify: `plugins/punchlist/lib/punchlist_core.py` (new `# --- queue ---` section after `next_id`)
- Modify: `plugins/punchlist/bin/punchlist` (docstring, subparser, `_print_queue`, dispatch)
- Modify: `plugins/punchlist/reference/formats.md`, `plugins/punchlist/skills/next/SKILL.md`
- Modify: `README.md`, `docs/design.md`
- Test: `tests/test_punchlist.py`

**Interfaces:**
- Consumes: `item["needs"]`, `NEEDS_KINDS`, `budgets.triage_after_days` (Task 2); `_next_up_lines`, `_item_age_days` (Task 1).
- Produces: `queue(root: Path, age_days: Callable | None = None) -> dict` with keys
  `workable`, `needs`, `triage`, each a list of entries:
  - workable: `{"id", "priority", "section", "text"}`
  - needs (items): the same plus `"kind"` (`decision` | `action`)
  - needs (findings): `{"id", "kind": "ruling", "priority": None, "section": None, "text": <title>, "question", "file"}`
  - triage: the workable shape plus `"age_days"`
- CLI: `punchlist queue [--json]`.

- [ ] **Step 1: Write the failing tests** — add `import json` to the test imports, then after `NeedsLintTest`:

```python
class QueueTest(unittest.TestCase):
    def test_workable_order_follows_next_up_then_now_then_next(self):
        punchlist = NEEDS_PUNCHLIST + "- **P-007** · now · Page the on-call when exports fail.\n"
        fixture = ProjectFixture(punchlist=punchlist)
        try:
            state = fixture.root / "docs" / "STATE.md"
            state.write_text(state.read_text().replace("1. P-001", "1. P-002"))
            result = core.queue(fixture.root, age_days=lambda *_: 0)
            self.assertEqual([entry["id"] for entry in result["workable"]], ["P-002", "P-001", "P-007"])
            self.assertEqual(result["workable"][0], {"id": "P-002", "priority": "next", "section": "Features", "text": "Export to CSV."})
        finally:
            fixture.close()

    def test_needs_lists_marked_items_and_findings_awaiting_a_ruling(self):
        findings = FINDINGS.replace("- **Status:** open\n", "- **Status:** needs-ruling: retry or fail fast?\n", 1)
        fixture = ProjectFixture(punchlist=NEEDS_PUNCHLIST, findings=findings)
        try:
            by_id = {entry["id"]: entry for entry in core.queue(fixture.root, age_days=lambda *_: 0)["needs"]}
            self.assertEqual(sorted(by_id), ["API-001", "P-005", "P-006"])
            self.assertEqual(by_id["P-005"]["kind"], "decision")
            self.assertEqual(by_id["P-005"]["text"], "Pick the CSV delimiter for EU locales. `needs: decision`")
            self.assertEqual(by_id["P-006"]["kind"], "action")
            self.assertEqual(
                by_id["API-001"],
                {"id": "API-001", "kind": "ruling", "priority": None, "section": None, "text": "Cancel never propagates",
                 "question": "retry or fail fast?", "file": str(Path("docs/code-review/01-api.md"))},
            )
        finally:
            fixture.close()

    def test_triage_lists_untagged_later_items_older_than_the_budget(self):
        punchlist = NEEDS_PUNCHLIST + "- **P-008** · later · Decide whether to keep the beta flag. `needs: decision`\n"
        fixture = ProjectFixture(punchlist=punchlist, config="budgets:\n  triage_after_days: 30\n")
        try:
            self.assertEqual(core.queue(fixture.root, age_days=lambda *_: 10)["triage"], [])
            old = core.queue(fixture.root, age_days=lambda *_: 45)
            self.assertEqual([(entry["id"], entry["age_days"]) for entry in old["triage"]], [("P-003", 45)])  # P-008 is tagged: it's in needs
            self.assertNotIn("P-003", [entry["id"] for entry in old["workable"]])  # later items are never workable
        finally:
            fixture.close()

    def test_cli_queue_json_and_plain(self):
        fixture = ProjectFixture(punchlist=NEEDS_PUNCHLIST)
        try:
            as_json = subprocess.run([sys.executable, str(BIN), "queue", "--json"], cwd=fixture.root, capture_output=True, text=True)
            self.assertEqual(as_json.returncode, 0, as_json.stderr)
            self.assertEqual(sorted(json.loads(as_json.stdout)), ["needs", "triage", "workable"])
            plain = subprocess.run([sys.executable, str(BIN), "queue"], cwd=fixture.root, capture_output=True, text=True)
            self.assertIn("P-005 · decision · Pick the CSV delimiter", plain.stdout)
            self.assertIn("Workable (2):", plain.stdout)
        finally:
            fixture.close()
```

- [ ] **Step 2: Run them — expect FAIL**

Run: `python3 -m unittest discover -s tests -k QueueTest`
Expected: FAIL — `AttributeError: module 'punchlist_core' has no attribute 'queue'`.

- [ ] **Step 3: Implement the core**

After `_next_up_lines` in the parsing section, add:

```python
def _item_text(lines: list, item: dict) -> str:
    """The item's words without the ID/priority prefix, continuation lines joined by spaces."""
    first = ITEM_RE.sub("", lines[item["start"]], count=1).strip()
    rest = [line.strip() for line in lines[item["start"] + 1 : item["end"]]]
    return " ".join(part for part in [first, *rest] if part)


def _next_up_ids(state_path: Path) -> list:
    """The leading P-ID of each Next up entry, in listed order."""
    if not state_path.exists():
        return []
    ids = []
    for _number, line in _next_up_lines(state_path.read_text()):
        if line.startswith("**Waiting on"):
            continue
        match = ANY_ID_RE.search(line)
        if match:
            ids.append(f"P-{match.group(1)}")
    return ids
```

After the `next_id` function, add:

```python
# --- queue --------------------------------------------------------------------------------------


def queue(root: Path, age_days: Callable | None = None) -> dict:
    """What to work next, what waits on the owner, and what's due for triage. Writes nothing."""
    root = Path(root)
    config = load_config(root)
    docs = _docs(root, config)
    age_days = age_days or (lambda path, line: blame_age_days(root, path, line))
    punchlist = docs / "PUNCHLIST.md"
    if not punchlist.exists():
        raise PunchlistError(f"{punchlist}: missing (run /punchlist:setup)")
    parsed = parse_punchlist(punchlist.read_text())
    items_by_id = {item["id"]: item for item in parsed["items"]}

    def entry(item: dict) -> dict:
        return {"id": item["id"], "priority": item["priority"], "section": item["section"], "text": _item_text(parsed["lines"], item)}

    # The same order /punchlist:next has always used: Next up as listed, then `now`, then `next`.
    candidates = [items_by_id[item_id] for item_id in _next_up_ids(docs / "STATE.md") if item_id in items_by_id]
    candidates += [item for item in parsed["items"] if item["priority"] == "now"]
    candidates += [item for item in parsed["items"] if item["priority"] == "next"]
    workable = []
    seen = set()
    for item in candidates:
        if item["id"] in seen or item["needs"] or item["priority"] == "later":
            continue
        seen.add(item["id"])
        workable.append(entry(item))

    needs = [dict(entry(item), kind=item["needs"][0]) for item in parsed["items"] if item["needs"]]
    for path in _finding_files(root, config):
        for finding in parse_findings(path.read_text()):
            status = finding["status"] or ""
            if not status.startswith("needs-ruling:"):
                continue
            needs.append({
                "id": finding["id"],
                "kind": "ruling",
                "priority": None,
                "section": None,
                "text": finding["title"],
                "question": status[len("needs-ruling:"):].strip(),
                "file": str(path.relative_to(root)),
            })

    triage = []
    for item in parsed["items"]:
        if item["priority"] != "later" or item["needs"]:
            continue
        age = _item_age_days(age_days, punchlist, item)
        if age > config["budgets"]["triage_after_days"]:
            triage.append(dict(entry(item), age_days=age))

    return {"workable": workable, "needs": needs, "triage": triage}
```

- [ ] **Step 4: Implement the CLI** — in `plugins/punchlist/bin/punchlist`:

In the docstring, after the `next-id` line add:

```
  queue [--json]      what's workable (in pick order), what needs the owner, what's due for triage
```

Above `def main`, add:

```python
def _print_queue(result: dict) -> None:
    groups = (("Workable", "workable", "priority"), ("Needs you", "needs", "kind"), ("Triage", "triage", "age_days"))
    for title, key, label_field in groups:
        entries = result[key]
        print(f"{title} ({len(entries)}):")
        for entry in entries:
            label = f"{entry[label_field]} days" if label_field == "age_days" else entry[label_field]
            print(f"  {entry['id']} · {label} · {entry['text'][:100]}")
```

After the `next_parser` lines, add:

```python
    queue_parser = commands.add_parser("queue")
    queue_parser.add_argument("--json", action="store_true")
```

After the `next-id` branch of the dispatch, add:

```python
        elif args.command == "queue":
            result = core.queue(root)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                _print_queue(result)
```

- [ ] **Step 5: Run all tests — expect PASS**

Run: `python3 -m unittest discover -s tests`
Expected: all pass.

- [ ] **Step 6: Docs and `:next`**

formats.md — in the Next-up paragraph, replace `record. \`lint\` errors if Next up names a done item,`
with `record, and \`punchlist queue\` lists them. \`lint\` errors if Next up names a done item,`. Then
insert before `## history/punchlist-done.md`:

```
## Pick order — `punchlist queue`

`punchlist queue [--json]` is the one definition of what to work next. Skills read it; they don't
re-derive it. Three groups:
- **workable** — open items with no `needs:` marker, in order: STATE Next up entries as listed, then
  `now` items, then `next` items (both in PUNCHLIST order), each once. `later` items are never
  workable; promote them first.
- **needs** — items with a `needs:` marker (`kind` decision | action), then findings whose Status is
  `needs-ruling:` (`kind` ruling, plus `question` and `file`).
- **triage** — untagged `later` items older than `budgets.triage_after_days`, with `age_days`.

Every entry has `id`, `priority`, `section` and `text`. For findings, `priority` and `section` are
null and `text` is the title.
```

`plugins/punchlist/skills/next/SKILL.md` — replace the row

```
| No argument | The first actionable entry in STATE "Next up"; else the first `now` item in PUNCHLIST order; else the first `next` item |
```

with

```
| No argument | The first `workable` entry of `$PL queue --json` (Next up, then `now`, then `next`; items tagged `needs:` and `later` items are excluded) |
```

`README.md` — in the script block, after the `next-id` line add
`  queue [--json]      workable / needs-you / triage lists — the pick order the skills use`.

`docs/design.md` — in the Components table, change `` `status`, `lint`, `next-id`, `compact`, `config`, `docs` ``
to `` `status`, `lint`, `next-id`, `queue`, `compact`, `config`, `docs` ``; in the script contract, after
the `next-id` bullet add:

```
- `punchlist queue [--json]` — the pick order: `workable` (Next up → `now` → `next`, no `needs:`, no
  `later`), `needs` (tagged items and `needs-ruling:` findings) and `triage` (untagged `later` items
  older than `triage_after_days`). Read-only.
```

- [ ] **Step 7: Commit**

```bash
just check
plugins/punchlist/bin/punchlist lint
plugins/punchlist/bin/punchlist queue
git add plugins tests README.md docs/design.md
git commit -m "feat(script): punchlist queue — one pick order for every skill (P-006)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected from `queue` on this repo: `Workable (2):` P-001 (listed in Next up), then P-006 (`now`);
`Needs you (0)`; `Triage (0)` (the `later` items are only days old).

---

### Task 4: `/punchlist:interview`

**Files:**
- Create: `plugins/punchlist/skills/interview/SKILL.md`
- Modify: `plugins/punchlist/skills/handoff/SKILL.md` (report item 5)
- Modify: `plugins/punchlist/reference/templates/claude-md-block.md`, `CLAUDE.md`, `README.md`, `docs/design.md`

**Interfaces:**
- Consumes: `punchlist queue --json` (Task 3); formats from Task 2 (Ruling line, `(manual)`, `DROPPED`, triaged PARKED, triage keep note, finding `open — ruling …`).

- [ ] **Step 1: Create `plugins/punchlist/skills/interview/SKILL.md`** with exactly:

````markdown
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

Run `git status`. If tracked files outside `<docs>/` are modified, stop and say so: this skill
commits bookkeeping on the current branch and must not tangle it with other work.

## 2. Build the queue

- Run `$PL queue --json`. Take `needs` (kinds `decision`, `action`, `ruling`) and `triage`. An
  argument narrows it: specific IDs, or one group (`decisions` = decision + ruling, `actions`,
  `triage`).
- Read `<docs>/PUNCHLIST.md` whole and look for **untagged** items only the owner can move: the
  Ops / manual section, or wording like decide, choose, confirm, approve, sign off, credentials,
  publish. If there are any, ask once, as a multi-select `AskUserQuestion`, which really need the
  owner. Tag those `needs: decision` or `needs: action` and add them to the queue.
- A tagged `decision` that fails the formats.md criteria for `needs: decision` stays in the queue, but
  its recommended option is **"Your call"**: you decide, record the ruling, and remove the tag.
- **Empty queue:** report "Nothing needs you — <N> items are workable." and suggest
  `/punchlist:autonomous` if N > 0. Stop.

## 3. Research before asking

For each `decision` and `ruling` entry, dispatch a **read-only** subagent (Explore, if available).
Send them all in one message so they run in parallel. Give each the entry's JSON, the project root
and this brief:

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

For each question:
- `header`: ≤ 12 characters naming the topic, not the ID.
- The recommended option comes first, its label ending in "(Recommended)". Each option's
  `description` is its one-line trade-off (cost · risk · reversibility); its `preview` holds the full
  option and its "After" line.
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

Anything an answer spawns (follow-up work, a new question) becomes a new item from
`$PL next-id --bump`, tagged `from: <ID>`.

## 6. Wrap — also when the owner stops partway

- If an answer made an item `now`, add it to STATE's Next up in order.
- Run `$PL lint` and fix every ERROR.
- Commit only `<docs>/` changes, as `docs(punchlist): interview — <n> resolved`.
- Report in ≤ 8 lines: what was resolved (by kind), what still waits (IDs), new items, and "<N> items
  are workable now". Suggest `/punchlist:autonomous` when N > 0.

## Common mistakes

| Mistake | Instead |
|---|---|
| Leading with "P-012: …" or pasting the item text | Lead with the plain-language headline; the ID is a footnote |
| Options without cost or reversibility | Every option says what it costs and how hard it is to undo |
| No recommendation | Always recommend one; the owner can overrule it |
| Asking before researching | Research every decision first, in parallel |
| One question per call when several are ready | Batch up to 4 |
| Recording everything at the end | Record each batch before asking the next |
| Tagging anything uncertain `needs: decision` | Apply the formats.md criteria; decide the rest and record a ruling |
````

- [ ] **Step 2: Wire it in**

`plugins/punchlist/skills/handoff/SKILL.md` — replace `5. Anything waiting on the owner.` with
`5. What waits on the owner: the \`needs\` group of \`$PL queue\` (count and IDs). Suggest \`/punchlist:interview\` if it isn't empty.`

`plugins/punchlist/reference/templates/claude-md-block.md` **and** the same lines in `CLAUDE.md` — replace

```
Workflow skills: `/punchlist:next [P-###|finding-ID]` works one backlog unit end to end ·
`/punchlist:add` captures an item · `/punchlist:handoff` closes a session · `/punchlist:review`
audits the codebase · `/punchlist:tidy` triages stale docs (archive, index, rewrite P-items).
```

with

```
Workflow skills: `/punchlist:next [P-###|finding-ID]` works one backlog unit end to end ·
`/punchlist:interview` clears items waiting on the owner · `/punchlist:add` captures an item ·
`/punchlist:handoff` closes a session · `/punchlist:review` audits the codebase · `/punchlist:tidy`
triages stale docs (archive, index, rewrite P-items).
```

`README.md` skills table, after the `/punchlist:next` row:

```
| `/punchlist:interview [IDs\|group]` | Clear what waits on you: researched, PM-style briefs for decisions, rulings, manual tasks and stale items, asked in batches and recorded |
```

`docs/design.md` Components table, after the `skills/next` row:

```
| `skills/interview` | Collect items tagged `needs:`, `needs-ruling:` findings and stale `later` items; research decisions in parallel; ask the owner in batches with a recommendation; record rulings, retirements and triage |
```

- [ ] **Step 3: Validate and commit**

```bash
just check
git add plugins/punchlist/skills/interview plugins/punchlist/skills/handoff/SKILL.md plugins/punchlist/reference/templates/claude-md-block.md CLAUDE.md README.md docs/design.md
git commit -m "feat(skills): /punchlist:interview — clear items waiting on the owner (P-006)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `claude plugin validate` accepts the new skill's frontmatter.

---

### Task 5: `/punchlist:autonomous`

**Files:**
- Create: `plugins/punchlist/skills/autonomous/SKILL.md`
- Modify: `plugins/punchlist/reference/templates/claude-md-block.md`, `CLAUDE.md`, `README.md`, `docs/design.md`

**Interfaces:**
- Consumes: `punchlist queue --json` (Task 3); the `punchlist:next` skill (with Task 2's `needs:` tagging); `/punchlist:interview` (Task 4) as the hand-over.

- [ ] **Step 1: Create `plugins/punchlist/skills/autonomous/SKILL.md`** with exactly:

````markdown
---
name: autonomous
description: Use when asked to work through the punchlist / backlog unattended — "run autonomously", "grind the backlog", "keep doing /punchlist:next until done" — in a project that has a .punchlist.yml. Works units one at a time through subagents until nothing workable is left, a unit fails, or only items that need the owner remain.
argument-hint: "[max-units]"
---

# Work the backlog unattended

You are the orchestrator. Subagents do the work, one `/punchlist:next` unit each, **strictly one at a
time**: every unit merges to the base branch and rewrites PUNCHLIST, STATE and the ID counter, so two
at once would collide. You never read or write code. Your context holds queue JSON, unit reports and
one review. Formats: `../../reference/formats.md` (relative to this skill's base directory).

**Script:** `PL="${CLAUDE_PLUGIN_ROOT}/bin/punchlist"`. If that variable is empty, use
`<this skill's base directory>/../../bin/punchlist`. `<docs>` and `base_branch` come from
`$PL config`. The argument is the maximum number of units; the default is 10.

If there's no `.punchlist.yml`, stop and suggest `/punchlist:setup`.

## 1. Preflight — stop on any failure and say which

- `git status`: you're on `base_branch` and no tracked files are modified.
- `$PL lint` has no ERROR. Every unit's retire runs lint, so an existing error would fail them all.
- `$PL queue --json` has at least one `workable` entry. If not, report the `needs` and `triage`
  counts, suggest `/punchlist:interview` if either is non-zero, and stop.
- Record `START=$(git rev-parse --short HEAD)`.
- Print one line: `Autonomous run: up to <max> units, starting with <ID> — <text>.` Add: "Units run
  gates and git commands; if this session asks before running commands, the run waits for you." Then
  proceed. Don't ask for confirmation.

## 2. The loop — one unit at a time

1. Run `$PL queue --json` and take the first `workable` entry. If that ID has already been dispatched
   twice this run, stop: it isn't converging.
2. Dispatch **one** general-purpose subagent **in the background** with the prompt below, then wait
   for its completion notification. Dispatch nothing else in the meantime.

   > Work one punchlist unit in `<project root>`: invoke the `punchlist:next` skill with argument
   > `<ID>` and follow it exactly, through merge and bookkeeping. Rules for this run: never ask the
   > user anything — if the unit needs the owner, tag it `needs:` as the skill says, commit the
   > bookkeeping and stop; never push, whatever `push:` says. Reply with only these lines:
   > outcome: done | partial | split | skipped | failed
   > id: <ID>
   > code_sha: <sha or ->
   > bookkeeping_sha: <sha or ->
   > gates: pass | fail — <which and why>
   > new_items: <P-IDs or ->
   > needs_you: <IDs with one line each, or ->
   > notes: <≤ 3 lines>

3. Run the checks in §3, then go back to step 1.

While a unit runs, the owner may message you. If they say to stop, let the unit finish, run the
checks, and stop with the reason "stopped by owner". Answer anything else from what you already know;
don't dispatch anything new.

## 3. Check after every unit — any failure stops the run

- `git branch --show-current` prints `base_branch`.
- `git status --porcelain --untracked-files=no` prints nothing.
- `$PL lint` has no ERROR.
- `outcome` isn't `failed`, and `gates` doesn't start with `fail`.

On a failure, stop. Don't clean up, stash, switch branches or retry: the owner decides. Skip §5 step 1
and go to the review and report.

## 4. Stop conditions

- No `workable` entries are left.
- `max-units` units have run.
- A check in §3 failed.
- The next ID would be dispatched a third time.
- The owner asked to stop.

## 5. Wrap

1. **Only if the last checks passed:** run `$PL compact`. Apply it with `$PL compact --apply` unless
   it parks an item this run touched. Run `$PL lint`. If anything changed, commit it as
   `docs(punchlist): autonomous run — <n> units`.
2. **Review the run.** If `git log --oneline START..HEAD -- . ':(exclude)<docs>'` lists any commit,
   dispatch one read-only reviewer subagent (use `superpowers:requesting-code-review` if it's
   available) with:
   > Review `git diff <START>..HEAD` in `<project root>`, unit by unit. Units: <one line each: ID —
   > item text — code_sha>. For each unit, reply `<ID>: fine` or `<ID>: look at this — <why>
   > (<file:line>)`. Look for correctness bugs, changes outside the item's scope, and tests that don't
   > exercise the change. Don't edit anything.

   The review is advisory. It never fixes, reverts or stops anything.
3. If this session has a push-notification tool, send one line:
   `punchlist: <n> units done — stopped: <reason>`.

## 6. Report — this is the whole output

```
Autonomous run — <n> units, stopped: <reason>

| Unit | Outcome | Code | Review |
|---|---|---|---|
| P-### <short text> | done | abc1234 | fine |

New items: P-### …
Review before publishing: git log --oneline <START>..HEAD — nothing was pushed.
<N> items need you — run /punchlist:interview
```

After a failure, add the failed unit's report, the branch it left, and the exact next step. Leave out
the `needs` line when nothing needs the owner.

## Common mistakes

| Mistake | Instead |
|---|---|
| Two units at once | Strictly serial; wait for each completion before the next dispatch |
| Reading code, or finishing a unit yourself | Subagents work; you pick, check and report |
| `/punchlist:handoff` after each unit | `:next` already retires and refreshes STATE; you run compact and lint once at the end |
| Cleaning up after a failed unit | Stop and report; the owner decides |
| Pushing | Never, whatever `push:` says |
| Working `later` items | Only `workable` entries; `later` items come back through `/punchlist:interview` triage |
| Asking the owner mid-run | Talk to the owner only in the preflight line and the report |
````

- [ ] **Step 2: Wire it in**

`plugins/punchlist/reference/templates/claude-md-block.md` **and** `CLAUDE.md` — replace

```
Workflow skills: `/punchlist:next [P-###|finding-ID]` works one backlog unit end to end ·
`/punchlist:interview` clears items waiting on the owner · `/punchlist:add` captures an item ·
```

with

```
Workflow skills: `/punchlist:next [P-###|finding-ID]` works one backlog unit end to end ·
`/punchlist:autonomous [max]` works units unattended, one at a time ·
`/punchlist:interview` clears items waiting on the owner · `/punchlist:add` captures an item ·
```

`README.md` skills table, after the `/punchlist:next` row:

```
| `/punchlist:autonomous [max]` | Work the backlog unattended: one subagent per `:next` unit, strictly serial, stopping on failure or when only owner items remain; ends with a review of the run. Never pushes |
```

`docs/design.md` Components table, after the `skills/next` row:

```
| `skills/autonomous` | Orchestrate `:next` units through background subagents, one at a time; check after each unit; stop on failure, cap or owner-only items; compact, review the run, report. Never pushes |
```

- [ ] **Step 3: Validate and commit**

```bash
just check
git add plugins/punchlist/skills/autonomous plugins/punchlist/reference/templates/claude-md-block.md CLAUDE.md README.md docs/design.md
git commit -m "feat(skills): /punchlist:autonomous — serial subagent loop over :next (P-006)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Dry-run scenarios (repo rule 4)

Baseline (no skill) vs with-skill for each new or changed skill, against a scratch repo. Skills load
**from this checkout**: subagents only see the installed v0.4.0, so every prompt says "read and follow
`<checkout>/plugins/punchlist/skills/<name>/SKILL.md`" and sets `PL=<checkout>/plugins/punchlist/bin/punchlist`.
Subagents can't ask the user or spawn subagents, so `:interview` runs in a subagent with canned
answers, and `:autonomous` runs in the **main session** as orchestrator.

**Files:**
- Create (scratchpad only, not committed): `$SCRATCH/make-fixture.sh`, fixture repos, `asks.md` logs
- Modify: whichever `SKILL.md` a scenario shows is unclear (then re-run that scenario)

- [ ] **Step 1: Write `$SCRATCH/make-fixture.sh`** (`$SCRATCH` = this session's scratchpad directory):

```bash
#!/usr/bin/env bash
# Usage: make-fixture.sh <dir> — a scratch project with 2 workable items, 2 decisions, 1 action,
# 1 needs-ruling finding and 1 stale later item, plus a bare "origin" to detect pushes.
set -euo pipefail
dir="$1"; rm -rf "$dir" "$dir.remote.git"; mkdir -p "$dir/docs/history" "$dir/docs/code-review"
git init -q --bare "$dir.remote.git"
cd "$dir"; git init -q -b main; git config user.email t@example.com; git config user.name T
cat > calc.py <<'EOF'
def add(a, b):
    return a - b


def mean(values):
    return sum(values) / len(values)
EOF
cat > test_calc.py <<'EOF'
import unittest

from calc import mean


class CalcTest(unittest.TestCase):
    def test_mean(self):
        self.assertEqual(mean([1, 2, 3]), 2)
EOF
cat > CLAUDE.md <<'EOF'
# calc — scratch project for punchlist dry runs
EOF
cat > .punchlist.yml <<'EOF'
docs_dir: docs
base_branch: main
branch_prefix: punchlist/
push: allowed
owner: maintainer
gates:
  - run: python3 -m unittest
EOF
cat > docs/PUNCHLIST.md <<'EOF'
# PUNCHLIST — the single backlog of open work

- **ID** — `P-###`, never reused, never renumbered. Next free ID: **P-007**.

## Bugs

- **P-001** · now · `calc.add` subtracts instead of adding: `add(2, 3)` returns -1. `calc.py:2`.
- **P-002** · next · `calc.mean([])` raises ZeroDivisionError; it should return 0.0. `calc.py:6`.

## Features

- **P-003** · next · Choose how `calc` rounds money: banker's rounding or half-up. The invoicing
  export depends on it. `needs: decision`
- **P-004** · next · Pick a license for the `calc` package: MIT or Apache-2.0. `needs: decision`
- **P-006** · later · Maybe add a `median` function.

## Ops / manual

- **P-005** · next · Create the PyPI project and add the upload token to CI secrets. `needs: action`
EOF
cat > docs/code-review/01-calc.md <<'EOF'
# Code review — calc

## Findings

### CALC-001 · medium · `mean` accepts strings and fails confusingly
- **Where:** `calc.py:6`
- **Category:** correctness
- **Confidence:** confirmed
- **Status:** needs-ruling: reject non-numbers with TypeError, or coerce numeric strings?
- **Problem:** `mean(["1", "2"])` raises a TypeError from inside `sum`.
- **Failure scenario:** a CSV import passes strings straight through.
- **Suggested fix:** validate inputs up front.
- **Effort:** S
EOF
printf '# PUNCHLIST — done\n' > docs/history/punchlist-done.md
printf '# Build log\n\n## Index\n\n| Date | Milestone | Merge | Spec / plan |\n|---|---|---|---|\n\n## Entries\n' > docs/history/build-log.md
old=$(python3 -c 'import datetime; print((datetime.datetime.now() - datetime.timedelta(days=45)).isoformat(timespec="seconds"))')
git add -A; GIT_AUTHOR_DATE="$old" GIT_COMMITTER_DATE="$old" git commit -q -m "initial"
sha=$(git rev-parse --short HEAD)
cat > docs/STATE.md <<EOF
# STATE

## Snapshot — $(date +%F)

- **Branch:** \`main\` @ \`$sha\`, clean.
- **Last shipped:** nothing yet.
- **In flight:** nothing.

## Next up

1. P-001 — \`add\` subtracts.

## Orientation

1. \`CLAUDE.md\`.

## Recent milestones

- none

## Maintaining this file

Refresh at handoff.
EOF
git add -A; git commit -q -m "docs: state"
git remote add origin "$dir.remote.git"; git push -q -u origin main
```

- [ ] **Step 2: Sanity-check the fixture**

```bash
bash "$SCRATCH/make-fixture.sh" "$SCRATCH/fx"
PL=plugins/punchlist/bin/punchlist
$PL --root "$SCRATCH/fx" lint
$PL --root "$SCRATCH/fx" queue
```

Expected: lint `0 error(s)` (a stale-`later` WARN for P-006 is fine); queue shows Workable P-001, P-002;
Needs P-003, P-004, P-005, CALC-001; Triage P-006 (~45 days).

- [ ] **Step 3: `:interview` — baseline, then with-skill** (two fresh fixtures, two subagents)

Canned answers for both: rounding → the recommended option; license → Not now; PyPI → Done;
CALC-001 → reject with TypeError; `median` → Park.

Baseline prompt: "In `<fx>`, clear the punchlist items that need my input. You can't talk to me:
wherever you'd ask me something, append exactly what you'd show me to `<fx>/../asks-baseline.md` and
use these answers: <canned>. Then finish."

With-skill prompt: "In `<fx>`, read and follow `<checkout>/plugins/punchlist/skills/interview/SKILL.md`
with `PL=<checkout>/plugins/punchlist/bin/punchlist`. You can't talk to me or use AskUserQuestion:
wherever the skill calls it, append the chat briefs and the call's JSON to `<fx>/../asks-skill.md`, and
use these answers: <canned>. Dispatch no subagents; do the research yourself."

Pass (with-skill), checked by reading `asks-skill.md` and the fixture:
- Every brief leads with a plain-language headline; no brief starts with a P-ID.
- Each decision and ruling has ≥ 2 options with cost and reversibility, and one "(Recommended)" first.
- ≤ 4 questions per call; headers ≤ 12 characters.
- P-003 has a `Ruling YYYY-MM-DD:` line and no `needs:`; P-004 is still tagged; P-005 is in
  punchlist-done with `(manual)`; CALC-001 is `open — ruling …`; P-006 is in parked.md with `triaged`.
- `$PL --root <fx> lint` shows 0 errors; exactly one new commit; `git status` clean.

Record how the baseline differs (cryptic IDs? no recommendation? wrong formats?) in the scenario notes.

- [ ] **Step 4: `:interview` stop-early** — fresh fixture, with-skill prompt, but the canned answers
say the owner answers the first batch and then says "stop". Pass: the answers from batch 1 are
recorded and committed; unanswered items stay tagged; lint is clean.

- [ ] **Step 5: `:add`, `:next`, `:handoff` — baseline (installed v0.4.0) vs checkout**

On fresh fixtures, one subagent per case, with-skill = "read and follow `<checkout>/…/<skill>/SKILL.md`", baseline = invoke the installed skill:
- `:add` "we need to decide whether to support Python 3.8" → with-skill tags `needs: decision`; no
  Waiting-on line anywhere. Baseline: record where it put the owner item.
- `:add` "rotate the production API key" → `needs: action`.
- `:next P-003` → stops, saying it needs the owner; nothing changes.
- `:handoff` after a conversation in which the owner said "we should decide on a changelog format
  before 1.0" → a new item tagged `needs: decision`; report item 5 lists the `needs` group.

- [ ] **Step 6: `:autonomous` happy path — main session as orchestrator**

On a fresh fixture, `cd` into it and follow `<checkout>/plugins/punchlist/skills/autonomous/SKILL.md`
with `PL=<checkout>/plugins/punchlist/bin/punchlist`. Change only the unit prompt: "read and follow
`<checkout>/plugins/punchlist/skills/next/SKILL.md` with `PL=<checkout>/…/bin/punchlist`" instead of
"invoke the `punchlist:next` skill". Pass:
- Two units (P-001 then P-002), dispatched one at a time, each merged to `main` with a test.
- The run stops with "no workable entries"; the report says 4 items need the owner and suggests
  `/punchlist:interview`.
- The review ran and has a verdict for each unit.
- `git -C <fx>.remote.git rev-parse main` is unchanged (no push, despite `push: allowed`).
- `$PL --root <fx> lint` has 0 errors.

Baseline: a fresh fixture and the prompt "Work through this project's punchlist autonomously using
subagents until you're done." Record whether it ran units in parallel, pushed, or ran handoff after
each unit.

- [ ] **Step 7: `:autonomous` failure stop** — fresh fixture with the gate changed to
`python3 -m unittest && false`. Pass: the run stops after the first unit; the report names the branch
left behind and the exact next step; no cleanup, no stash, and nothing else dispatched.

- [ ] **Step 8: Fix what the scenarios exposed**

For each failed pass criterion, tighten the skill's wording (usually a Common-mistakes row or a
sharper step), re-run that scenario, and repeat until it passes. Commit the wording fixes:

```bash
just check
git add plugins/punchlist/skills
git commit -m "fix(skills): tighten interview/autonomous wording from dry runs (P-006)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Keep a short scenario log (baseline vs with-skill, pass/fail, fixes) for the build-log entry in Task 7.
The owner-says-stop check can't be simulated here; it moves to Task 8.

---

### Task 7: Retire P-006 and merge

Follow `/punchlist:next` §4 (retire) for P-006.

**Files:**
- Modify: `docs/PUNCHLIST.md`, `docs/history/punchlist-done.md`, `docs/history/build-log.md`, `docs/STATE.md`

- [ ] **Step 1:** `CODE_SHA=$(git log -1 --format=%h -- . ':(exclude)docs')` — the last code commit.
- [ ] **Step 2:** Cut P-006 from `docs/PUNCHLIST.md` and paste it under `## Features` in
  `docs/history/punchlist-done.md` (create the heading at the end if it's missing), followed by
  `  — DONE <today> (<CODE_SHA>): /punchlist:interview + /punchlist:autonomous, needs: marker, punchlist queue.`
- [ ] **Step 3:** Build log — an index row `| <today> | Interview + autonomous skills | \`<CODE_SHA>\` | \`docs/specs/2026-09-25-interview-autonomous-design.md\` · \`docs/plans/2026-09-25-interview-autonomous.md\` |`
  and an entry (≤ 15 lines): **Why** (owner items pile up, and working the backlog needs re-invoking
  `:next`); **What shipped** (the two skills, the `needs:` marker replacing Waiting-on, `punchlist queue`,
  item age spanning the item, `triage_after_days`); **Rulings** (R1–R10 by number, one line); **Deferred**
  (any new P-IDs); **Verification** (unit test count, dry-run scenario results; "owner stop and live
  dogfood pending Task 8").
- [ ] **Step 4:** STATE — Snapshot (today, `main` @ `<CODE_SHA>`, Last shipped: "P-006 interview +
  autonomous (unreleased — needs `just release minor`)", In flight: nothing); Next up refreshed from
  `$PL queue`; system-map Skills row
  `plugins/punchlist/skills/{setup,next,autonomous,interview,add,handoff,review,tidy}/SKILL.md`; roll
  Recent milestones.
- [ ] **Step 5:** File a P-item (`$PL next-id --bump`, `from: P-006`) for anything deferred or
  discovered, including — if Task 8 can't happen this session — "Dogfood `/punchlist:interview` and an
  owner-stopped `/punchlist:autonomous` on this repo after `just release minor`".
- [ ] **Step 6: Lint, commit, merge**

```bash
plugins/punchlist/bin/punchlist lint
just check
git add docs
git commit -m "docs(punchlist): retire P-006 — interview + autonomous skills

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git switch main
git merge --ff-only punchlist/P-006-interview-autonomous
git branch -d punchlist/P-006-interview-autonomous
```

Expected: fast-forward; lint `0 error(s)`. Do not push.

---

### Task 8: Release and dogfood (with the maintainer present)

- [ ] **Step 1:** Ask the maintainer to approve `just release minor` (→ v0.5.0: new skills and a
  format change). On yes, run it. It commits, tags, reinstalls and re-points STATE's snapshot.
- [ ] **Step 2:** Ask the maintainer to run `/reload-plugins` (or restart the session), so the Skill
  tool and subagents load v0.5.0.
- [ ] **Step 3:** Run `/punchlist:interview` on this repo. Expected queue: P-005 (a real
  `needs: action` candidate — offer to tag it in the heuristic sweep) plus any triage-due `later`
  items. Check the briefs against Task 6 Step 3's pass criteria, live. Also confirm, live, that the
  research subagents return every brief field and that AskUserQuestion accepts the `preview` option
  field.
- [ ] **Step 4:** Run `/punchlist:autonomous 2` on this repo and have the maintainer say "stop" while
  the first unit runs. Pass: the unit finishes, the checks run, the run stops with "stopped by owner",
  and the review and report still happen. Note: after P-006 retires, this repo's only workable item
  is P-001 (large — headless smoke); `:next` should size it as large and write a spec/plan as its
  unit, or queue a small item first for the owner-stop test.
- [ ] **Step 5:** Anything found becomes a P-item (`from: P-006`). If the P-item from Task 7 Step 5
  was filed, retire it (`— DONE <date> (manual): dogfooded`). Commit
  `docs(punchlist): dogfood interview + autonomous`. The maintainer publishes with `just publish`.
