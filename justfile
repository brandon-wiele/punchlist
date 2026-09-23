# punchlist plugin — dev + release tasks.

set shell := ["bash", "-euo", "pipefail", "-c"]

manifest := "plugins/punchlist/.claude-plugin/plugin.json"
marketplace := "punchlist"
plugin := "punchlist@punchlist"

default:
    @just --list

# Unit tests for the punchlist script.
test:
    python3 -m unittest discover -s tests

# Validate the marketplace and plugin manifests (and skill frontmatter).
validate:
    claude plugin validate .
    claude plugin validate plugins/punchlist

# Everything a release requires.
check: test validate

# Current plugin version.
version:
    @python3 -c 'import json; print(json.load(open("{{manifest}}"))["version"])'

# First-time install on this machine (user scope, every project).
install:
    claude plugin marketplace add "{{justfile_directory()}}"
    claude plugin install {{plugin}}

# Release: `just release` (patch), `just release minor`, `just release major`, or `just release 1.4.0`.
# Requires a clean tree; runs checks, bumps the version, commits, tags, and updates the installed copy.
release bump="patch": check
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -n "$(git status --porcelain)" ]; then
        echo "release: commit or stash your changes first — the release commit must contain only the version bump" >&2
        git status --short >&2
        exit 1
    fi
    new=$(python3 - "{{manifest}}" "{{bump}}" <<'PY'
    import json, re, sys
    path, bump = sys.argv[1], sys.argv[2]
    data = json.load(open(path))
    major, minor, patch = (int(n) for n in data["version"].split("."))
    if re.fullmatch(r"\d+\.\d+\.\d+", bump):
        new = bump
    elif bump == "major":
        new = f"{major + 1}.0.0"
    elif bump == "minor":
        new = f"{major}.{minor + 1}.0"
    elif bump == "patch":
        new = f"{major}.{minor}.{patch + 1}"
    else:
        sys.exit(f"release: bump must be patch, minor, major or X.Y.Z (got {bump!r})")
    if tuple(map(int, new.split("."))) <= (major, minor, patch):
        sys.exit(f"release: {new} is not newer than {data['version']}")
    data["version"] = new
    with open(path, "w") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
    print(new)
    PY
    )
    git add "{{manifest}}"
    git commit -q -m "release: v${new}"
    git tag "v${new}"
    claude plugin marketplace update {{marketplace}}
    claude plugin update {{plugin}}
    # The release commit is a code commit, so point this repo's own STATE snapshot at it.
    just _snapshot "release v${new}"
    echo "released v${new} — restart Claude Code sessions (or /reload-plugins) to pick it up"

# Push main and tags to GitHub. Maintainer only: sessions never push. Run after `just release`.
publish:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ "$(git branch --show-current)" != "main" ]; then echo "publish: switch to main first" >&2; exit 1; fi
    if [ -n "$(git status --porcelain)" ]; then echo "publish: working tree not clean" >&2; git status --short >&2; exit 1; fi
    just check
    git push origin main --tags
    echo "published $(git describe --tags --abbrev=0) — users update with: /plugin marketplace update {{marketplace}}"

# Point docs/STATE.md's snapshot at HEAD and commit it (used after releases).
_snapshot reason:
    #!/usr/bin/env bash
    set -euo pipefail
    sha=$(git rev-parse --short HEAD)
    sed -i '' -E "s/(\*\*Branch:\*\*[^@]*@ \`)[0-9a-f]+(\`)/\1${sha}\2/" docs/STATE.md
    plugins/punchlist/bin/punchlist lint
    git commit -q -m "docs(punchlist): snapshot at ${sha} ({{reason}})" -- docs/STATE.md
