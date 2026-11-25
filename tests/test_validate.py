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
        """files: {filename: list_of_records}. A name may include a folder, such as
        meta/changelog.json. Returns (exit_code, output)."""
        with tempfile.TemporaryDirectory() as tmp:
            for name, records in files.items():
                target = Path(tmp, name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(records), encoding="utf-8")
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

    # --- enjoined -----------------------------------------------------------

    def test_enjoined_requires_an_injunction(self):
        self.assert_fails_with({"us_state_bills.json": [state(status="enjoined")]}, "requires 'injunction'")

    def test_enjoined_with_injunction_passes(self):
        code, output = self.run_validator({"us_state_bills.json": [state(
            status="enjoined", injunction="Preliminary injunction, Example v. State, D. Test, 2026-03-01",
            date_enjoined="2026-03-01")]})
        self.assertEqual(code, 0, output)

    # --- field vocabulary ---------------------------------------------------

    def test_misspelled_field_is_rejected(self):
        self.assert_fails_with({"us_state_bills.json": [state(efective_date="2026-01-01")]},
                               "unknown field 'efective_date'")

    def test_retired_date_effective_names_its_replacement(self):
        self.assert_fails_with({"us_state_bills.json": [state(date_effective="2026-01-01")]},
                               "rename it to 'effective_date'")

    # --- milestones ---------------------------------------------------------

    def test_good_milestones_pass(self):
        code, output = self.run_validator({"us_state_bills.json": [state(milestones=[
            {"date": "2026-01-01", "description": "First duties"},
            {"date": "2027-01-01", "description": "Second duties"}])]})
        self.assertEqual(code, 0, output)

    def test_milestones_must_be_a_non_empty_list(self):
        self.assert_fails_with({"us_state_bills.json": [state(milestones=[])]}, "non-empty list")

    def test_milestone_dates_must_be_valid(self):
        self.assert_fails_with({"us_state_bills.json": [state(milestones=[
            {"date": "2026-1-1", "description": "x"}])]}, "milestones[0] date")

    def test_milestones_must_be_in_order(self):
        self.assert_fails_with({"us_state_bills.json": [state(milestones=[
            {"date": "2027-01-01", "description": "later"},
            {"date": "2026-01-01", "description": "earlier"}])]}, "oldest first")

    def test_milestone_needs_a_description_and_no_extra_fields(self):
        self.assert_fails_with({"us_state_bills.json": [state(milestones=[
            {"date": "2026-01-01", "description": "", "note": "x"}])]}, "unexpected field")
        self.assert_fails_with({"us_state_bills.json": [state(milestones=[
            {"date": "2026-01-01"}])]}, "non-empty 'description'")

    # --- changelog ----------------------------------------------------------

    def with_changelog(self, entries, records=None):
        return {"us_state_bills.json": records or [state()], "meta/changelog.json": entries}

    def test_good_changelog_passes(self):
        code, output = self.run_validator(self.with_changelog([
            {"date": "2026-02-01", "summary": "Corrected it.", "updated": ["state-001"]},
            {"date": "2026-01-01", "summary": "Added it.", "added": ["state-001"]}]))
        self.assertEqual(code, 0, output)

    def test_changelog_ids_must_exist(self):
        self.assert_fails_with(self.with_changelog([
            {"date": "2026-01-01", "summary": "x", "added": ["state-999"]}]), "unknown id 'state-999'")

    def test_changelog_must_be_newest_first(self):
        self.assert_fails_with(self.with_changelog([
            {"date": "2026-01-01", "summary": "x", "updated": ["state-001"]},
            {"date": "2026-02-01", "summary": "y", "updated": ["state-001"]}]), "newest first")

    def test_changelog_entry_must_name_a_record(self):
        self.assert_fails_with(self.with_changelog([
            {"date": "2026-01-01", "summary": "x"}]), "at least one record")

    def test_record_cannot_be_added_twice(self):
        self.assert_fails_with(self.with_changelog([
            {"date": "2026-02-01", "summary": "x", "added": ["state-001"]},
            {"date": "2026-01-01", "summary": "y", "added": ["state-001"]}]), "added twice")

    def test_changelog_rejects_unknown_fields(self):
        self.assert_fails_with(self.with_changelog([
            {"date": "2026-01-01", "summary": "x", "updated": ["state-001"], "author": "me"}]), "unexpected field")


if __name__ == "__main__":
    unittest.main()
