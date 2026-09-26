# End-to-end skill evals with `claude plugin eval` — design

P-001 (absorbs P-003) · 2026-09-26 · Size: large → two slices, plus two owner decisions

## Why

Skills are verified today by hand-run dry runs: a subagent is told to read the checkout's `SKILL.md`
and follow it against a scratch repo. That is slow, unrepeatable, and skips the real loading path —
the Skill tool, `${CLAUDE_PLUGIN_ROOT}` expansion, and the fact that subagents see the *installed*
version, not the checkout. P-001 asked for real headless runs; P-003 asked for an automated
regression suite. `claude plugin eval` (Claude Code ≥ 2.1.281) does both.

## Approach (E1)

Build on `claude plugin eval` rather than a hand-rolled `claude -p` harness. It already provides
(docs: <https://code.claude.com/docs/en/plugin-evals>):

- A fresh, isolated, non-interactive workspace per run, with only this plugin loaded — no user
  settings, other plugins or memory.
- `context.scaffold_script`: Bash that runs in the empty workspace before Claude starts and can build
  a git repo with fixture docs (only under `--scaffold`).
- A path target loads the plugin from the **working tree**, so unreleased skill text is what gets
  tested — no release or restart needed.
- Graders over the final reply, the full trace, tool calls, and **file contents after the run**
  (`target: { source: file, path: … }`).
- A no-plugin **baseline arm** (`--ablation with-without`, the default) — the before/after comparison
  repo rule 4 asks for, built in.
- Cost ceilings (`--max-cost-usd`), JSON results, exit codes, an HTML report.

A `claude -p` harness would reimplement all of this.

## Layout

- The eval dir must sit below the plugin, so the suite lives at `plugins/punchlist/evals/` (the
  default; no manifest change). It ships with the plugin — small text files. `evals/results/` is
  gitignored.
- `evals/_lib/fixture.sh` builds the standard scratch project (the dry-run fixture used for P-006):
  a tiny `calc.py` with a unittest gate, `.punchlist.yml`, STATE, and a PUNCHLIST holding two workable
  bugs, two `needs: decision` items, one `needs: action` item, a `needs-ruling:` finding, and a
  `later` item backdated 45 days. Each case's own `fixture.sh` calls it, then adjusts.
- One directory per case: `evals/<skill>-<scenario>/case.yaml` (+ `fixture.sh`), graders inline.
- Tags: `smoke` for cheap cases worth running after any skill-wording change; `slow` for cases that
  dispatch subagents (autonomous, review).

## Grading

- **Deterministic first; they cost nothing.** `regex` against file contents after the run (e.g.
  `docs/PUNCHLIST.md` gained `` `needs: decision` ``), `tool_used` (e.g. `Skill` with
  `input_match: punchlist:add` — a with-only, plugin-fired indicator; `Bash` matching
  `git commit`; `Edit` on `calc.py` with `max: 0` to prove a skip), and `regex` over the `trace`
  for the skill's own `lint: 0 error(s)` line.
- There is **no shell grader**, so lint results and git state are graded through the skill's own
  commands in the trace or through file contents.
- `llm` graders (judge: haiku) only where the output is prose: `:brief`, and `:interview`'s briefs.
- Assert outcomes loosely (a marker, a heading, a SHA-shaped string), never exact wording — skills
  are model-driven.

## Cases

**Slice 1 (P-001): the harness plus smoke cases for the script-backed skills**

| Case | Prompt | Passes when |
|---|---|---|
| `add-owner-decision` | `/punchlist:add we need to decide whether to support Python 3.8` | PUNCHLIST has a new item with `needs: decision`; STATE Next up doesn't list it; a `docs(punchlist): add` commit |
| `add-plain-bug` | `/punchlist:add export crashes on empty input` | New item under Bugs, no `needs:` marker; counter advanced |
| `next-works-a-bug` | `/punchlist:next` | `calc.py` fixed; the done file has a `— DONE … (<sha>)` line for the picked item; lint clean in the trace; a fast-forward merge |
| `next-skips-owner-item` | `/punchlist:next P-003` | No `Edit` of `calc.py`; the reply says it needs the owner |
| `handoff-files-owner-question` | A short account of a session, then "hand off" | New item tagged `needs: decision` and `from:`; STATE refreshed; one handoff commit |
| `brief-is-read-only` | `/punchlist:brief` | No `Write`/`Edit`/`git commit`; judge: three plain-language sections, names the item waiting on the owner |
| `setup-new-project` | `/punchlist:setup` in a small repo with no docs | `.punchlist.yml`, `docs/STATE.md`, `docs/PUNCHLIST.md` created; lint clean in the trace |

**Slice 2 (P-011): the rest** — `setup` upgrade (legacy Waiting-on migration), `tidy` (a stale doc),
`interview` (as far as the spike shows questions can go), `autonomous` (`slow`, `max-units 2`),
`review` (`slow`).

## Running it

- `just eval` → `claude plugin eval plugins/punchlist --scaffold --allow-tools Bash Write Edit
  --tag smoke --runs 1 --max-cost-usd 5 --no-publish`. For iterating on a skill.
- `just eval-full` → every case, default 3 runs, `--max-cost-usd 25`. Before a release.
- Neither is part of `just check`: they take minutes, need model credentials and cost money.

## Owner decisions (filed as `needs: decision` items)

- **D1 — CI (P-012).** Run the smoke suite in CI? It needs an API-key secret and spends money on
  every run. **Decided 2026-09-26: no** — evals stay local.
- **D2 — Rule 4 (P-013).** Once slice 1 passes, replace CLAUDE.md rule 4's hand-run dry runs with
  `just eval`. That changes a documented contract, so it's the owner's call. **Decided 2026-09-26:
  yes** — done by P-013 after slice 1 passes.

## Rulings

- **E1** — `claude plugin eval`, not a `claude -p` harness (see Approach).
- **E2** — P-003 is merged into P-001 and dropped as a separate item.
- **E3** — The suite lives under `plugins/punchlist/evals/` and ships with the plugin; results are
  gitignored.
- **E4** — `smoke` runs once per case under a cost ceiling; the full suite runs on demand.
- **E6** — No CI: `just eval` is run locally by whoever changes skill text (owner, D1).
- **E7** — Rule 4 switches to `just eval` once slice 1 passes (owner, D2; P-013).
- **E5** — Unknowns are settled by a spike as slice 1's first task: what happens when a skill calls
  `AskUserQuestion` in a non-interactive run; whether a case's scaffold can call the shared
  `_lib/fixture.sh` (via `$(dirname "$0")`); whether `tool_used: Skill` fires for a slash-command
  prompt; the time and cost of one run.

## Risks

- **Flakiness.** Model-driven skills vary between runs. Loose graders, and in full mode a
  `--threshold` below 1.0 if three-run cases prove noisy (decided from the spike's numbers).
- **Cost.** Measured in the spike; the ceilings above bound it.
- **Questions.** If `AskUserQuestion` can't be answered in a run, `:interview` is graded only up to
  its first question, and the rest stays a manual check.
