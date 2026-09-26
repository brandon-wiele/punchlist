"""Behavioral tests for the punchlist CLI core. Run: python3 -m unittest discover -s tests"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins" / "punchlist" / "lib"))

import punchlist_core as core  # noqa: E402

BIN = Path(__file__).resolve().parents[1] / "plugins" / "punchlist" / "bin" / "punchlist"

PUNCHLIST = textwrap.dedent(
    """\
    # PUNCHLIST

    - **ID** — `P-###`, never reused, never renumbered. Next free ID: **P-005**.

    ## Bugs

    - **P-001** · now · Login email never sends.

    ## Features

    - **P-002** · next · Export to CSV.
      Continuation line.
    - **P-003** · later · Dark mode.
    """
)

DONE = textwrap.dedent(
    """\
    # PUNCHLIST — done

    ## Bugs

    [x] An old pre-ID item.
    - **P-004** · now · Crash on save. — DONE 2026-09-01 (abc1234): fixed.
    """
)

FINDINGS = textwrap.dedent(
    """\
    # Code review — API

    ## Findings

    ### API-001 · high · Cancel never propagates
    - **Where:** `a.ts:1`
    - **Status:** open
    - **Problem:** p

    ### API-002 · medium · Leaky sessions
    - **Where:** `b.ts:2`
    - **Status:** fixed abc1234
    - **Problem:** p

    ### API-003 · low · Old thing — wontfix: by design

    ### API-004 · nit · Naming
    - **Status:** open — RULED: keep
    - **Problem:** p

    ## Not reviewed / follow-up areas

    - stuff
    """
)

STATE_TMPL = textwrap.dedent(
    """\
    # STATE

    ## Snapshot — 2026-09-23

    - **Branch:** `main` @ `{sha}`, clean.

    ## Next up

    1. P-001
    """
)

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


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


class ProjectFixture:
    """A throwaway git repo with a docs tree in the documented formats."""

    def __init__(self, punchlist=PUNCHLIST, done=DONE, findings=FINDINGS, config=None):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "T")
        (self.root / "src").mkdir()
        (self.root / "src" / "app.txt").write_text("v1\n")
        docs = self.root / "docs"
        (docs / "history").mkdir(parents=True)
        (docs / "code-review").mkdir()
        (docs / "PUNCHLIST.md").write_text(punchlist)
        (docs / "history" / "punchlist-done.md").write_text(done)
        (docs / "code-review" / "01-api.md").write_text(findings)
        (docs / "code-review" / "README.md").write_text(
            "# Review\n\n<!-- punchlist:status:begin -->\nstale\n<!-- punchlist:status:end -->\n\n## Fix first\n"
        )
        if config is not None:
            (self.root / ".punchlist.yml").write_text(config)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "code")
        self.code_sha = git(self.root, "rev-parse", "--short", "HEAD")
        (docs / "STATE.md").write_text(STATE_TMPL.format(sha=self.code_sha))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "docs")

    def close(self):
        self.tmp.cleanup()


class YamlSubsetTest(unittest.TestCase):
    def test_parses_scalars_maps_and_lists_of_maps(self):
        parsed = core.parse_yaml_subset(
            textwrap.dedent(
                """\
                docs_dir: documentation   # trailing comment
                push: never
                gates:
                  - run: just check
                  - run: just admin-check
                    when: apps/admin/**
                budgets:
                  state_lines: 100
                tags:
                  - a
                  - "b c"
                """
            )
        )
        self.assertEqual(parsed["docs_dir"], "documentation")
        self.assertEqual(parsed["gates"][1], {"run": "just admin-check", "when": "apps/admin/**"})
        self.assertEqual(parsed["budgets"]["state_lines"], 100)
        self.assertEqual(parsed["tags"], ["a", "b c"])

    def test_config_defaults_fill_missing_keys(self):
        fixture = ProjectFixture(config="docs_dir: docs\nbudgets:\n  state_lines: 50\n")
        try:
            config = core.load_config(fixture.root)
            self.assertEqual(config["budgets"]["state_lines"], 50)
            self.assertEqual(config["budgets"]["punchlist_lines"], 250)
            self.assertEqual(config["push"], "never")
            self.assertEqual(config["budgets"]["triage_after_days"], 30)
        finally:
            fixture.close()


class ParsingTest(unittest.TestCase):
    def test_punchlist_items_carry_section_priority_and_span(self):
        parsed = core.parse_punchlist(PUNCHLIST)
        self.assertEqual(parsed["counter"], 5)
        ids = [(item["id"], item["priority"], item["section"]) for item in parsed["items"]]
        self.assertEqual(ids, [("P-001", "now", "Bugs"), ("P-002", "next", "Features"), ("P-003", "later", "Features")])
        export = parsed["items"][1]
        self.assertEqual(export["end"] - export["start"], 2)  # item line + continuation

    def test_done_ids_ignore_pre_id_entries(self):
        self.assertEqual(core.parse_done_ids(DONE), {"P-004"})

    def test_findings_status_open_closed_and_collapsed(self):
        findings = {f["id"]: f for f in core.parse_findings(FINDINGS)}
        self.assertFalse(findings["API-001"]["closed"])
        self.assertTrue(findings["API-002"]["closed"])
        self.assertTrue(findings["API-003"]["closed"])
        self.assertTrue(findings["API-003"]["collapsed"])
        self.assertFalse(findings["API-004"]["closed"])  # "open — RULED" is still open

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


class StatusTest(unittest.TestCase):
    def test_counts_and_write_rollup_between_markers(self):
        fixture = ProjectFixture()
        try:
            report = core.status(fixture.root)
            self.assertEqual(report["punchlist"]["open"], 3)
            self.assertEqual(report["punchlist"]["done"], 1)
            self.assertEqual(report["findings"]["open"], 2)
            self.assertEqual(report["findings"]["closed"], 2)
            core.write_rollup(fixture.root)
            readme = (fixture.root / "docs" / "code-review" / "README.md").read_text()
            self.assertNotIn("stale", readme)
            self.assertIn("| 01-api.md | 2 | 2 |", readme)
            self.assertIn("## Fix first", readme)  # content outside the markers untouched
        finally:
            fixture.close()


class NextIdTest(unittest.TestCase):
    def test_bump_increments_counter_in_place(self):
        fixture = ProjectFixture()
        try:
            self.assertEqual(core.next_id(fixture.root, bump=True), "P-005")
            self.assertIn("Next free ID: **P-006**", (fixture.root / "docs" / "PUNCHLIST.md").read_text())
        finally:
            fixture.close()


class LintTest(unittest.TestCase):
    def messages(self, root):
        return [(level, message) for level, _path, _line, message in core.lint(root, age_days=lambda *_: 0)]

    def test_clean_fixture_has_no_errors(self):
        fixture = ProjectFixture()
        try:
            errors = [m for level, m in self.messages(fixture.root) if level == "ERROR"]
            self.assertEqual(errors, [])
        finally:
            fixture.close()

    def test_stale_snapshot_after_a_code_commit(self):
        fixture = ProjectFixture()
        try:
            (fixture.root / "src" / "app.txt").write_text("v2\n")
            git(fixture.root, "commit", "-qam", "more code")
            self.assertTrue(any("snapshot" in m for level, m in self.messages(fixture.root) if level == "ERROR"))
        finally:
            fixture.close()

    def test_claude_md_and_config_edits_do_not_stale_the_snapshot(self):
        fixture = ProjectFixture()
        try:
            (fixture.root / "CLAUDE.md").write_text("# rules\n")
            (fixture.root / ".punchlist.yml").write_text("owner: X\n")
            git(fixture.root, "add", "-A")
            git(fixture.root, "commit", "-qm", "bookkeeping only")
            self.assertFalse(any("snapshot" in m for level, m in self.messages(fixture.root) if level == "ERROR"))
        finally:
            fixture.close()

    def test_id_both_open_and_done_and_bad_counter_and_bad_status(self):
        punchlist = PUNCHLIST.replace("P-005", "P-002") + "- **P-004** · next · Reopened by mistake.\n"
        findings = FINDINGS.replace("- **Status:** fixed abc1234", "- **Status:** done-ish")
        fixture = ProjectFixture(punchlist=punchlist, findings=findings)
        try:
            errors = [m for level, m in self.messages(fixture.root) if level == "ERROR"]
            self.assertTrue(any("P-004" in m and "done" in m for m in errors))
            self.assertTrue(any("counter" in m for m in errors))
            self.assertTrue(any("API-002" in m and "status" in m.lower() for m in errors))
        finally:
            fixture.close()

    def test_budget_and_stale_later_warnings(self):
        fixture = ProjectFixture(config="budgets:\n  punchlist_lines: 5\n  stale_later_days: 30\n")
        try:
            found = core.lint(fixture.root, age_days=lambda *_: 90)
            self.assertTrue(any(level == "ERROR" and "PUNCHLIST" in path for level, path, _l, _m in found))
            self.assertTrue(any(level == "WARN" and "P-003" in m for level, _p, _l, m in found))
            self.assertFalse(any("P-002" in m for _lv, _p, _l, m in found if "stale" in m))  # only `later` items age out
        finally:
            fixture.close()


class LintConsistencyTest(unittest.TestCase):
    def lint_messages(self, fixture):
        return [(level, m) for level, _p, _l, m in core.lint(fixture.root, age_days=lambda *_: 0)]

    def test_malformed_item_is_an_error_and_its_id_is_never_reissued(self):
        punchlist = PUNCHLIST.replace("P-005", "P-003") + "- **P-009** - next - dash instead of middle dot\n"
        fixture = ProjectFixture(punchlist=punchlist)
        try:
            self.assertTrue(any(level == "ERROR" and "P-009" in m and "malformed" in m for level, m in self.lint_messages(fixture)))
            self.assertEqual(core.next_id(fixture.root), "P-010")
        finally:
            fixture.close()

    def test_next_up_listing_a_closed_item(self):
        fixture = ProjectFixture()
        try:
            state = fixture.root / "docs" / "STATE.md"
            state.write_text(state.read_text().replace("1. P-001", "1. P-004 — already done\n2. P-099 — unknown"))
            messages = self.lint_messages(fixture)
            self.assertTrue(any(level == "ERROR" and "P-004" in m and "Next up" in m for level, m in messages))
            self.assertTrue(any(level == "WARN" and "P-099" in m for level, m in messages))
        finally:
            fixture.close()

    def test_snapshot_claims_clean_but_tree_is_dirty(self):
        fixture = ProjectFixture()
        try:
            (fixture.root / "src" / "app.txt").write_text("uncommitted\n")
            self.assertTrue(any(level == "WARN" and "clean" in m for level, m in self.lint_messages(fixture)))
        finally:
            fixture.close()

    def test_uncommitted_bookkeeping_does_not_contradict_clean(self):
        fixture = ProjectFixture()
        try:
            punchlist = fixture.root / "docs" / "PUNCHLIST.md"
            punchlist.write_text(punchlist.read_text() + "  more context\n")
            self.assertFalse(any("clean" in m for _level, m in self.lint_messages(fixture)))
        finally:
            fixture.close()

    def test_overlong_item_warns(self):
        long_item = "- **P-006** · next · Long.\n" + "".join(f"  context {n}\n" for n in range(6))
        fixture = ProjectFixture(punchlist=PUNCHLIST.replace("P-005", "P-007") + long_item)
        try:
            self.assertTrue(any(level == "WARN" and "P-006" in m and "lines" in m for level, m in self.lint_messages(fixture)))
        finally:
            fixture.close()


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

    def test_next_up_needs_warn_checks_only_the_leading_id(self):
        # P-005 is only mentioned in passing on this line; P-002 (the leading ID) has no `needs:`.
        fixture = ProjectFixture(punchlist=NEEDS_PUNCHLIST)
        try:
            state = fixture.root / "docs" / "STATE.md"
            state.write_text(state.read_text().replace("1. P-001", "1. P-002 — after P-005 lands"))
            warnings = [m for level, m in self.lint_messages(fixture) if level == "WARN"]
            self.assertFalse(any("P-005" in m for m in warnings))
        finally:
            fixture.close()

    def test_next_up_naming_a_later_item_warns(self):
        fixture = ProjectFixture(punchlist=NEEDS_PUNCHLIST)
        try:
            state = fixture.root / "docs" / "STATE.md"
            state.write_text(state.read_text().replace("1. P-001", "1. P-003"))
            warnings = [m for level, m in self.lint_messages(fixture) if level == "WARN"]
            self.assertTrue(any("P-003" in m and "later" in m for m in warnings))
        finally:
            fixture.close()


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

    def test_needs_marker_without_a_space_parses_and_is_not_workable(self):
        punchlist = NEEDS_PUNCHLIST.replace("`needs: action`", "`needs:action`")
        fixture = ProjectFixture(punchlist=punchlist)
        try:
            items = {item["id"]: item for item in core.parse_punchlist(punchlist)["items"]}
            self.assertEqual(items["P-006"]["needs"], ["action"])
            workable_ids = [entry["id"] for entry in core.queue(fixture.root, age_days=lambda *_: 0)["workable"]]
            self.assertNotIn("P-006", workable_ids)
        finally:
            fixture.close()

    def test_next_up_naming_a_later_item_is_not_workable(self):
        fixture = ProjectFixture()
        try:
            state = fixture.root / "docs" / "STATE.md"
            state.write_text(state.read_text().replace("1. P-001", "1. P-003"))
            workable_ids = [entry["id"] for entry in core.queue(fixture.root, age_days=lambda *_: 0)["workable"]]
            self.assertNotIn("P-003", workable_ids)
        finally:
            fixture.close()

    def test_next_up_naming_a_done_id_and_an_unknown_id_are_skipped_without_error(self):
        fixture = ProjectFixture()
        try:
            state = fixture.root / "docs" / "STATE.md"
            state.write_text(state.read_text().replace("1. P-001", "1. P-004\n2. P-099"))
            workable_ids = [entry["id"] for entry in core.queue(fixture.root, age_days=lambda *_: 0)["workable"]]
            self.assertEqual(workable_ids, ["P-001", "P-002"])
        finally:
            fixture.close()

    def test_no_state_file_workable_falls_back_to_now_then_next(self):
        fixture = ProjectFixture()
        try:
            (fixture.root / "docs" / "STATE.md").unlink()
            workable_ids = [entry["id"] for entry in core.queue(fixture.root, age_days=lambda *_: 0)["workable"]]
            self.assertEqual(workable_ids, ["P-001", "P-002"])
        finally:
            fixture.close()

    def test_no_punchlist_file_raises_punchlist_error(self):
        fixture = ProjectFixture()
        try:
            (fixture.root / "docs" / "PUNCHLIST.md").unlink()
            with self.assertRaises(core.PunchlistError):
                core.queue(fixture.root, age_days=lambda *_: 0)
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


class BuildLogBudgetTest(unittest.TestCase):
    def test_entries_before_build_log_since_are_exempt(self):
        fixture = ProjectFixture(config="build_log_since: 2026-09-01\nbudgets:\n  build_log_entry_lines: 3\n")
        try:
            long_body = "".join(f"- line {n}\n" for n in range(6))
            (fixture.root / "docs" / "history" / "build-log.md").write_text(
                "# Build log\n\n## Entries\n\n### 2026-09-10 — New — merged `abc`\n" + long_body
                + "\n### 2026-08-01 — Legacy — merged `def`\n" + long_body
            )
            warnings = [m for level, _p, _l, m in core.lint(fixture.root, age_days=lambda *_: 0) if "build-log" in m]
            self.assertEqual(len(warnings), 1)
        finally:
            fixture.close()


class DocsInventoryTest(unittest.TestCase):
    def test_inventory_flags_dangling_refs_and_counts_inbound_links(self):
        fixture = ProjectFixture()
        try:
            docs = fixture.root / "docs"
            (docs / "arch.md").write_text(
                "# Arch\n\nSee `src/app.txt` and `src/gone.ts:12` and `lib/old/` and [spec](specs/missing.md).\n"
                "Ignore `*.md`, `<docs>/x.md`, https://example.com/a/b.md and `npm run build`.\n"
            )
            (docs / "notes.md").write_text("# Notes\n\nBackground: [arch](arch.md).\n")
            git(fixture.root, "add", "-A")
            git(fixture.root, "commit", "-qm", "docs")
            rows = {row["path"]: row for row in core.docs_inventory(fixture.root)}
            arch = rows["docs/arch.md"]
            self.assertEqual(sorted(arch["dangling"]), ["lib/old/", "specs/missing.md", "src/gone.ts"])
            self.assertEqual(arch["inbound"], 1)
            self.assertEqual(rows["docs/notes.md"]["inbound"], 0)
            self.assertTrue(rows["docs/PUNCHLIST.md"]["managed"])
            self.assertFalse(arch["managed"])
            self.assertRegex(arch["last_changed"], r"^\d{4}-\d{2}-\d{2}$")
        finally:
            fixture.close()


class DocsInventorySignalsTest(unittest.TestCase):
    def test_resolution_is_forgiving_and_dangling_splits_removed_from_never(self):
        fixture = ProjectFixture()
        try:
            root = fixture.root
            (root / "apps" / "hub" / "src" / "mcp").mkdir(parents=True)
            (root / "apps" / "hub" / "src" / "mcp" / "catalog.ts").write_text("x\n")
            (root / "old").mkdir()
            (root / "old" / "thing.ts").write_text("x\n")
            (root / ".gitignore").write_text("storage/\n")
            git(root, "add", "-A")
            git(root, "commit", "-qm", "add files")
            git(root, "rm", "-q", "old/thing.ts")
            git(root, "commit", "-qm", "remove thing")
            (root / "docs" / "plan.md").write_text(
                "Uses `mcp/catalog.ts`, `apps/hub/src/mcp/catalog.js`, `storage/db-backups/`, `@anthropic-ai/sdk@0.1.0`,\n"
                "`~/notes/x.md`, `old/thing.ts` (removed) and `new/never.ts` (never existed).\n"
            )
            git(root, "add", "-A")
            git(root, "commit", "-qm", "plan")
            row = {r["path"]: r for r in core.docs_inventory(root)}["docs/plan.md"]
            self.assertEqual(row["dangling"], ["new/never.ts", "old/thing.ts"])
            self.assertEqual(row["dangling_removed"], ["old/thing.ts"])
        finally:
            fixture.close()

    def test_paths_ignored_by_a_nested_gitignore_are_not_dangling(self):
        fixture = ProjectFixture()
        try:
            root = fixture.root
            (root / "apps" / "admin").mkdir(parents=True)
            (root / "apps" / "admin" / ".gitignore").write_text("/storage/db-backups\n")
            (root / "docs" / "dr.md").write_text("Backups land in `storage/db-backups/` and `storage/other/x.sql`.\n")
            git(root, "add", "-A")
            git(root, "commit", "-qm", "dr doc")
            row = {r["path"]: r for r in core.docs_inventory(root)}["docs/dr.md"]
            self.assertEqual(row["dangling"], ["storage/other/x.sql"])
        finally:
            fixture.close()

    def test_generated_files_and_vendor_regions_are_ignored(self):
        fixture = ProjectFixture(config="docs_exclude:\n  - apps/*/AGENTS.md\ndocs_ignore_tags:\n  - vendor-rules\n")
        try:
            root = fixture.root
            (root / "apps" / "web").mkdir(parents=True)
            vendor = "<vendor-rules>\nSet it in `config/activitylog.php`.\n</vendor-rules>\n"
            (root / "apps" / "web" / "AGENTS.md").write_text("# mirror\n" + vendor)
            (root / "apps" / "web" / "CLAUDE.md").write_text("# Web\nOur code is in `web/missing.ts`.\n" + vendor)
            git(root, "add", "-A")
            git(root, "commit", "-qm", "agent docs")
            rows = {r["path"]: r for r in core.docs_inventory(root)}
            self.assertNotIn("apps/web/AGENTS.md", rows)
            self.assertEqual(rows["apps/web/CLAUDE.md"]["dangling"], ["web/missing.ts"])
        finally:
            fixture.close()

    def test_laravel_boost_block_is_ignored_by_default(self):
        fixture = ProjectFixture()
        try:
            (fixture.root / "CLAUDE.md").write_text("<laravel-boost-guidelines>\nSee `config/activitylog.php`.\n</laravel-boost-guidelines>\n")
            git(fixture.root, "add", "-A")
            git(fixture.root, "commit", "-qm", "boost")
            self.assertEqual({r["path"]: r for r in core.docs_inventory(fixture.root)}["CLAUDE.md"]["dangling"], [])
        finally:
            fixture.close()

    def test_history_links_and_commit_mentions_signal_shipped_plans(self):
        fixture = ProjectFixture()
        try:
            root = fixture.root
            plans = root / "docs" / "plans"
            plans.mkdir()
            (plans / "2026-09-01-widget-export.md").write_text("# Widget export plan\n")
            (plans / "2026-09-02-orphan-idea.md").write_text("# Orphan\n")
            (root / "docs" / "history" / "build-log.md").write_text("| 2026-09-05 | Widget export | `abc` | `plans/2026-09-01-widget-export.md` |\n")
            git(root, "add", "-A")
            git(root, "commit", "-qm", "docs: plans")
            (root / "src" / "app.txt").write_text("export\n")
            git(root, "commit", "-qam", "feat: widget export (plan 2026-09-01-widget-export)")
            rows = {r["path"]: r for r in core.docs_inventory(root)}
            shipped = rows["docs/plans/2026-09-01-widget-export.md"]
            orphan = rows["docs/plans/2026-09-02-orphan-idea.md"]
            self.assertTrue(shipped["in_history"])
            self.assertGreaterEqual(shipped["commit_mentions"], 1)
            self.assertFalse(orphan["in_history"])
            self.assertEqual(orphan["commit_mentions"], 0)
        finally:
            fixture.close()

    def test_base_branch_defaults_to_current_branch_without_config(self):
        fixture = ProjectFixture()
        try:
            git(fixture.root, "branch", "-m", "master")
            self.assertEqual(core.load_config(fixture.root)["base_branch"], "master")
        finally:
            fixture.close()


class CompactTest(unittest.TestCase):
    def test_collapses_closed_findings_and_parks_stale_later_items(self):
        fixture = ProjectFixture(config="budgets:\n  stale_later_days: 30\n")
        try:
            changes = core.compact(fixture.root, age_days=lambda *_: 90, today="2026-09-23")
            findings = changes[str(Path("docs/code-review/01-api.md"))]
            self.assertIn("### API-002 · medium · Leaky sessions — fixed abc1234\n", findings)
            self.assertNotIn("`b.ts:2`", findings)
            self.assertIn("`a.ts:1`", findings)  # open finding untouched
            self.assertIn("## Not reviewed", findings)
            punchlist = changes[str(Path("docs/PUNCHLIST.md"))]
            self.assertNotIn("P-003", punchlist)
            parked = changes[str(Path("docs/history/parked.md"))]
            self.assertIn("## Features", parked)
            self.assertIn("- **P-003** · later · Dark mode.\n  — PARKED 2026-09-23: stale", parked)
            # nothing written without apply
            self.assertIn("`b.ts:2`", (fixture.root / "docs" / "code-review" / "01-api.md").read_text())
        finally:
            fixture.close()


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


def commit_at(root, message, when):
    """Commit all tracked changes with a fixed author and committer date (ISO 8601, local time)."""
    env = dict(os.environ, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
    subprocess.run(["git", "-C", str(root), "commit", "-qam", message], check=True, capture_output=True, text=True, env=env)
    return git(root, "rev-parse", "--short", "HEAD")


class RecentTest(unittest.TestCase):
    def fixture_with_two_fixes_on_one_day(self):
        fixture = ProjectFixture()
        (fixture.root / "src" / "app.txt").write_text("v2\n")
        morning = commit_at(fixture.root, "first fix", "2026-09-20T09:00:00")
        (fixture.root / "src" / "app.txt").write_text("v3\n")
        evening = commit_at(fixture.root, "second fix", "2026-09-20T18:00:00")
        return fixture, morning, evening

    def test_done_items_come_newest_first_and_commit_time_breaks_same_day_ties(self):
        fixture, morning, evening = self.fixture_with_two_fixes_on_one_day()
        try:
            done = DONE + textwrap.dedent(
                f"""\

                ## Features

                - **P-010** · next · Morning thing.
                  — DONE 2026-09-20 ({morning}): shipped in the morning.
                - **P-011** · next · Evening thing.
                  — DONE 2026-09-20 ({evening}): shipped in the evening.
                - **P-012** · later · A task the owner did.
                  — DONE 2026-09-22 (manual): done by hand.
                - **P-013** · later · An idea we dropped.
                  — DROPPED 2026-09-23: not needed.
                """
            )
            (fixture.root / "docs" / "history" / "punchlist-done.md").write_text(done)
            units = core.recent(fixture.root, limit=10)
            # API-002's "fixed abc1234" names no commit here, so it has no date and sorts last.
            self.assertEqual([unit["id"] for unit in units], ["P-012", "P-011", "P-010", "P-004", "API-002"])
            self.assertEqual(
                units[1],
                {"id": "P-011", "kind": "item", "closed": "2026-09-20", "sha": evening, "section": "Features",
                 "text": "Evening thing.", "note": "shipped in the evening."},
            )
            self.assertIsNone(units[0]["sha"])  # done by hand: no commit
            self.assertEqual(units[3]["text"], "Crash on save.")  # an inline DONE suffix is cut from the text
        finally:
            fixture.close()

    def test_fixed_findings_are_dated_by_the_fixing_commit(self):
        fixture, _morning, evening = self.fixture_with_two_fixes_on_one_day()
        try:
            findings = fixture.root / "docs" / "code-review" / "01-api.md"
            findings.write_text(FINDINGS.replace("fixed abc1234", f"fixed {evening}"))
            units = core.recent(fixture.root, limit=10)
            self.assertEqual([unit["id"] for unit in units], ["API-002", "P-004"])  # wontfix and open findings aren't built work
            self.assertEqual(
                units[0],
                {"id": "API-002", "kind": "finding", "closed": "2026-09-20", "sha": evening, "section": "01-api.md",
                 "text": "Leaky sessions", "note": None},
            )
        finally:
            fixture.close()

    def test_limit_keeps_the_newest_and_missing_history_is_empty(self):
        fixture = ProjectFixture()
        try:
            self.assertEqual([unit["id"] for unit in core.recent(fixture.root, limit=1)], ["P-004"])
            (fixture.root / "docs" / "history" / "punchlist-done.md").unlink()
            (fixture.root / "docs" / "code-review" / "01-api.md").unlink()
            self.assertEqual(core.recent(fixture.root), [])
        finally:
            fixture.close()

    def test_cli_recent_json_and_plain(self):
        fixture = ProjectFixture()
        try:
            as_json = subprocess.run([sys.executable, str(BIN), "recent", "--json"], cwd=fixture.root, capture_output=True, text=True)
            self.assertEqual(as_json.returncode, 0, as_json.stderr)
            self.assertEqual([unit["id"] for unit in json.loads(as_json.stdout)], ["P-004", "API-002"])
            plain = subprocess.run([sys.executable, str(BIN), "recent", "--limit", "1"], cwd=fixture.root, capture_output=True, text=True)
            self.assertIn("2026-09-01 · P-004 · Crash on save.", plain.stdout)
            self.assertNotIn("API-002", plain.stdout)
        finally:
            fixture.close()


class BlameAgeTest(unittest.TestCase):
    """Ages come from real `git blame` here, not an injected function."""

    def fixture_with_old_and_new_later_items(self):
        fixture = ProjectFixture(config="budgets:\n  triage_after_days: 30\n")
        punchlist = fixture.root / "docs" / "PUNCHLIST.md"
        punchlist.write_text(punchlist.read_text() + "- **P-020** · later · An old idea.\n  With a second line.\n")
        commit_at(fixture.root, "old idea", "2026-01-01T12:00:00")
        punchlist.write_text(punchlist.read_text() + "- **P-021** · later · A fresh idea.\n")
        git(fixture.root, "commit", "-qam", "fresh idea")
        return fixture

    def count_blames(self, call):
        original = core._git
        blames = []

        def counting(root, *args):
            if args and args[0] == "blame":
                blames.append(args)
            return original(root, *args)

        core._git = counting
        try:
            return call(), len(blames)
        finally:
            core._git = original

    def test_queue_blames_each_file_once_however_many_items(self):
        fixture = self.fixture_with_old_and_new_later_items()
        try:
            result, blames = self.count_blames(lambda: core.queue(fixture.root))
            self.assertEqual(blames, 1)  # three `later` items, five lines, one blame of PUNCHLIST.md
            triage_ids = [entry["id"] for entry in result["triage"]]
            self.assertIn("P-020", triage_ids)  # committed in January: well past 30 days
            self.assertNotIn("P-021", triage_ids)  # committed just now
        finally:
            fixture.close()

    def test_lint_and_compact_blame_each_file_once(self):
        fixture = self.fixture_with_old_and_new_later_items()
        try:
            _found, lint_blames = self.count_blames(lambda: core.lint(fixture.root))
            _changes, compact_blames = self.count_blames(lambda: core.compact(fixture.root))
            self.assertEqual((lint_blames, compact_blames), (1, 1))
        finally:
            fixture.close()

    def test_an_uncommitted_edit_makes_an_item_fresh(self):
        fixture = self.fixture_with_old_and_new_later_items()
        try:
            punchlist = fixture.root / "docs" / "PUNCHLIST.md"
            punchlist.write_text(punchlist.read_text().replace("With a second line.", "With a second line, edited."))
            triage_ids = [entry["id"] for entry in core.queue(fixture.root)["triage"]]
            self.assertNotIn("P-020", triage_ids)  # an uncommitted line counts as changed today
        finally:
            fixture.close()


class CliTest(unittest.TestCase):
    def test_cli_runs_from_any_cwd_and_lint_exit_code(self):
        fixture = ProjectFixture()
        try:
            ok = subprocess.run([sys.executable, str(BIN), "lint"], cwd=fixture.root / "src", capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
            (fixture.root / "src" / "app.txt").write_text("v3\n")
            git(fixture.root, "commit", "-qam", "code after snapshot")
            bad = subprocess.run([sys.executable, str(BIN), "lint"], cwd=fixture.root, capture_output=True, text=True)
            self.assertEqual(bad.returncode, 1)
            self.assertIn("ERROR", bad.stdout)
        finally:
            fixture.close()


if __name__ == "__main__":
    unittest.main()
