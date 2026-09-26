# punchlist

**Long-running projects driven by many AI sessions lose the thread.** Each session starts cold,
nobody is sure what's done, what's next or what was deferred, and stale docs quietly send agents
back to designs the project abandoned.

`punchlist` is a Claude Code plugin that keeps a project oriented. It gives your repo a small set of
plain Markdown files that every session reads and keeps up to date, and a handful of commands for
the moments that matter: starting work, picking what's next, capturing an idea, and wrapping up.

- **`STATE.md`** — where the project is right now and what's next, read at the start of every
  session.
- **`PUNCHLIST.md`** — the *only* backlog. Every open item has a stable ID like `P-012` and a
  priority of `now`, `next` or `later`.
- **History files** — what shipped and what was closed, kept out of the way so the files sessions
  read stay short.

Everything is ordinary Markdown in your repo, committed alongside your code. There's no service,
no account and nothing to host.

## Getting started

### 1. Install the plugin

In Claude Code:

```
/plugin marketplace add brandon-wiele/punchlist
/plugin install punchlist@punchlist
```

Restart Claude Code afterwards so the commands appear.

### 2. Set up a project

Open Claude Code in your project (it must be a git repo) and run:

```
/punchlist:setup
```

Setup looks at the repo before it asks anything. In an existing codebase it drafts the backlog from
your TODOs, issues and docs, and the history from your git log. In a new project it starts from
templates and asks a few questions. It then shows you, in one go, the settings it detected (docs
folder, main branch, the test command that must pass before work is committed) and previews of the
new files. Nothing is written until you approve.

You end up with:

| File | What it's for |
|---|---|
| `.punchlist.yml` | Per-project settings |
| `docs/STATE.md` | Where things stand and what's next |
| `docs/PUNCHLIST.md` | The backlog |
| `docs/history/` | The build log and closed items |
| A section in `CLAUDE.md` | Tells every session to read STATE first and how to hand off |

If the project already has a pile of docs, setup offers to run `/punchlist:tidy` next, and it can
also offer a full codebase review to seed the backlog. It never runs either without asking.

### 3. Work your first item

```
/punchlist:next
```

This picks the top item from the backlog, builds it (test-first where it can), runs your test
command, commits, merges it into your main branch locally, and updates the docs. You get a short
report of what changed and what's next.

## A typical week

- **Coming back to the project?** `/punchlist:brief` tells you in plain language where things
  stand, what got built recently and why it matters, and what's next.
- **Ready to build?** `/punchlist:next` works one item from start to finish. Name one to pick it
  yourself: `/punchlist:next P-014`.
- **Something came up mid-task?** `/punchlist:add` captures it without derailing you.
- **Stepping away, or about to clear the conversation?** `/punchlist:handoff` records what was
  done, what was deferred, and where the next session should pick up.
- **Items waiting on your decision?** `/punchlist:interview` walks you through them one question at
  a time, each with context, options and a recommendation, and records your answers.
- **Want the backlog worked while you're away?** `/punchlist:autonomous` runs `/punchlist:next`
  repeatedly, one item at a time, and stops when something fails or only your decisions are left.
- **Every so often:** `/punchlist:review` for a whole-codebase health check, and `/punchlist:tidy`
  when the docs have drifted.

## Skills

### `/punchlist:brief [N]` — catch up

Use it at the start of a session, or after a week away. It's read-only.

```
/punchlist:brief
```

You get three short sections: where the project stands (release, anything half-finished, anything
unhealthy), what the last few finished items built and why they matter, and what's next, including
anything waiting on you. `N` is how many finished items to cover (default 5).

### `/punchlist:next [P-###]` — work one item end to end

Use it whenever you want progress. With no argument it takes the top of the backlog; with an ID it
takes that item.

```
/punchlist:next
/punchlist:next P-014
```

One run is one unit of work: pick, build, run your checks, commit, merge locally, update the docs,
report. If the item is too big for one sitting, it writes a plan and splits the work into new
items instead. If an item needs your decision, it tags it and moves on rather than guessing.

### `/punchlist:add <what>` — capture something

Use it the moment you notice a bug, an idea or a chore, so it isn't lost.

```
/punchlist:add export button returns a 500 when the CSV is empty
/punchlist:add we need to decide whether to support Python 3.8
/punchlist:add rotate the production API key
```

It checks for duplicates, files the item in the right section with the next free ID, and commits
it. Items only you can move, like the last two above, are tagged so sessions don't try them.

### `/punchlist:handoff` — close a session

Use it before you stop, or before clearing the conversation, after any session that changed code or
priorities.

```
/punchlist:handoff
```

It turns anything deferred or discovered into backlog items, closes what was finished, updates the
build log and refreshes STATE, so tomorrow's session starts from an accurate picture.

### `/punchlist:interview` — answer what's waiting on you

Use it when decisions pile up, or after an autonomous run stops on items that need you.

```
/punchlist:interview
```

It researches each open question first, then asks you in small batches. Each question comes with
plain-language context, what it's blocking, two or three options with their cost and risk, and a
recommendation. Your answers are recorded as you go, so stopping halfway loses nothing.

### `/punchlist:autonomous [max]` — let it run

Use it when the backlog has clear, self-contained items and you'd like them done without watching.

```
/punchlist:autonomous
/punchlist:autonomous 3
```

It works items one at a time, each in a fresh sub-agent, checks the repo after every item, and stops
on the first failure, when only your decisions remain, or after `max` items (default 10). It ends
with a review of everything it did and never pushes. You can tell it to stop at any time; it
finishes the current item first.

### `/punchlist:review` — whole-codebase health check

Use it when you adopt punchlist on an existing project, or every few months.

```
/punchlist:review
```

Several read-only reviewers look at the codebase in parallel. Findings land in `docs/code-review/`
with a short "fix first" list, and one backlog item points at that list so `/punchlist:next` can
work through it.

### `/punchlist:tidy` — clean up stale docs

Use it when sessions keep building from outdated specs or notes, or after a big rewrite.

```
/punchlist:tidy
```

It checks each doc against the code, proposes what to keep, archive (with the reason) or rewrite,
and waits for your approval before moving anything. It also writes a docs index.

### `/punchlist:setup` — add or upgrade

Covered in [Getting started](#2-set-up-a-project). Run it again after updating the plugin to refresh
the section it manages in `CLAUDE.md`.

## Good to know

- **Nothing is pushed.** Work is committed and merged locally; you push when you're ready. (Set
  `push: allowed` in `.punchlist.yml` if you want sessions to push.)
- **Your checks are the gate.** Work is only committed after the commands listed under `gates:` in
  `.punchlist.yml` pass.
- **Decisions stay yours.** Items that need you, such as product choices, spending money, or anything
  public, are tagged and skipped by sessions until you answer them.
- **After updating the plugin, restart Claude Code.** Reloading plugins isn't enough to pick up
  newly added commands.

## Configuration

`.punchlist.yml` sits at the project root. Setup writes it; you rarely need to touch it.

```yaml
docs_dir: docs              # where STATE, PUNCHLIST and history live
base_branch: main           # where finished work is merged
push: never                 # never | allowed
owner: Jordan               # who "needs you" items wait on
gates:                      # must pass before any work is committed
  - run: npm test
  - run: npm run lint
    when: src/**            # optional: only when these paths changed
```

The full format, including size budgets, is in
[`plugins/punchlist/reference/formats.md`](plugins/punchlist/reference/formats.md).

## The script

The skills lean on a small helper script that does the mechanical parts. You don't need to run it,
but it's there if you want to check a project by hand:

```
plugins/punchlist/bin/punchlist [--root <project>] <command>

  config              resolved .punchlist.yml as JSON
  status [--write]    open/done counts; --write regenerates the code-review roll-up
  next-id [--bump]    the next free P-ID
  queue [--json]      workable / needs-you / triage lists — the pick order the skills use
  recent [--limit N]  the last N finished units, newest first (for /punchlist:brief)
  lint                budgets and consistency checks; exits 1 on any ERROR
  compact [--apply]   collapse closed findings, park stale `later` items
  docs [--under P]    staleness evidence for /punchlist:tidy
```

It needs Python 3.9+ and git, and has no other dependencies.

## Develop

This repo uses punchlist on itself. Start with [`docs/STATE.md`](docs/STATE.md).

```bash
just check                 # unit tests + manifest validation
just install               # install from this checkout (local marketplace)
just release [minor|…]     # bump, commit, tag, reinstall locally
just publish               # push main + tags (maintainer)
```

Installs are cached per plugin version, so a change reaches sessions only after `just release` and a
restart.

## Privacy

punchlist collects nothing and has no telemetry. It runs entirely on your machine:

- The helper script only reads and writes files in your project and runs `git`. It makes no network
  requests.
- `/punchlist:setup` can use your own `gh` command-line tool, if you have it, to read your repo's
  settings and open issues when drafting the backlog.
- Nothing is pushed anywhere unless you set `push: allowed` in `.punchlist.yml`.

The commands run inside Claude Code, which handles your conversation and the files it reads under
Anthropic's own terms and privacy policy, the same as any other Claude Code session.

## License

[MIT](LICENSE)
