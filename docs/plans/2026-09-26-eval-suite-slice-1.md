# Eval suite — slice 1 plan (P-001)

**Spec:** `docs/specs/2026-09-26-eval-suite-design.md` (rulings E1–E5 are binding).
**Goal:** a working `claude plugin eval` suite under `plugins/punchlist/evals/` with smoke cases
for add, next, handoff, brief and setup, runnable as `just eval`.
**Docs:** <https://code.claude.com/docs/en/plugin-evals> — read the case.yaml fields, grader types
and "What a grader can look at" sections before writing cases.

## Constraints

- Evals are not part of `just check`: they cost money and need credentials. `just check` must stay
  green and fast.
- A case's scaffold runs as you, outside the sandbox, only with `--scaffold`. Scaffolds build
  throwaway repos in the run's workspace and touch nothing else.
- Grade outcomes loosely: markers, headings, SHA shapes. Never grade exact wording.
- Every task that runs evals uses `--runs 1 --max-cost-usd 5` while iterating (`--ablation none`
  halves the cost further while tuning graders). Record the reported cost in the task's commit
  message.
- Commits carry `(P-001)`; `just check` before every commit; never push.

## Tasks

### 1. Spike (settles spec E5; ~1 run each)

Create `plugins/punchlist/evals/add-owner-decision/` with the case below and a minimal inline
`fixture.sh` (no shared lib yet). Run
`claude plugin eval plugins/punchlist --case add-owner-decision --scaffold --allow-tools Bash Write Edit --runs 1 --max-cost-usd 5 --no-publish`.
Also make a throwaway case (deleted afterwards) whose prompt asks Claude to call `AskUserQuestion`,
to see what a non-interactive run returns. Record in the spec, under a new "Spike results" section:
pass/fail per grader, time and cost per run, the `AskUserQuestion` behavior, whether
`$(dirname "$0")` in a scaffold resolves to the case directory, and whether the `skill-fired`
grader matched a slash-command prompt. Adjust E4/E5 and the case table if the numbers demand it.

```yaml
# plugins/punchlist/evals/add-owner-decision/case.yaml
schema_version: "1.1"
name: add-owner-decision
description: An owner's "we need to decide" request is captured and tagged as their decision.
tags: [smoke]
execution:
  prompt: "/punchlist:add we need to decide whether to support Python 3.8"
  max_turns: 25
  timeout_seconds: 300
  allowed_tools: [Read, Glob, Grep, Skill]
context:
  scaffold_script: fixture.sh
graders:
  - name: skill-fired
    type: tool_used
    tool: Skill
    input_match: '"skill"\s*:\s*"(?:[\w-]+:)?add"'
  - name: tagged-as-owner-decision
    type: regex
    target: { source: file, path: docs/PUNCHLIST.md }
    pattern: 'Python 3\.8[^\n]*(?:\n  [^\n]*)*`needs: decision`'
  - name: kept-out-of-next-up
    type: regex
    target: { source: file, path: docs/STATE.md }
    pattern: 'Python 3\.8'
    match: not_contains
  - name: committed
    type: tool_used
    tool: Bash
    input_match: 'git commit'
```

Commit: `test(evals): spike — first case and findings (P-001)`.

### 2. Shared fixture and plumbing

- `plugins/punchlist/evals/_lib/fixture.sh`: the standard scratch project from the spec's Layout
  section (reuse the P-006 dry-run fixture: `calc.py` + `test_calc.py`, `.punchlist.yml` with gate
  `python3 -m unittest`, PUNCHLIST with P-001…P-006, a `needs-ruling:` finding, the `later` item
  committed with a date 45 days back, STATE whose snapshot names the code commit). It must leave
  `punchlist lint` at 0 errors.
- Make `_lib` not count as a case (a directory is a case only if it holds `prompt.md` or
  `case.yaml`).
- Point the spike case's `fixture.sh` at the shared lib, if the spike showed that works; otherwise
  generate per-case copies from one source with a small `just eval-fixtures` recipe.
- Add `plugins/punchlist/evals/results/` to `.gitignore`.
- Commit: `test(evals): shared fixture (P-001)`.

### 3–7. Cases

One commit per task, each case graded as the spec's table says. Run each case once and fix graders
until they pass for the right reason; check the no-plugin baseline arm fails the plugin-specific
graders (proof the grader measures the skill, not the model's defaults).

3. `add-plain-bug`.
4. `next-works-a-bug` and `next-skips-owner-item` (the second uses `tool_used: Edit` with
   `input_match: 'calc\.py'`, `min: 0`, `max: 0`).
5. `handoff-files-owner-question`: the prompt describes a session (no code changed; the owner said
   "we should decide on a changelog format before 1.0") and asks for a handoff.
6. `brief-is-read-only`: `tool_used` `Write` and `Edit` with `max: 0`; an `llm` grader on
   `last_message`: PASS if there are three sections (where things stand, what was built lately,
   what's next), it's in full sentences, and it says one or more items wait on the owner; FAIL if it
   leads with IDs or pastes raw item lines.
7. `setup-new-project`: its own scaffold (a small git repo with code, a README and no docs); graders
   on `file_exists` for `.punchlist.yml`, `docs/STATE.md` and `docs/PUNCHLIST.md`, plus the trace's
   `lint: 0 error`.

### 8. Verbs and docs

- `justfile`: `eval` (smoke: `--tag smoke --runs 1 --max-cost-usd 5 --scaffold --allow-tools Bash
  Write Edit --no-publish`) and `eval-full` (all cases, default runs, `--max-cost-usd 25`). Both take
  optional extra args, such as `--case <glob>`.
- STATE Verbs: add both, noting they cost money and aren't the gate. README "Develop": one
  paragraph. `docs/design.md` Testing: evals replace the hand-run dry runs for covered skills (rule 4
  itself changes only after the owner decides P-013).
- Commit: `docs: eval verbs (P-001)`.

### 9. Full smoke run and close-out

Run `just eval`; every smoke case passes. Record the with/without deltas and total cost in the
build-log entry. Retire P-001 per `/punchlist:next` §4.
