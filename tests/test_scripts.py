"""
Smoke tests for the command-line tools and the files generated from the data.
Standard library only.

    python3 -m unittest discover -s tests

These run the real scripts against the real data/ files, read-only. They fail
when a tool crashes, drops a field, or when a committed file has drifted away
from the data it was generated from.
"""

import csv
import datetime
import glob
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT / "scripts"))

import generate_dashboard  # noqa: E402
import maintenance_report  # noqa: E402
import query_legislation  # noqa: E402

IN_FORCE = ("enacted", "active", "adopted")


def load_records():
    records = {}
    for path in sorted(glob.glob(str(ROOT / "data" / "*.json"))):
        with open(path, encoding="utf-8") as handle:
            records[Path(path).stem] = json.load(handle)
    return records


def run(script, *args, env_extra=None):
    env = dict(os.environ)
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True, env=env, cwd=str(ROOT), timeout=60,
    )


def text(completed):
    return completed.stdout.decode("utf-8"), completed.stderr.decode("utf-8")


class QueryTests(unittest.TestCase):
    def count(self, *args):
        done = run(SRC / "query_legislation.py", *args, "--count")
        self.assertEqual(done.returncode, 0, text(done))
        match = re.search(r"Total matching items: (\d+)", text(done)[0])
        self.assertIsNotNone(match, text(done))
        return int(match.group(1))

    def test_search_finds_a_record_by_bill_number_and_id(self):
        state = load_records()["us_state_bills"][0]
        self.assertGreaterEqual(self.count("--search", state["bill_number"]), 1)
        self.assertGreaterEqual(self.count("--search", state["id"]), 1)

    def test_jurisdiction_federal_returns_every_federal_record(self):
        federal = load_records()["us_federal_actions"]
        self.assertEqual(self.count("--jurisdiction", "federal"), len(federal))

    def test_jurisdiction_still_matches_an_issuing_body(self):
        federal = load_records()["us_federal_actions"]
        body = federal[0]["issuing_body"]
        expected = sum(1 for r in federal if body.lower() in r["issuing_body"].lower())
        self.assertGreaterEqual(self.count("--jurisdiction", body), expected)

    def test_jurisdiction_matches_a_state(self):
        states = load_records()["us_state_bills"]
        name = states[0]["state"]
        expected = sum(1 for r in states if name.lower() in r["state"].lower())
        self.assertGreaterEqual(self.count("--jurisdiction", name), expected)

    def test_status_filter_counts_match_the_data(self):
        every = [r for records in load_records().values() for r in records]
        enacted = sum(1 for r in every if r["status"] == "enacted")
        self.assertEqual(self.count("--status", "enacted"), enacted)

    def test_survives_a_legacy_windows_console(self):
        done = run(SRC / "query_legislation.py", "--tag", "employment",
                   env_extra={"PYTHONIOENCODING": "cp1252"})
        self.assertEqual(done.returncode, 0, text(done))

    def test_in_force_matches_the_rule(self):
        today = datetime.date.today().isoformat()
        every = [r for records in load_records().values() for r in records]
        expected = sum(1 for r in every if r["status"] in ("enacted", "active", "adopted")
                       and not (r.get("effective_date") and r["effective_date"] > today))
        self.assertEqual(self.count("--in-force"), expected)

    def test_federal_records_are_found_as_the_site_names_them(self):
        federal = load_records()["us_federal_actions"]
        self.assertEqual(self.count("--search", "us federal"), len(federal))


class SearchFieldTests(unittest.TestCase):
    """Each searched field, tested with a word that appears nowhere else in the record.

    A test that searched the real data for a milestone word used to pass even
    with milestone search removed, because the same word was in the summary."""

    base = {"id": "state-900", "title": "Plain", "summary": "Nothing", "status": "enacted",
            "state": "Nowhere", "bill_number": "HB 9", "key_provisions": ["One"], "tags": ["alpha"],
            "last_verified": "2026-01-01", "_source": "us_state_bills"}

    def found(self, query, **fields):
        record = dict(self.base, **fields)
        return query_legislation.search_text([record], query) == [record]

    def test_baseline_does_not_match_the_probe_words(self):
        for word in ("zebra", "us federal", "frontier ai", "executive order"):
            self.assertFalse(self.found(word), word)

    def test_milestone_descriptions(self):
        self.assertTrue(self.found("zebra", milestones=[{"date": "2027-01-01", "description": "Zebra duties begin"}]))
        self.assertFalse(self.found("zebra", milestones="zebra"))      # malformed: ignored, no crash
        self.assertFalse(self.found("zebra", milestones=[None, 5]))

    def test_injunction(self):
        self.assertTrue(self.found("zebra", injunction="Zebra v. State, D. Test"))

    def test_each_plain_field(self):
        for field in ("title", "summary", "bill_number", "state", "jurisdiction", "issuing_body",
                      "type", "verification", "last_verified", "id"):
            self.assertTrue(self.found("zebra", **{field: "Zebra"}), field)
        self.assertTrue(self.found("zebra", key_provisions=["A zebra clause"]))
        self.assertTrue(self.found("zebra", tags=["zebra"]))

    def test_tags_and_types_match_as_written_and_as_displayed(self):
        self.assertTrue(self.found("frontier_ai", tags=["frontier_ai"]))
        self.assertTrue(self.found("frontier ai", tags=["frontier_ai"]))
        self.assertTrue(self.found("executive order", type="executive_order"))

    def test_federal_records_match_us_federal(self):
        self.assertTrue(self.found("us federal", _source="us_federal_actions"))
        self.assertFalse(self.found("us federal", _source="international_frameworks"))

    def test_search_ignores_case_and_surrounding_space(self):
        self.assertTrue(self.found("  ZEBRA ", title="zebra crossing"))


class DashboardTests(unittest.TestCase):
    def test_runs_and_reports_the_right_total(self):
        done = run(SRC / "generate_dashboard.py")
        self.assertEqual(done.returncode, 0, text(done))
        total = sum(len(r) for r in load_records().values())
        self.assertIn(f"**Total Items Tracked:** {total}", text(done)[0])

    def test_every_status_in_the_data_is_counted(self):
        done = run(SRC / "generate_dashboard.py")
        out = text(done)[0]
        for filename, records in load_records().items():
            for status in {r["status"] for r in records}:
                self.assertIn(f"**{status.title()}:**", out, f"{filename}: status '{status}' not summarised")

    def test_survives_a_legacy_windows_console(self):
        done = run(SRC / "generate_dashboard.py", env_extra={"PYTHONIOENCODING": "cp1252"})
        self.assertEqual(done.returncode, 0, text(done))

    def test_key_dates_tolerates_a_malformed_milestones_value(self):
        # The validator reports this; the dashboard and the weekly report must not crash on it.
        for bad in (5, "x", None, {"date": "2030-01-01"}, [5, None, "x", {}]):
            record = {"effective_date": "2030-01-01", "milestones": bad}
            self.assertEqual(generate_dashboard.key_dates(record), [("2030-01-01", "Takes effect")], repr(bad))

    def test_upcoming_dates_skip_laws_that_are_not_in_force(self):
        data = {"us_state_bills": [
            {"id": "state-001", "state": "A", "title": "Dead", "status": "superseded", "effective_date": "2999-01-01"},
            {"id": "state-002", "state": "B", "title": "Live", "status": "enacted", "effective_date": "2999-01-01",
             "milestones": [{"date": "2999-06-01", "description": "Second stage"}]},
        ]}
        rows = generate_dashboard.upcoming_effective_dates(data, "2026-01-01")
        self.assertEqual([(r[2], r[3]) for r in rows], [("Live", "Takes effect"), ("Live", "Second stage")])

    def test_committed_example_matches_the_data(self):
        example = (ROOT / "examples" / "current_landscape.md").read_text(encoding="utf-8")
        total = sum(len(r) for r in load_records().values())
        self.assertTrue(
            f"**Total Items Tracked:** {total}" in example,
            "examples/current_landscape.md is stale. Regenerate it: "
            "python3 src/generate_dashboard.py examples/current_landscape.md")


class ExportTests(unittest.TestCase):
    def export(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.csv"
            done = run(SRC / "export_csv.py", str(target))
            self.assertEqual(done.returncode, 0, text(done))
            with open(target, encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
        return done, rows

    def test_one_row_per_record(self):
        _, rows = self.export()
        self.assertEqual(len(rows), sum(len(r) for r in load_records().values()))

    def test_no_field_in_the_data_is_dropped(self):
        # export_csv.py warns on stderr about any field without a column. If this
        # fails, add the new field to COLUMNS in src/export_csv.py.
        done, _ = self.export()
        self.assertEqual(text(done)[1], "")

    def test_federal_rows_keep_their_issuing_body(self):
        _, rows = self.export()
        federal = [r for r in rows if r["jurisdiction_type"] == "federal"]
        self.assertTrue(federal)
        self.assertTrue(all(r["issuing_body"] for r in federal))

    def test_milestones_become_readable_cells(self):
        records = [r for rs in load_records().values() for r in rs if r.get("milestones")]
        _, rows = self.export()
        by_id = {r["id"]: r for r in rows}
        for record in records:
            expected = " | ".join(f"{m['date']}: {m['description']}" for m in record["milestones"])
            self.assertEqual(by_id[record["id"]]["milestones"], expected)

    def test_dates_and_reasons_survive(self):
        records = [r for rs in load_records().values() for r in rs]
        _, rows = self.export()
        by_id = {r["id"]: r for r in rows}
        for record in records:
            for field in ("date_vetoed", "veto_reason", "date_rescinded"):
                if field in record:
                    self.assertEqual(by_id[record["id"]][field], record[field])


class RepoConsistencyTests(unittest.TestCase):
    """Numbers and dates written by hand in the README, checked against the data."""

    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    def jurisdictions(self):
        every = [r for records in load_records().values() for r in records]
        return {maintenance_report.jurisdiction_of(r) for r in every}

    def test_readme_badge_matches_the_data(self):
        match = re.search(r"Legislation%20Tracked-(\d+)-", self.readme)
        self.assertIsNotNone(match)
        total = sum(len(r) for r in load_records().values())
        self.assertEqual(int(match.group(1)), total, "README badge count is out of date")

    def test_readme_jurisdiction_counts_match_the_data(self):
        expected = len(self.jurisdictions())
        badge = re.search(r"Jurisdictions-(\d+)-", self.readme)
        self.assertIsNotNone(badge)
        self.assertEqual(int(badge.group(1)), expected, "README Jurisdictions badge is out of date")
        line = re.search(r"(\d+) entries across (\d+) jurisdictions", self.readme)
        self.assertIsNotNone(line, "README no longer has its 'N entries across M jurisdictions' line")
        total = sum(len(r) for r in load_records().values())
        self.assertEqual((int(line.group(1)), int(line.group(2))), (total, expected),
                         "README 'entries across jurisdictions' line is out of date")

    def test_readme_at_a_glance_table_matches_the_data(self):
        records = load_records()
        files = {"US Federal": ["us_federal_actions"], "US State": ["us_state_bills"],
                 "International": ["international_frameworks"], "Total": list(records)}
        section = self.readme.split("### At a glance", 1)[1].split("###", 1)[0]
        seen = set()
        for line in section.splitlines():
            cells = [c.strip().strip("*") for c in line.strip().strip("|").split("|")]
            if cells[0] not in files:
                continue
            seen.add(cells[0])
            rows = [r for name in files[cells[0]] for r in records[name]]
            in_force = sum(1 for r in rows if r["status"] in IN_FORCE)
            pending = sum(1 for r in rows if r["status"] == "pending")
            expected = [len(rows), in_force, pending, len(rows) - in_force - pending]
            written = [0 if c in ("—", "-", "") else int(c) for c in cells[1:5]]
            self.assertEqual(written, expected,
                             f"README 'At a glance' row '{cells[0]}' should read {expected} "
                             "(total, enacted/active/adopted, pending, the rest)")
        self.assertEqual(seen, set(files), "README 'At a glance' table is missing a row")

    def upcoming_table(self):
        return Counter((when.isoformat(), cells[0])
                       for when, cells in maintenance_report.readme_upcoming_rows(self.readme))

    def dated_stages(self):
        every = [r for records in load_records().values() for r in records]
        return [(when.isoformat(), maintenance_report.jurisdiction_of(record), record["id"], what)
                for when, record, what in maintenance_report.dated_stages(every)]

    def test_every_readme_upcoming_row_is_a_date_in_the_data(self):
        """Catches a README row left behind when a law's date changes or the law
        is superseded, which is how the Colorado entry went stale."""
        in_data = Counter((when, where) for when, where, _, _ in self.dated_stages())
        extra = sorted((self.upcoming_table() - in_data).elements())
        self.assertEqual(extra, [], "README 'Upcoming effective dates' rows with no matching date "
                                    "(date, jurisdiction) in the data: remove or correct them")

    def test_every_future_date_in_the_data_has_a_readme_row(self):
        """Only ever fails when the data or the README changes: as time passes,
        dates move into the past and stop being required."""
        today = datetime.date.today().isoformat()
        future = [stage for stage in self.dated_stages() if stage[0] > today]
        missing = Counter((when, where) for when, where, _, _ in future) - self.upcoming_table()
        details = [f"{when} | {where} | {rid}: {what}" for when, where, rid, what in future
                   if missing[(when, where)] > 0]
        self.assertEqual(details, [], "Add a row to README 'Upcoming effective dates' for each of these")


if __name__ == "__main__":
    unittest.main()
