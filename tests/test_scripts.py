"""
Smoke tests for the command-line tools and the files generated from the data.
Standard library only.

    python3 -m unittest discover -s tests

These run the real scripts against the real data/ files, read-only. They fail
when a tool crashes, drops a field, or when a committed file has drifted away
from the data it was generated from.
"""

import csv
import glob
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


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

    def test_dates_and_reasons_survive(self):
        records = [r for rs in load_records().values() for r in rs]
        _, rows = self.export()
        by_id = {r["id"]: r for r in rows}
        for record in records:
            for field in ("date_vetoed", "veto_reason", "date_rescinded"):
                if field in record:
                    self.assertEqual(by_id[record["id"]][field], record[field])


class RepoConsistencyTests(unittest.TestCase):
    def test_readme_badge_matches_the_data(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        match = re.search(r"Legislation%20Tracked-(\d+)-", readme)
        self.assertIsNotNone(match)
        total = sum(len(r) for r in load_records().values())
        self.assertEqual(int(match.group(1)), total, "README badge count is out of date")


if __name__ == "__main__":
    unittest.main()
