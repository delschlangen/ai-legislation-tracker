"""
Tests for validate.py. Standard library only.

    python3 -m unittest discover -s tests

Each test writes a tiny data directory to a temporary folder and points the
validator at it, so nothing here touches the real data/ files.
"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import validate  # noqa: E402


def state(**overrides):
    record = {
        "id": "state-001",
        "state": "Testland",
        "bill_number": "HB 1",
        "title": "Test Act",
        "status": "enacted",
        "date_enacted": "2025-01-02",
        "effective_date": "2026-01-01",
        "summary": "A summary.",
        "key_provisions": ["One", "Two", "Three"],
        "source_url": "https://legislature.example/bills/hb1",
        "tags": ["testing"],
        "last_verified": "2026-09-17",
    }
    record.update(overrides)
    return record


def federal(**overrides):
    record = {
        "id": "fed-001",
        "title": "Test Order",
        "type": "executive_order",
        "status": "active",
        "date_issued": "2025-01-02",
        "issuing_body": "White House",
        "summary": "A summary.",
        "key_provisions": ["One", "Two", "Three"],
        "source_url": "https://agency.example/orders/1",
        "tags": ["testing"],
        "last_verified": "2026-09-17",
    }
    record.update(overrides)
    return record


class ValidatorTests(unittest.TestCase):
    def run_validator(self, files):
        """files: {filename: list_of_records}. Returns (exit_code, output)."""
        with tempfile.TemporaryDirectory() as tmp:
            for name, records in files.items():
                Path(tmp, name).write_text(json.dumps(records), encoding="utf-8")
            original = validate.DATA_DIR
            validate.DATA_DIR = Path(tmp)
            out = io.StringIO()
            try:
                with contextlib.redirect_stdout(out):
                    code = validate.main(["--quiet"])
            finally:
                validate.DATA_DIR = original
        return code, out.getvalue()

    def assert_fails_with(self, files, fragment):
        code, output = self.run_validator(files)
        self.assertEqual(code, 1, f"expected a failure, got:\n{output}")
        self.assertIn(fragment, output)

    def test_real_data_is_valid(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = validate.main(["--quiet"])
        self.assertEqual(code, 0, out.getvalue())

    def test_good_records_pass(self):
        code, output = self.run_validator({
            "us_state_bills.json": [state()],
            "us_federal_actions.json": [federal()],
        })
        self.assertEqual(code, 0, output)

    def test_tags_must_be_a_list(self):
        self.assert_fails_with({"us_state_bills.json": [state(tags="employment")]}, "'tags' must be a list")

    def test_key_provisions_must_be_a_list(self):
        self.assert_fails_with(
            {"us_state_bills.json": [state(key_provisions="one long string")]}, "'key_provisions' must be a list")

    def test_dates_must_be_zero_padded(self):
        self.assert_fails_with(
            {"us_state_bills.json": [state(effective_date="2026-1-5")]}, "zero-padded YYYY-MM-DD")

    def test_dates_must_be_real(self):
        self.assert_fails_with(
            {"us_state_bills.json": [state(effective_date="2026-02-30")]}, "zero-padded YYYY-MM-DD")

    def test_sentinel_is_only_for_last_verified(self):
        code, output = self.run_validator(
            {"us_state_bills.json": [state(last_verified="needs_verification")]})
        self.assertEqual(code, 0, output)
        self.assert_fails_with(
            {"us_state_bills.json": [state(effective_date="needs_verification")]}, "'effective_date'")

    def test_non_object_record_is_reported_not_a_crash(self):
        self.assert_fails_with({"us_state_bills.json": [state(), "oops"]}, "record is not an object")

    def test_title_is_required_and_name_is_retired(self):
        record = state()
        record["name"] = record.pop("title")
        self.assert_fails_with({"us_state_bills.json": [record]}, "retired field 'name'")

    def test_bare_domain_url_is_rejected(self):
        self.assert_fails_with(
            {"us_state_bills.json": [state(source_url="https://legislature.example")]}, "not a specific http(s) link")

    def test_placeholder_id_is_rejected(self):
        self.assert_fails_with({"us_state_bills.json": [state(id="state-NNN")]}, "followed by at least three digits")

    def test_id_prefix_must_match_the_file(self):
        self.assert_fails_with({"us_state_bills.json": [state(id="fed-001")]}, "followed by at least three digits")

    def test_duplicate_ids_are_rejected(self):
        self.assert_fails_with(
            {"us_state_bills.json": [state(), state(title="Another Act")]}, "duplicate id")

    def test_per_file_required_fields(self):
        record = federal()
        del record["issuing_body"]
        self.assert_fails_with({"us_federal_actions.json": [record]}, "missing required field 'issuing_body'")

    def test_superseded_requires_a_successor(self):
        self.assert_fails_with(
            {"us_state_bills.json": [state(status="superseded")]}, "requires 'superseded_by'")

    def test_vetoed_requires_a_reason(self):
        self.assert_fails_with({"us_state_bills.json": [state(status="vetoed")]}, "requires 'veto_reason'")

    def test_one_way_supersession_is_rejected(self):
        old = state(id="state-001", status="superseded", superseded_by="state-002", date_superseded="2026-05-01")
        new = state(id="state-002", title="Replacement Act")
        self.assert_fails_with({"us_state_bills.json": [old, new]}, "state-002 has supersedes = None")

    def test_mutual_supersession_passes(self):
        old = state(id="state-001", status="superseded", superseded_by="state-002", date_superseded="2026-05-01")
        new = state(id="state-002", title="Replacement Act", supersedes="state-001")
        code, output = self.run_validator({"us_state_bills.json": [old, new]})
        self.assertEqual(code, 0, output)

    def test_link_to_unknown_id_is_rejected(self):
        self.assert_fails_with(
            {"us_state_bills.json": [state(amends="state-999")]}, "points at unknown id 'state-999'")

    def test_link_to_self_is_rejected(self):
        self.assert_fails_with({"us_state_bills.json": [state(amends="state-001")]}, "points at itself")

    def test_unknown_status_is_rejected(self):
        self.assert_fails_with({"us_state_bills.json": [state(status="maybe")]}, "is not one of")


if __name__ == "__main__":
    unittest.main()
