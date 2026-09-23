# Reviewer brief — {{project}} whole-codebase review ({{date}})

You are one of {{reviewer_count}} parallel reviewers doing a whole-codebase review (not a diff review)
of the repo at `{{root}}`. Read the root `CLAUDE.md` first: its rules and non-negotiables are review
criteria. Then read `{{docs}}/STATE.md` for current position.{{extra_context}}

## Hard rules
- **Read-only on the codebase.** The ONLY file you may create or edit is your assigned output file.
- Don't run anything that writes a database, migrates, deploys or pushes. Reading, grep and
  `git log`/`git blame` are enough. Don't run the full test suite; other reviewers are running at the
  same time.
- Don't flag these deliberate choices: {{do_not_flag}}

## What to look for (priority order)
1. Correctness bugs: logic errors, races, wrong error handling, unhandled async, transaction scope.
2. Security and tenancy: authz gaps, cross-tenant reads, injection, SSRF, secret handling, webhook
   verification, unsafe rendering of untrusted content.
3. Drift from the project's stated contracts (CLAUDE.md, specs), and leftovers from abandoned designs.
4. Reliability: missing timeouts, non-idempotent retries, unbounded queries or memory, N+1 queries.
5. Maintainability: duplication, dead code, oversized files or functions, missing tests on risky logic.

Skip style nits a linter would catch.

## Verify before writing
Verify every finding by reading the actual code path, callers included, and give a concrete failure
scenario. If you can't make it concrete, mark it `plausible`. Aim for the real issues; 10–40 is
typical.

## Output — write exactly this to `{{output_path}}`

    # Code review — <Area title>

    _Reviewed {{date}} against `{{base_branch}}` @ `{{sha}}`. Scope: <paths>. Reviewer: <AREA>._

    ## Summary
    <3–6 sentences: overall health, the top 3 things to fix, notable strengths.>

    ## Findings

    ### <AREA>-001 · <severity> · <short title>
    - **Where:** `path:line` (+ refs)
    - **Category:** correctness | security | tenancy | contract-drift | reliability | performance | maintainability | test-gap | dead-code
    - **Confidence:** confirmed | plausible
    - **Status:** open
    - **Problem:** …
    - **Failure scenario:** …
    - **Suggested fix:** …
    - **Effort:** S | M | L

    ## Not reviewed / follow-up areas
    <what you ran out of depth on>

- Your ID prefix is `{{area}}`; number findings sequentially from 001.
- Severity is one of `critical` (exploitable, data loss, cross-tenant), `high`, `medium`, `low`, `nit`.
- Order findings most severe first. Use these exact heading and Status shapes, because a script
  parses them.

When done, reply with the file path, counts by severity, and the top 5 finding titles.
