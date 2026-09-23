# Build log — shipped milestones (newest first)

> Companion to [`../STATE.md`](../STATE.md). STATE says where we are; this file says how we got here.
> Read the **index table** first and open entries by grep. Releases are tagged `vX.Y.Z`.

## Index

| Date | Milestone | Merge | Spec / plan |
|---|---|---|---|
| 2026-09-23 | v0.4.0 — first public release | `v0.4.0` | `docs/design.md` |

## Entries

### 2026-09-23 — v0.4.0, first public release — tag `v0.4.0`
design `docs/design.md`
- **What shipped:** six skills (`setup`, `next`, `add`, `handoff`, `review`, `tidy`); the normative
  formats reference and templates; the stdlib `punchlist` script (`config`, `status`, `next-id`,
  `lint`, `compact`, `docs`) with 27 unit tests; a `justfile` for check/release/publish.
- **Verification:** unit tests plus dry-run scenario tests (baseline vs with-skill) for every skill,
  and a pilot on a large, long-running project.
