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


class Raw(str):
    """File content written exactly as given, for text that is not valid JSON."""


class ValidatorTests(unittest.TestCase):
    def run_validator(self, files):
        """files: {filename: list_of_records}. A name may include a folder, such as
        meta/changelog.json. Content is written with json.dumps, which writes
        NaN for float("nan"), unless it is Raw text or bytes. Returns (exit_code, output)."""
        with tempfile.TemporaryDirectory() as tmp:
            for name, records in files.items():
                target = Path(tmp, name)
                target.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(records, bytes):
                    target.write_bytes(records)
                else:
                    target.write_text(records if isinstance(records, Raw) else json.dumps(records), encoding="utf-8")
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

    def test_every_link_direction_must_be_mutual(self):
        cases = [
            ([state(id="state-001"), state(id="state-002", amends="state-001")],
             "state-001 has amended_by = None"),
            ([state(id="state-001", amended_by="state-002"), state(id="state-002")],
             "state-002 has amends = None"),
            ([state(id="state-001"), state(id="state-002", supersedes="state-001")],
             "state-001 has superseded_by = None"),
            ([state(id="state-001", status="superseded", superseded_by="state-002"),
              state(id="state-002", supersedes="state-003"),
              state(id="state-003", status="superseded", superseded_by="state-002")],
             "but state-002 has supersedes = 'state-003'"),
        ]
        for records, fragment in cases:
            with self.subTest(fragment=fragment):
                self.assert_fails_with({"us_state_bills.json": records}, fragment)

    def test_mutual_amendment_passes(self):
        code, output = self.run_validator({"us_state_bills.json": [
            state(id="state-001", amended_by="state-002"), state(id="state-002", amends="state-001")]})
        self.assertEqual(code, 0, output)

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

    # --- odd values are reported, never a crash --------------------------------

    def test_status_that_is_not_text_is_reported_not_a_crash(self):
        for value in ({}, ["enacted"], 5):
            self.assert_fails_with({"us_state_bills.json": [state(status=value)]}, "is not one of")
        # An empty value for a required field reads as missing.
        self.assert_fails_with({"us_state_bills.json": [state(status=[])]}, "missing required field 'status'")

    def test_verification_that_is_not_text_is_reported_not_a_crash(self):
        for value in ([], {}, 5, None):
            self.assert_fails_with({"us_state_bills.json": [state(verification=value)]}, "is not one of")

    def test_null_is_not_a_date(self):
        self.assert_fails_with({"us_state_bills.json": [state(effective_date=None)]},
                               "leave the field out if there is no date")

    def test_link_must_be_one_record_id(self):
        for value in (None, "", 5, ["state-002"], "Colorado SB 26-189"):
            self.assert_fails_with({"us_state_bills.json": [state(superseded_by=value)]},
                                   "expected one record id")

    def test_optional_text_fields_cannot_be_blank_or_another_type(self):
        self.assert_fails_with({"us_state_bills.json": [state(type=7)]}, "'type' must be text")
        self.assert_fails_with({"us_state_bills.json": [state(injunction="  ")]}, "'injunction' must be text")
        self.assert_fails_with({"us_state_bills.json": [state(signatories="28")]}, "must be a whole number")
        self.assert_fails_with({"us_state_bills.json": [state(enforcement="AG")]}, "must be an object")
        self.assert_fails_with({"us_state_bills.json": [state(principles="fairness")]}, "list of non-blank strings")

    def test_dates_use_plain_digits(self):
        # The last two have ASCII months and days, which Python's own date parser
        # accepts, so only the ASCII-digit rule stands in their way.
        for date in ("\u0662\u0660\u0662\u0666-\u0660\u0661-\u0660\u0661", "\u0662\u0660\u0662\u0666-01-01",
                     "\uff12\uff10\uff12\uff16-01-01"):
            with self.subTest(date=date):
                self.assert_fails_with({"us_state_bills.json": [state(effective_date=date)]},
                                       "zero-padded YYYY-MM-DD")
                self.assert_fails_with(self.with_changelog([
                    {"date": date, "summary": "x", "updated": ["state-001"]}]), "zero-padded YYYY-MM-DD")

    def test_needs_verification_cannot_say_how_it_was_checked(self):
        for verification in ("primary", "secondary", "unconfirmed"):
            with self.subTest(verification=verification):
                self.assert_fails_with({"us_state_bills.json": [
                    state(last_verified="needs_verification", verification=verification)]}, "nobody has checked it")
        code, output = self.run_validator({"us_state_bills.json": [state(last_verified="needs_verification")]})
        self.assertEqual(code, 0, output)

    def test_tags_must_be_lowercase(self):
        for tag in ("Employment", "AI_Governance", "ai-safety", "ai safety"):
            with self.subTest(tag=tag):
                self.assert_fails_with({"us_state_bills.json": [state(tags=[tag])]}, "should be lowercase")

    def test_nan_and_infinity_are_not_json(self):
        """Python reads them; browsers do not, and the site would lose the whole file."""
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                self.assert_fails_with({"us_state_bills.json": [state(enforcement={"fine": value})]},
                                       "is not valid JSON")
        self.assert_fails_with(self.with_changelog(Raw('[{"date": "2026-01-01", "summary": "x", '
                                                       '"updated": ["state-001"], "n": NaN}]')), "is not valid JSON")

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

    def test_first_milestone_must_be_the_effective_date(self):
        # The site's "in force today" rule reads effective_date alone, so a phased
        # law whose first stage is somewhere else would be reported wrongly.
        self.assert_fails_with({"us_state_bills.json": [state(effective_date="2026-06-01", milestones=[
            {"date": "2026-01-01", "description": "First duties"},
            {"date": "2027-01-01", "description": "Second duties"}])]}, "but the first milestone is 2026-01-01")

    def test_milestones_need_an_effective_date(self):
        record = state(milestones=[{"date": "2026-01-01", "description": "First duties"}])
        del record["effective_date"]
        self.assert_fails_with({"us_state_bills.json": [record]}, "needs effective_date")

    def test_real_phased_records_follow_the_first_stage_rule(self):
        for name in ("us_federal_actions", "us_state_bills", "international_frameworks"):
            for record in json.loads((ROOT / "data" / f"{name}.json").read_text(encoding="utf-8")):
                if record.get("milestones"):
                    self.assertEqual(record["effective_date"], record["milestones"][0]["date"], record["id"])

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

    def test_changelog_ids_that_are_not_strings_are_reported_not_a_crash(self):
        self.assert_fails_with(self.with_changelog([
            {"date": "2026-01-01", "summary": "x", "updated": [{"id": "state-001"}]}]), "record ids as strings")
        self.assert_fails_with(self.with_changelog([
            {"date": "2026-01-01", "summary": "x", "added": [["state-001"]]}]), "record ids as strings")

    def test_changelog_dates_must_be_real_and_padded(self):
        for date in ("2026-1-5", "2026-02-30", 20260101, None, "yesterday"):
            with self.subTest(date=date):
                self.assert_fails_with(self.with_changelog([
                    {"date": date, "summary": "x", "updated": ["state-001"]}]), "expected a zero-padded YYYY-MM-DD date")

    def test_changelog_needs_a_summary(self):
        for entry in ({"date": "2026-01-01", "summary": "  ", "updated": ["state-001"]},
                      {"date": "2026-01-01", "summary": None, "updated": ["state-001"]},
                      {"date": "2026-01-01", "updated": ["state-001"]}):
            with self.subTest(entry=entry):
                self.assert_fails_with(self.with_changelog([entry]), "needs a non-empty 'summary'")

    def test_changelog_lists_each_record_once_per_entry(self):
        self.assert_fails_with(self.with_changelog([
            {"date": "2026-01-01", "summary": "x", "updated": ["state-001", "state-001"]}]), "listed more than once")
        self.assert_fails_with(self.with_changelog([
            {"date": "2026-01-01", "summary": "x", "added": ["state-001"], "updated": ["state-001"]}]),
            "listed more than once")

    def test_changelog_shapes_are_reported_not_a_crash(self):
        for ids in ({"state-001": True}, "state-001", None, 5):
            with self.subTest(added=ids):
                self.assert_fails_with(self.with_changelog([
                    {"date": "2026-01-01", "summary": "x", "added": ids, "updated": ["state-001"]}]),
                    "'added' must be a list of record ids")
        self.assert_fails_with(self.with_changelog(["oops"]), "entry is not an object")
        for content in ({}, None, "text", 5):
            with self.subTest(file=content):
                self.assert_fails_with(self.with_changelog(content), "expected a list of entries")
        self.assert_fails_with(self.with_changelog(Raw('[{"date": "2026-01-01",}]')), "cannot read as JSON")

    def test_data_file_shapes_are_reported_not_a_crash(self):
        for content in ({}, None, "text"):
            with self.subTest(file=content):
                self.assert_fails_with({"us_state_bills.json": content}, "expected a list of records")
        self.assert_fails_with({"us_state_bills.json": Raw("[{,]")}, "cannot read as JSON")
        self.assert_fails_with({"us_state_bills.json": b"[\xff\xfe]"}, "cannot read as JSON")   # not UTF-8

    def test_every_record_must_be_listed_as_added(self):
        records = [state(id="state-001"), state(id="state-002", title="Second Act")]
        self.assert_fails_with(self.with_changelog([
            {"date": "2026-01-01", "summary": "x", "added": ["state-001"]}], records), "state-002 is never listed as added")
        code, output = self.run_validator(self.with_changelog([
            {"date": "2026-02-01", "summary": "y", "added": ["state-002"], "updated": ["state-001"]},
            {"date": "2026-01-01", "summary": "x", "added": ["state-001"]}], records))
        self.assertEqual(code, 0, output)

    def test_changelog_rejects_unknown_fields(self):
        self.assert_fails_with(self.with_changelog([
            {"date": "2026-01-01", "summary": "x", "updated": ["state-001"], "author": "me"}]), "unexpected field")


if __name__ == "__main__":
    unittest.main()
