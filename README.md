# punchlist

**Long-running projects driven by many AI sessions lose the thread.** Each session starts cold,
nobody is sure what's done, what's next or what was deferred, and stale docs quietly send agents
back to designs the project abandoned.

`punchlist` is a Claude Code plugin that keeps a project oriented:

- **`STATE.md`** is a lean "where we are" doc: snapshot, next up and orientation, read at the start of
  every session.
- **`PUNCHLIST.md`** is the *only* backlog. Every open item has a stable `P-###` ID and a
  now/next/later priority.
- **History files** (build log, done items, parked items) record what shipped without bloating what
  sessions read.
- **Strict handoffs** and a **one-item-at-a-time** workflow keep the docs honest.
- A small **stdlib Python script** does the mechanical part: it counts, lints, compacts, and
  inventories docs for staleness, so the docs stay small enough to read every session.

## Skills

| Skill | Use |
|---|---|
| `/punchlist:setup` | Add the system to a new or existing project (seeds from the repo), or upgrade it |
| `/punchlist:next [P-###\|finding]` | Work one backlog unit end to end: pick → build → gates → merge → retire |
| `/punchlist:autonomous [max]` | Work the backlog unattended: one subagent per `:next` unit, strictly serial, stopping on failure or when only owner items remain; ends with a review of the run. Never pushes |
| `/punchlist:interview [IDs\|group]` | Clear what waits on you: researched, PM-style briefs for decisions, rulings, manual tasks and stale items, asked in batches and recorded |
| `/punchlist:add <text>` | Capture an item under the next free ID |
| `/punchlist:handoff` | End-of-session routine, plus lint and compact |
| `/punchlist:review` | Parallel whole-codebase review into `docs/code-review/`, wired into the backlog |
| `/punchlist:tidy` | Triage existing docs, specs and plans: keep the current ones, archive superseded ones with the reason, file rewrites as P-items, and write a docs index |

## Install

In Claude Code:

```
/plugin marketplace add brandon-wiele/punchlist
/plugin install punchlist@punchlist
```

Then, in a project, run `/punchlist:setup`. Per-project settings (docs folder, base branch, gate
commands, push policy, size budgets) live in `.punchlist.yml` at the project root.

## The script

```
plugins/punchlist/bin/punchlist [--root <project>] <command>

  config              resolved .punchlist.yml as JSON
  status [--write]    open/done counts; --write regenerates the code-review roll-up
  next-id [--bump]    the next free P-ID
  queue [--json]      workable / needs-you / triage lists — the pick order the skills use
  lint                budgets and consistency checks; exits 1 on any ERROR
  compact [--apply]   collapse closed findings, park stale `later` items
  docs [--under P]    staleness evidence for /punchlist:tidy
```

It needs Python 3.9+ and git, and has no other dependencies. Document formats are defined in
[`plugins/punchlist/reference/formats.md`](plugins/punchlist/reference/formats.md).

## Develop

This repo uses punchlist on itself. Start with [`docs/STATE.md`](docs/STATE.md).

```bash
just check                 # unit tests + manifest validation
just install               # install from this checkout (local marketplace)
just release [minor|…]     # bump, commit, tag, reinstall locally
just publish               # push main + tags (maintainer)
```

Installs are cached per plugin version, so a change reaches sessions only after `just release`.

## License

[MIT](LICENSE)
