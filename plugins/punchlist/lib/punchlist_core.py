"""Core of the `punchlist` CLI: parse the continuity docs, count, lint, compact.

Stdlib only, so it runs anywhere Python 3.9+ does. The document shapes it parses are defined in
reference/formats.md; keep the two in step.
"""

from __future__ import annotations

import datetime as _dt
import difflib
import fnmatch
import re
import subprocess
from pathlib import Path
from typing import Callable

DEFAULT_CONFIG = {
    "docs_dir": "docs",
    "base_branch": "main",
    "branch_prefix": "punchlist/",
    "push": "never",
    "owner": "the maintainer",
    "gates": [],
    "build_log_since": None,
    "planning_rules": True,
    "docs_exclude": [],  # globs of whole files `punchlist docs` skips (generated mirrors, vendored docs)
    "docs_ignore_tags": ["laravel-boost-guidelines"],  # <tag>…</tag> regions are generated vendor text
    "budgets": {
        "state_lines": 120,
        "punchlist_lines": 250,
        "build_log_entry_lines": 15,
        "stale_later_days": 60,
        "triage_after_days": 30,
    },
}

PRIORITIES = ("now", "next", "later")
SEVERITIES = ("critical", "high", "medium", "low", "nit")
NEEDS_KINDS = ("decision", "action")

COUNTER_RE = re.compile(r"Next free ID: \*\*P-(\d+)\*\*")
ITEM_RE = re.compile(r"^- \*\*(P-\d+)\*\* · (\w+) · ")
SECTION_RE = re.compile(r"^## (.+?)\s*$")
FINDING_RE = re.compile(r"^### ([A-Z][A-Z0-9-]*-\d+) · (\w+) · (.+?)\s*$")
STATUS_RE = re.compile(r"^- \*\*Status:\*\*\s*(.*)$")
COLLAPSED_SUFFIX_RE = re.compile(r"^(.*?) — ((?:fixed|wontfix|dup of) .*|wontfix:.*)$")
SNAPSHOT_SHA_RE = re.compile(r"\*\*Branch:\*\*.*?@ `([0-9a-f]{7,40})`")
BUILD_ENTRY_RE = re.compile(r"^### (\d{4}-\d{2}-\d{2})")
ANY_ITEM_START_RE = re.compile(r"^- \*\*(P-\d+)\*\*")
ANY_ID_RE = re.compile(r"\bP-(\d{3,})\b")
DONE_RE = re.compile(r"—\s*DONE (\d{4}-\d{2}-\d{2}) \(([^)]*)\):\s*(.*)$")
FIXED_STATUS_RE = re.compile(r"^fixed ([0-9a-f]{7,40})\b")
SHA_RE = re.compile(r"[0-9a-f]{7,40}")
BLAME_HEADER_RE = re.compile(r"^([0-9a-f]{40}) \d+ (\d+)(?: \d+)?$")
NEEDS_RE = re.compile(r"`needs:\s*([^`]+)`")
MAX_ITEM_LINES = 5  # the item line + up to 3 context lines + a progress note
ROLLUP_BEGIN = "<!-- punchlist:status:begin -->"
ROLLUP_END = "<!-- punchlist:status:end -->"


class PunchlistError(Exception):
    """A project isn't set up the way the formats require (missing file, no counter line, ...)."""


# --- config -------------------------------------------------------------------------------------


def _scalar(raw: str):
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if value in ("true", "false"):
        return value == "true"
    return value


def _strip_comment(line: str) -> str:
    # A '#' starts a comment only at line start or after whitespace, and never inside quotes.
    in_quote = None
    for index, char in enumerate(line):
        if char in "\"'" and in_quote in (None, char):
            in_quote = None if in_quote else char
        elif char == "#" and in_quote is None and (index == 0 or line[index - 1].isspace()):
            return line[:index].rstrip()
    return line.rstrip()


def parse_yaml_subset(text: str):
    """Parse the YAML subset .punchlist.yml allows: scalars, nested maps, lists of scalars or maps."""
    lines = []
    for raw in text.splitlines():
        stripped = _strip_comment(raw)
        if stripped.strip():
            lines.append((len(stripped) - len(stripped.lstrip(" ")), stripped.strip()))

    def parse_block(index: int, indent: int):
        if index < len(lines) and lines[index][1].startswith("- "):
            return parse_list(index, indent)
        return parse_map(index, indent)

    def parse_map(index: int, indent: int):
        result = {}
        while index < len(lines) and lines[index][0] == indent and not lines[index][1].startswith("- "):
            key, _, rest = lines[index][1].partition(":")
            index += 1
            if rest.strip():
                result[key.strip()] = _scalar(rest)
            elif index < len(lines) and lines[index][0] > indent:
                result[key.strip()], index = parse_block(index, lines[index][0])
            else:
                result[key.strip()] = None
        return result, index

    def parse_list(index: int, indent: int):
        result = []
        while index < len(lines) and lines[index][0] == indent and lines[index][1].startswith("- "):
            body = lines[index][1][2:].strip()
            if re.match(r"^[\w.-]+:(\s|$)", body):
                # A map item: first key on the dash line, the rest indented to align with it.
                lines[index] = (indent + 2, body)
                item, index = parse_map(index, indent + 2)
                result.append(item)
            else:
                result.append(_scalar(body))
                index += 1
        return result, index

    if not lines:
        return {}
    parsed, _ = parse_block(0, lines[0][0])
    return parsed


def load_config(root: Path) -> dict:
    config = {key: (dict(value) if isinstance(value, dict) else value) for key, value in DEFAULT_CONFIG.items()}
    path = Path(root) / ".punchlist.yml"
    loaded = parse_yaml_subset(path.read_text()) or {} if path.exists() else {}
    for key, value in loaded.items():
        if key == "budgets" and isinstance(value, dict):
            config["budgets"].update(value)
        else:
            config[key] = value
    if "base_branch" not in loaded:
        current = _git(Path(root), "symbolic-ref", "--short", "-q", "HEAD").stdout.strip()
        if current:
            config["base_branch"] = current
    return config


def find_root(start: Path) -> Path:
    """The git toplevel containing `start`; the project root everything is relative to."""
    out = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if out.returncode != 0:
        raise PunchlistError(f"not inside a git repository: {start}")
    return Path(out.stdout.strip())


def _docs(root: Path, config: dict) -> Path:
    return Path(root) / config["docs_dir"]


# --- parsing ------------------------------------------------------------------------------------


def parse_punchlist(text: str) -> dict:
    lines = text.splitlines(keepends=True)
    counter = None
    counter_line = None
    items = []
    section = None
    current = None
    for number, line in enumerate(lines):
        counter_match = COUNTER_RE.search(line)
        if counter_match and counter is None:
            counter, counter_line = int(counter_match.group(1)), number
        section_match = SECTION_RE.match(line)
        item_match = ITEM_RE.match(line)
        if section_match or item_match or not line.startswith("  "):
            if current is not None:
                current["end"] = number
                items.append(current)
                current = None
        if section_match:
            section = section_match.group(1)
        if item_match:
            current = {
                "id": item_match.group(1),
                "priority": item_match.group(2),
                "section": section,
                "start": number,
                "end": None,
            }
    if current is not None:
        current["end"] = len(lines)
        items.append(current)
    # An item's span ends at its last non-blank line.
    for item in items:
        while item["end"] > item["start"] + 1 and not lines[item["end"] - 1].strip():
            item["end"] -= 1
        item["needs"] = [kind.strip() for kind in NEEDS_RE.findall("".join(lines[item["start"] : item["end"]]))]
    return {"counter": counter, "counter_line": counter_line, "items": items, "lines": lines}


def parse_done_ids(text: str) -> set:
    return {match.group(1) for match in (ITEM_RE.match(line) for line in text.splitlines()) if match}


def _next_up_lines(state_text: str) -> list:
    """(0-based line number, line) for each line of STATE's `## Next up` section, heading excluded."""
    lines = state_text.splitlines()
    heading = next((n for n, line in enumerate(lines) if line.startswith("## Next up")), None)
    if heading is None:
        return []
    end = next((n for n in range(heading + 1, len(lines)) if lines[n].startswith("## ")), len(lines))
    return [(number, lines[number]) for number in range(heading + 1, end)]


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


def _status_is_closed(status: str) -> bool | None:
    """True closed, False open, None if the value isn't in the status vocabulary."""
    if status == "open" or status.startswith("open ") or status.startswith("needs-ruling:"):
        return False
    if re.match(r"^fixed [0-9a-f]{7,40}\b", status) or status.startswith("wontfix:") or re.match(r"^dup of [A-Z][A-Z0-9-]*-\d+", status):
        return True
    return None


def parse_findings(text: str) -> list:
    lines = text.splitlines(keepends=True)
    findings = []
    current = None
    for number, line in enumerate(lines):
        heading = FINDING_RE.match(line.rstrip("\n"))
        if heading or line.startswith("## ") or line.startswith("### "):
            if current is not None:
                current["end"] = number
                findings.append(current)
                current = None
        if heading:
            title = heading.group(3)
            collapsed = COLLAPSED_SUFFIX_RE.match(title)
            current = {
                "id": heading.group(1),
                "severity": heading.group(2),
                "title": collapsed.group(1) if collapsed else title,
                "status": collapsed.group(2) if collapsed else None,
                "collapsed": bool(collapsed),
                "start": number,
                "end": None,
                "status_line": None,
            }
            continue
        if current is not None and current["status"] is None:
            status_match = STATUS_RE.match(line.rstrip("\n"))
            if status_match:
                current["status"] = status_match.group(1).strip()
                current["status_line"] = number
    if current is not None:
        current["end"] = len(lines)
        findings.append(current)
    for finding in findings:
        while finding["end"] > finding["start"] + 1 and not lines[finding["end"] - 1].strip():
            finding["end"] -= 1
        verdict = _status_is_closed(finding["status"] or "")
        finding["valid_status"] = verdict is not None
        finding["closed"] = bool(verdict)
    return findings


def _finding_files(root: Path, config: dict) -> list:
    review = _docs(root, config) / "code-review"
    if not review.is_dir():
        return []
    return sorted(path for path in review.glob("*.md") if path.name != "README.md")


# --- status -------------------------------------------------------------------------------------


def status(root: Path) -> dict:
    root = Path(root)
    config = load_config(root)
    docs = _docs(root, config)
    punchlist_path = docs / "PUNCHLIST.md"
    report = {"punchlist": {"open": 0, "done": 0, "by_priority": {p: 0 for p in PRIORITIES}, "by_section": {}}, "findings": {"open": 0, "closed": 0, "files": []}}
    if punchlist_path.exists():
        parsed = parse_punchlist(punchlist_path.read_text())
        for item in parsed["items"]:
            report["punchlist"]["open"] += 1
            report["punchlist"]["by_priority"][item["priority"]] = report["punchlist"]["by_priority"].get(item["priority"], 0) + 1
            report["punchlist"]["by_section"][item["section"]] = report["punchlist"]["by_section"].get(item["section"], 0) + 1
        report["punchlist"]["next_id"] = f"P-{parsed['counter']:03d}" if parsed["counter"] is not None else None
    done_path = docs / "history" / "punchlist-done.md"
    if done_path.exists():
        report["punchlist"]["done"] = len(parse_done_ids(done_path.read_text()))
    for path in _finding_files(root, config):
        findings = parse_findings(path.read_text())
        open_by_severity = {s: 0 for s in SEVERITIES}
        for finding in findings:
            if not finding["closed"]:
                open_by_severity[finding["severity"]] = open_by_severity.get(finding["severity"], 0) + 1
        opened = sum(1 for f in findings if not f["closed"])
        report["findings"]["files"].append({"file": path.name, "open": opened, "closed": len(findings) - opened, "open_by_severity": open_by_severity})
        report["findings"]["open"] += opened
        report["findings"]["closed"] += len(findings) - opened
    return report


def render_rollup(report: dict) -> str:
    header = "| File | Open | Closed | " + " | ".join(s.capitalize() for s in SEVERITIES) + " |"
    rows = [header, "|" + "---|" * (3 + len(SEVERITIES))]
    totals = {s: 0 for s in SEVERITIES}
    for entry in report["findings"]["files"]:
        cells = [entry["file"], str(entry["open"]), str(entry["closed"])]
        for severity in SEVERITIES:
            count = entry["open_by_severity"].get(severity, 0)
            totals[severity] += count
            cells.append(str(count))
        rows.append("| " + " | ".join(cells) + " |")
    total_cells = ["**Total**", f"**{report['findings']['open']}**", f"**{report['findings']['closed']}**"] + [f"**{totals[s]}**" for s in SEVERITIES]
    rows.append("| " + " | ".join(total_cells) + " |")
    note = "_Generated by `punchlist status --write`. Severity columns count **open** findings. Do not edit by hand._"
    return note + "\n\n" + "\n".join(rows) + "\n"


def write_rollup(root: Path) -> bool:
    root = Path(root)
    config = load_config(root)
    readme = _docs(root, config) / "code-review" / "README.md"
    if not readme.exists():
        return False
    text = readme.read_text()
    begin, end = text.find(ROLLUP_BEGIN), text.find(ROLLUP_END)
    if begin == -1 or end == -1 or end < begin:
        raise PunchlistError(f"{readme}: missing {ROLLUP_BEGIN} / {ROLLUP_END} markers")
    updated = text[: begin + len(ROLLUP_BEGIN)] + "\n" + render_rollup(status(root)) + text[end:]
    if updated != text:
        readme.write_text(updated)
    return updated != text


# --- next-id ------------------------------------------------------------------------------------


def next_id(root: Path, bump: bool = False) -> str:
    root = Path(root)
    path = _docs(root, load_config(root)) / "PUNCHLIST.md"
    parsed = parse_punchlist(path.read_text())
    if parsed["counter"] is None:
        raise PunchlistError(f"{path}: no 'Next free ID: **P-###**' counter line")
    used = []
    for source in (path, path.parent / "history" / "punchlist-done.md", path.parent / "history" / "parked.md"):
        if source.exists():
            # Any line that starts like an item counts, even a malformed one, so an ID is never reissued.
            used += [int(m.group(1)[2:]) for m in map(ANY_ITEM_START_RE.match, source.read_text().splitlines()) if m]
    number = max([parsed["counter"], *[u + 1 for u in used]])
    if bump:
        lines = parsed["lines"]
        index = parsed["counter_line"]
        lines[index] = COUNTER_RE.sub(f"Next free ID: **P-{number + 1:03d}**", lines[index], count=1)
        path.write_text("".join(lines))
    return f"P-{number:03d}"


# --- queue --------------------------------------------------------------------------------------


def queue(root: Path, age_days: Callable | None = None) -> dict:
    """What to work next, what waits on the owner, and what's due for triage. Writes nothing."""
    root = Path(root)
    config = load_config(root)
    docs = _docs(root, config)
    age_days = age_days or blame_ages(root)
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


# --- recent -------------------------------------------------------------------------------------


def _commit_times(root: Path, shas: list) -> dict:
    """{sha as written: (unix time, YYYY-MM-DD)} for each sha that names a commit in this repo."""
    candidates = sorted({sha for sha in shas if sha and SHA_RE.fullmatch(sha)})
    if not candidates:
        return {}
    # Two git calls in total, however many units: resolve every sha at once, then date them at once.
    check = subprocess.run(
        ["git", "-C", str(root), "cat-file", "--batch-check=%(objectname) %(objecttype)"],
        input="".join(f"{sha}\n" for sha in candidates),
        capture_output=True,
        text=True,
    )
    full_by_sha = {}
    for sha, line in zip(candidates, check.stdout.splitlines()):
        parts = line.split()
        if len(parts) == 2 and parts[1] == "commit":
            full_by_sha[sha] = parts[0]
    if not full_by_sha:
        return {}
    shown = _git(root, "show", "-s", "--format=%H %ct %cs", *full_by_sha.values())
    times_by_full = {}
    for line in shown.stdout.splitlines():
        full, timestamp, date = line.split()
        times_by_full[full] = (int(timestamp), date)
    return {sha: times_by_full[full] for sha, full in full_by_sha.items() if full in times_by_full}


def recent(root: Path, limit: int = 5) -> list:
    """The last `limit` finished units (done P-items and fixed findings), newest first. Writes nothing."""
    root = Path(root)
    config = load_config(root)
    docs = _docs(root, config)
    units = []

    done_path = docs / "history" / "punchlist-done.md"
    if done_path.exists():
        parsed = parse_punchlist(done_path.read_text())
        for item in parsed["items"]:
            text = _item_text(parsed["lines"], item)
            done = DONE_RE.search(text)
            if not done:
                continue  # DROPPED items and pre-format entries aren't built work
            written = done.group(2).strip()
            units.append({
                "id": item["id"],
                "kind": "item",
                "closed": done.group(1),
                "sha": written if SHA_RE.fullmatch(written) else None,
                "section": item["section"],
                "text": text[: done.start()].strip(),
                "note": done.group(3).strip(),
            })

    for path in _finding_files(root, config):
        for finding in parse_findings(path.read_text()):
            fixed = FIXED_STATUS_RE.match(finding["status"] or "")
            if not fixed:
                continue
            units.append({
                "id": finding["id"],
                "kind": "finding",
                "closed": None,
                "sha": fixed.group(1),
                "section": path.name,
                "text": finding["title"],
                "note": None,
            })

    times = _commit_times(root, [unit["sha"] for unit in units])
    for unit in units:
        if unit["closed"] is None and unit["sha"] in times:
            unit["closed"] = times[unit["sha"]][1]

    def newest_first(unit: dict) -> tuple:
        # The closing date decides; the commit's time breaks ties within a day. Undated units sort last.
        timestamp, _date = times.get(unit["sha"], (0, None))
        return (unit["closed"] or "", timestamp)

    units.sort(key=newest_first, reverse=True)
    return units[:limit]


# --- git helpers --------------------------------------------------------------------------------


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


def _blame_line_times(root: Path, path: Path) -> dict:
    """{0-based line number: author time} for every line of `path`, from a single `git blame`."""
    out = _git(root, "blame", "--porcelain", "--", str(path))
    if out.returncode != 0:
        return {}
    time_by_sha = {}
    sha_by_line = {}
    current_sha = None
    for line in out.stdout.splitlines():
        header = BLAME_HEADER_RE.match(line)
        if header:
            current_sha = header.group(1)
            sha_by_line[int(header.group(2)) - 1] = current_sha
        elif line.startswith("author-time ") and current_sha:
            # Porcelain prints a commit's headers only the first time the commit appears.
            time_by_sha[current_sha] = int(line.split()[1])
    return {number: time_by_sha[sha] for number, sha in sha_by_line.items() if sha in time_by_sha}


def blame_ages(root: Path, today: _dt.date | None = None) -> Callable:
    """An age_days(path, line) that blames each file once and answers every line from that.

    Days since the given (0-based) line last changed. Uncommitted lines are age 0.
    """
    today = today or _dt.date.today()
    times_by_path = {}

    def age_days(path: Path, line_number: int) -> int:
        if path not in times_by_path:
            times_by_path[path] = _blame_line_times(root, path)
        timestamp = times_by_path[path].get(line_number)
        if timestamp is None:
            return 0
        changed = _dt.datetime.fromtimestamp(timestamp, tz=_dt.timezone.utc).date()
        return (today - changed).days

    return age_days


def _item_age_days(age_days: Callable, path: Path, item: dict) -> int:
    """Days since any line of the item last changed, so a fresh note or ruling makes the item fresh."""
    return min(age_days(path, line) for line in range(item["start"], item["end"]))


# --- lint ---------------------------------------------------------------------------------------


def lint(root: Path, age_days: Callable | None = None) -> list:
    """Return (level, path, line, message) tuples. line is 1-based or 0 when not line-specific."""
    root = Path(root)
    config = load_config(root)
    budgets = config["budgets"]
    docs = _docs(root, config)
    age_days = age_days or blame_ages(root)
    found = []

    def add(level, path, line, message):
        found.append((level, str(Path(path).relative_to(root)) if Path(path).is_absolute() else str(path), line, message))

    state = docs / "STATE.md"
    punchlist = docs / "PUNCHLIST.md"
    for required in (state, punchlist):
        if not required.exists():
            add("ERROR", required, 0, "required file is missing (run /punchlist:setup)")

    if state.exists():
        text = state.read_text()
        if len(text.splitlines()) > budgets["state_lines"]:
            add("ERROR", state, 0, f"STATE.md is {len(text.splitlines())} lines; budget {budgets['state_lines']} — move backlog/narrative out")
        sha_match = SNAPSHOT_SHA_RE.search(text)
        if not sha_match:
            add("ERROR", state, 0, "snapshot has no '**Branch:** `<branch>` @ `<sha>`' line")
        else:
            sha = sha_match.group(1)
            if _git(root, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}").returncode != 0:
                add("ERROR", state, 0, f"snapshot SHA {sha} is not a commit in this repo")
            else:
                # Bookkeeping never stales the snapshot: the docs tree, the config, and CLAUDE.md files.
                excludes = [f":(exclude){config['docs_dir']}", ":(exclude).punchlist.yml", ":(exclude,glob)**/CLAUDE.md"]
                later = _git(root, "log", "--format=%h", f"{sha}..HEAD", "--", ".", *excludes).stdout.split()
                if later:
                    add("ERROR", state, 0, f"stale snapshot: {len(later)} code commit(s) after {sha} (latest {later[0]}) — refresh the Snapshot")

    open_ids = {}
    done_ids = set()
    if punchlist.exists():
        parsed = parse_punchlist(punchlist.read_text())
        if len(parsed["lines"]) > budgets["punchlist_lines"]:
            add("ERROR", punchlist, 0, f"PUNCHLIST.md is {len(parsed['lines'])} lines; budget {budgets['punchlist_lines']} — run `punchlist compact` or park `later` items")
        if parsed["counter"] is None:
            add("ERROR", punchlist, 0, "no 'Next free ID: **P-###**' counter line")
        for item in parsed["items"]:
            if item["id"] in open_ids:
                add("ERROR", punchlist, item["start"] + 1, f"duplicate ID {item['id']}")
            open_ids[item["id"]] = item
            for kind in item["needs"]:
                if kind not in NEEDS_KINDS:
                    add("ERROR", punchlist, item["start"] + 1, f"{item['id']}: unknown `needs:` kind '{kind}' — use one of {', '.join(NEEDS_KINDS)}")
            if len(item["needs"]) > 1:
                add("ERROR", punchlist, item["start"] + 1, f"{item['id']} has {len(item['needs'])} `needs:` markers — keep one")
            if item["priority"] not in PRIORITIES:
                add("ERROR", punchlist, item["start"] + 1, f"{item['id']}: priority '{item['priority']}' is not now/next/later")
            elif item["priority"] == "later":
                age = _item_age_days(age_days, punchlist, item)
                if age > budgets["stale_later_days"]:
                    add("WARN", punchlist, item["start"] + 1, f"{item['id']} is a stale `later` item ({age} days unchanged) — park it with `punchlist compact`")
        done_path = docs / "history" / "punchlist-done.md"
        done_ids = parse_done_ids(done_path.read_text()) if done_path.exists() else set()
        for duplicate in sorted(set(open_ids) & done_ids):
            add("ERROR", punchlist, open_ids[duplicate]["start"] + 1, f"{duplicate} is both open and done — remove it from one file")
        if parsed["counter"] is not None:
            highest = max([int(i[2:]) for i in [*open_ids, *done_ids]] or [0])
            if parsed["counter"] <= highest:
                add("ERROR", punchlist, parsed["counter_line"] + 1, f"counter P-{parsed['counter']:03d} is not above the highest used ID P-{highest:03d}")

        for number, line in enumerate(parsed["lines"]):
            start = ANY_ITEM_START_RE.match(line)
            if start and not ITEM_RE.match(line):
                add("ERROR", punchlist, number + 1, f"{start.group(1)}: malformed item line — expected '- **P-###** · now|next|later · text'")
        for item in parsed["items"]:
            if item["end"] - item["start"] > MAX_ITEM_LINES:
                add("WARN", punchlist, item["start"] + 1, f"{item['id']} is {item['end'] - item['start']} lines; keep items to ≤ {MAX_ITEM_LINES} and link out")

    if state.exists() and punchlist.exists():
        state_text = state.read_text()
        for number, line in enumerate(state_text.splitlines()):
            if line.startswith("**Waiting on"):
                add("WARN", state, number + 1, "legacy 'Waiting on' line — tag those items `needs: decision|action` in PUNCHLIST and delete the line")
        for number, line in _next_up_lines(state_text):
            if line.startswith("**Waiting on"):
                continue
            matches = list(ANY_ID_RE.finditer(line))
            leading_id = f"P-{matches[0].group(1)}" if matches else None
            for match in matches:
                item_id = f"P-{match.group(1)}"
                if item_id in done_ids and item_id not in open_ids:
                    add("ERROR", state, number + 1, f"Next up lists {item_id}, which is done — refresh Next up")
                elif item_id not in open_ids:
                    add("WARN", state, number + 1, f"Next up lists {item_id}, which isn't an open PUNCHLIST item")
                elif item_id != leading_id:
                    continue
                elif open_ids[item_id]["priority"] == "later":
                    add("WARN", state, number + 1, f"Next up lists {item_id}, a `later` item — promote it or remove it from Next up")
                elif open_ids[item_id]["needs"]:
                    add("WARN", state, number + 1, f"Next up lists {item_id}, which needs the owner (`needs: {open_ids[item_id]['needs'][0]}`) — sessions will skip it")

    if state.exists():
        snapshot = SNAPSHOT_SHA_RE.search(state.read_text())
        claims_clean = bool(snapshot) and ", clean" in state.read_text()[snapshot.start(): snapshot.end() + 20]
        # Uncommitted bookkeeping (docs, config, CLAUDE.md) is normal mid-handoff; only code counts.
        dirty = _git(root, "status", "--porcelain", "--untracked-files=no", "--", ".", f":(exclude){config['docs_dir']}", ":(exclude).punchlist.yml", ":(exclude,glob)**/CLAUDE.md").stdout.strip()
        if claims_clean and dirty:
            add("WARN", state, 0, "snapshot says 'clean' but tracked files have uncommitted changes — say what's uncommitted in In flight")

    build_log = docs / "history" / "build-log.md"
    if build_log.exists():
        lines = build_log.read_text().splitlines()
        # Entries older than build_log_since predate the budget (adopted mid-project) and are exempt.
        since = str(config.get("build_log_since") or "")
        starts = [n for n, line in enumerate(lines) if BUILD_ENTRY_RE.match(line)]
        for position, start in enumerate(starts):
            end = starts[position + 1] if position + 1 < len(starts) else len(lines)
            while end > start and not lines[end - 1].strip():
                end -= 1
            entry_date = BUILD_ENTRY_RE.match(lines[start]).group(1)
            if entry_date >= since and end - start > budgets["build_log_entry_lines"]:
                add("WARN", build_log, start + 1, f"build-log entry is {end - start} lines; budget {budgets['build_log_entry_lines']}")

    for path in _finding_files(root, config):
        for finding in parse_findings(path.read_text()):
            line = (finding["status_line"] if finding["status_line"] is not None else finding["start"]) + 1
            if finding["status"] is None:
                add("ERROR", path, line, f"{finding['id']}: no Status line")
            elif not finding["valid_status"]:
                add("ERROR", path, line, f"{finding['id']}: status '{finding['status']}' is not open/needs-ruling:/fixed <sha>/wontfix:/dup of <ID>")
            if finding["severity"] not in SEVERITIES:
                add("ERROR", path, finding["start"] + 1, f"{finding['id']}: severity '{finding['severity']}' is not one of {', '.join(SEVERITIES)}")
    return found


# --- compact ------------------------------------------------------------------------------------


def _append_under_heading(text: str, heading: str, block: str) -> str:
    """Append `block` at the end of the `## heading` section, creating the section at EOF if needed."""
    lines = text.splitlines(keepends=True)
    target = f"## {heading}"
    start = next((n for n, line in enumerate(lines) if line.rstrip() == target), None)
    if start is None:
        prefix = text if text.endswith("\n") or not text else text + "\n"
        return prefix + f"\n{target}\n\n{block}"
    end = next((n for n in range(start + 1, len(lines)) if lines[n].startswith("## ")), len(lines))
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    return "".join(lines[:end]) + block + "".join(lines[end:])


PARKED_HEADER = "# PUNCHLIST — parked\n\nStale `later` items moved out of PUNCHLIST by `punchlist compact`. Not rejected — move one back\n(keeping its ID) to revive it.\n"


def compact(root: Path, age_days: Callable | None = None, today: str | None = None) -> dict:
    """Return {relative_path: new_text} for every file compaction would change. Writes nothing."""
    root = Path(root)
    config = load_config(root)
    docs = _docs(root, config)
    age_days = age_days or blame_ages(root)
    today = today or _dt.date.today().isoformat()
    changes = {}

    for path in _finding_files(root, config):
        text = path.read_text()
        lines = text.splitlines(keepends=True)
        replacements = []
        for finding in parse_findings(text):
            if finding["closed"] and not finding["collapsed"]:
                one_line = f"### {finding['id']} · {finding['severity']} · {finding['title']} — {finding['status']}\n"
                end = finding["end"]
                # Keep one blank separator after the collapsed heading.
                replacements.append((finding["start"], end, [one_line]))
        for start, end, new in reversed(replacements):
            lines[start:end] = new
        new_text = "".join(lines)
        if new_text != text:
            changes[str(path.relative_to(root))] = new_text

    punchlist = docs / "PUNCHLIST.md"
    if punchlist.exists():
        parsed = parse_punchlist(punchlist.read_text())
        stale = [i for i in parsed["items"] if i["priority"] == "later" and _item_age_days(age_days, punchlist, i) > config["budgets"]["stale_later_days"]]
        if stale:
            lines = list(parsed["lines"])
            parked_path = docs / "history" / "parked.md"
            parked = parked_path.read_text() if parked_path.exists() else PARKED_HEADER
            for item in stale:
                block = lines[item["start"] : item["end"]]
                days = _item_age_days(age_days, punchlist, item)
                block.append(f"  — PARKED {today}: stale (no change in {days} days)\n")
                parked = _append_under_heading(parked, item["section"] or "Unsorted", "".join(block))
            for item in reversed(stale):
                del lines[item["start"] : item["end"]]
            changes[str(punchlist.relative_to(root))] = "".join(lines)
            changes[str(parked_path.relative_to(root))] = parked
    return changes


def render_diff(root: Path, changes: dict) -> str:
    chunks = []
    for relative, new_text in changes.items():
        path = Path(root) / relative
        old_text = path.read_text() if path.exists() else ""
        chunks.extend(difflib.unified_diff(old_text.splitlines(keepends=True), new_text.splitlines(keepends=True), f"a/{relative}", f"b/{relative}"))
    return "".join(chunks)


def apply_changes(root: Path, changes: dict) -> None:
    for relative, new_text in changes.items():
        path = Path(root) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_text)


# --- docs inventory -----------------------------------------------------------------------------

BACKTICK_RE = re.compile(r"`([^`\s]+)`")
MD_LINK_RE = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
LINE_SUFFIX_RE = re.compile(r":\d+(?:[-,]\d+)*$")
PATHLIKE_RE = re.compile(r"^[\w.@~+-][\w./@~+-]*/(?:[\w.@~+-]+\.\w{1,6}|[\w./@~+-]*/)$")


def _managed(relative: str, docs_dir: str) -> bool:
    prefix = docs_dir.rstrip("/") + "/"
    return relative in (prefix + "STATE.md", prefix + "PUNCHLIST.md") or relative.startswith((prefix + "history/", prefix + "code-review/"))


def _references(text: str) -> list:
    """Path-like references in a doc: backticked paths (with an extension or a trailing slash) and
    relative markdown links. Globs, placeholders, URLs and commands are ignored."""
    found = []
    for token in BACKTICK_RE.findall(text):
        token = LINE_SUFFIX_RE.sub("", token.rstrip(".,;:"))
        if any(mark in token for mark in ("*", "<", ">", "{", "}", "$", "://", "…")):
            continue
        if PATHLIKE_RE.match(token):
            found.append(token)
    for target in MD_LINK_RE.findall(text):
        if "://" in target or target.startswith(("mailto:", "#")):
            continue
        found.append(target)
    return found


JS_TO_TS = {".js": (".ts", ".tsx"), ".jsx": (".tsx",), ".mjs": (".mts", ".ts")}


def docs_inventory(root: Path) -> list:
    """Every tracked markdown file with its evidence for /punchlist:tidy.

    Per file: lines, last change, managed flag, inbound links from other docs, dangling path
    references (`dangling_removed` = the subset that existed in git history once), whether history
    files mention it (`in_history`), and how many commit messages mention its name (`commit_mentions`).
    References resolve forgivingly (doc-relative, root-relative, unique path suffix, .js→.ts, gitignored)
    so dangling means genuinely missing.
    """
    root = Path(root)
    config = load_config(root)
    docs_dir = config["docs_dir"].rstrip("/")
    tracked = [p for p in _git(root, "ls-files", "-z").stdout.split("\0") if p]
    tracked_set = set(tracked)
    tracked_dirs = {str(Path(p).parent) + "/" for p in tracked}
    ever = {p for p in _git(root, "log", "--all", "--name-only", "--format=").stdout.splitlines() if p}
    ever_dirs = {str(Path(p).parent) + "/" for p in ever}
    messages = _git(root, "log", "--all", "--format=%B%x00").stdout.lower()
    excludes = list(config.get("docs_exclude") or [])
    md_paths = sorted(p for p in tracked if p.endswith(".md") and not any(fnmatch.fnmatch(p, glob) for glob in excludes))
    ignore_tags = [t for t in (config.get("docs_ignore_tags") or []) if isinstance(t, str) and t]
    history_text = "".join(
        (root / p).read_text(errors="replace")
        for p in md_paths
        if p.startswith(f"{docs_dir}/history/") or p == f"{docs_dir}/STATE.md" or "history" in Path(p).name.lower()
    )

    def matches(ref: str, files: set, dirs: set) -> str | None:
        if ref.endswith("/"):
            if ref in dirs:
                return ref
            return next((d for d in dirs if d.endswith("/" + ref)), None)
        if ref in files:
            return ref
        return next((f for f in files if f.endswith("/" + ref)), None)

    def resolve(ref: str, doc_dir: Path) -> str | None:
        """The tracked path a reference points at, or None if it genuinely doesn't exist."""
        for base in (doc_dir, root):
            candidate = (base / ref.lstrip("/")).resolve()
            if candidate.exists():
                try:
                    return str(candidate.relative_to(root.resolve())) + ("/" if candidate.is_dir() else "")
                except ValueError:
                    return "<outside>"
        clean = ref.lstrip("./").lstrip("/")
        variants = [clean]
        suffix = Path(clean).suffix
        variants += [clean[: -len(suffix)] + alt for alt in JS_TO_TS.get(suffix, ())]
        for variant in variants:
            hit = matches(variant, tracked_set, tracked_dirs)
            if hit:
                return hit
        return None

    rows, unresolved = [], []
    inbound = {path: set() for path in md_paths}
    for relative in md_paths:
        text = (root / relative).read_text(errors="replace")
        doc_dir = (root / relative).parent
        dangling = set()
        claims = text
        for tag in ignore_tags:
            claims = re.sub(rf"<{re.escape(tag)}>.*?(</{re.escape(tag)}>|\Z)", "", claims, flags=re.S)
        for ref in _references(claims):
            if ref.startswith(("~", "@")) or "@" in ref:
                continue  # home paths and package specifiers aren't repo paths
            target = resolve(ref, doc_dir)
            if target is None:
                dangling.add(ref)
                continue
            if target in inbound and target != relative:
                inbound[target].add(relative)
        unresolved.extend(dangling)
        stem = Path(relative).stem.lower()
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem)
        rows.append(
            {
                "path": relative,
                "lines": len(text.splitlines()),
                "last_changed": _git(root, "log", "-1", "--format=%cs", "--", relative).stdout.strip() or None,
                "managed": _managed(relative, docs_dir),
                "dangling": sorted(dangling),
                "in_history": Path(relative).name in history_text or (slug != stem and slug in history_text),
                "commit_mentions": messages.count(stem) if len(stem) >= 6 else 0,
            }
        )
    # Paths git ignores (build output, backups) exist by design. A doc usually writes them relative to
    # the sub-app whose .gitignore ignores them, so also test each ref under every directory holding a
    # tracked .gitignore. One batch call.
    ignored = set()
    if unresolved:
        ignore_dirs = sorted({str(Path(p).parent) for p in tracked if Path(p).name == ".gitignore"} - {"."})
        candidates = {}
        for ref in set(unresolved):
            clean = ref.lstrip("./").lstrip("/")
            for candidate in [clean, *(f"{d}/{clean}" for d in ignore_dirs)]:
                candidates.setdefault(candidate, set()).add(ref)
        out = subprocess.run(["git", "-C", str(root), "check-ignore", "--no-index", "--stdin"], input="\n".join(sorted(candidates)), capture_output=True, text=True).stdout
        for hit in out.splitlines():
            ignored |= candidates.get(hit.strip(), set())
    for row in rows:
        row["dangling"] = [ref for ref in row["dangling"] if ref not in ignored]
        row["dangling_removed"] = [ref for ref in row["dangling"] if matches(ref.lstrip("./").lstrip("/"), ever, ever_dirs)]
        row["inbound"] = len(inbound[row["path"]])
    return rows
