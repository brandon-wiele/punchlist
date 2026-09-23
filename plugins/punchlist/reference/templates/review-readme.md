# Code review — {{date}} (whole codebase, `{{base_branch}}` @ `{{sha}}`)

A static, read-only review by {{reviewer_count}} parallel reviewers, one per area. Every finding was
checked against the code path it describes; `plausible` marks the ones a reviewer couldn't fully
confirm.

## How to use these files

- Finding IDs are stable. Cite them in commits (`fix(x): … (<ID>)`) and in PUNCHLIST items.
- Update a finding's `Status:` line in place: `fixed <sha>`, `wontfix: <why>`, `dup of <ID>`, or
  `needs-ruling: <question>`. `punchlist compact` later collapses closed findings to one line.
- Re-read the cited code before acting; line numbers drift.
- Work the Fix-first table through `/punchlist:next`. The umbrella PUNCHLIST item {{umbrella_id}}
  retires when its last row closes.

## Roll-up

<!-- punchlist:status:begin -->
<!-- punchlist:status:end -->

## Files

| File | Scope |
|---|---|
{{file_rows}}

{{strengths}}

## Themes (cross-file clusters)

{{themes}}

## Fix first (suggested order)

| # | Finding(s) | Why first | Effort |
|---|---|---|---|
{{fix_first_rows}}
