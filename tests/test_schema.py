"""
Keeps schema/legislation.schema.json and validate.py in agreement, and checks
the real data against the schema. Standard library only.

    python3 -m unittest discover -s tests

validate.py checks every record against the schema with its own small checker
(the project has no dependencies). These tests cover that checker, the rules
the two layers share, and the few places where validate.py is deliberately
stricter than a schema can be. If the `jsonschema` package happens to be
installed, one extra test compares the small checker with it; without the
package that test is skipped.
"""

import contextlib
import copy
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import validate  # noqa: E402

SCHEMA, _problem = validate.load_schema()
assert SCHEMA is not None, _problem

FILE_DEFS = {
    "us_federal_actions.json": "federalFile",
    "us_state_bills.json": "stateFile",
    "international_frameworks.json": "internationalFile",
}

try:
    import jsonschema  # optional; never required
except ImportError:
    jsonschema = None


def errors(value, definition):
    return validate.schema_errors(value, {"$ref": f"#/$defs/{definition}"}, SCHEMA)


def friendly(filename, record):
    """Problems from validate.py's own checks, without the schema layer."""
    problems = []
    validate.check_record(filename, record, problems)
    return problems


# ---------------------------------------------------------------------------
# A table of records, each a valid base record with one thing changed.
# ---------------------------------------------------------------------------

STATE = {
    "id": "state-001", "state": "Testland", "bill_number": "HB 1", "title": "Test Act",
    "status": "enacted", "date_enacted": "2025-06-01", "effective_date": "2026-01-01",
    "summary": "A summary.", "key_provisions": ["One", "Two"],
    "source_url": "https://legislature.example/bills/hb1", "tags": ["testing"],
    "last_verified": "2026-09-17", "verification": "secondary",
}
FEDERAL = {
    "id": "fed-001", "title": "Test Order", "type": "executive_order", "status": "active",
    "date_issued": "2025-01-02", "issuing_body": "White House", "summary": "A summary.",
    "key_provisions": ["One"], "source_url": "https://agency.example/orders/1",
    "tags": ["testing"], "last_verified": "2026-09-17",
}
INTERNATIONAL = {
    "id": "intl-001", "jurisdiction": "Testland", "title": "Test Regulation", "type": "regulation",
    "status": "enacted", "date_adopted": "2025-01-02", "summary": "A summary.",
    "key_provisions": ["One"], "source_url": "https://gazette.example/reg/1",
    "tags": ["testing"], "last_verified": "2026-09-17",
}
BASES = {
    "us_state_bills.json": ("stateRecord", STATE),
    "us_federal_actions.json": ("federalRecord", FEDERAL),
    "international_frameworks.json": ("internationalRecord", INTERNATIONAL),
}

DROP = object()
GOOD_MILESTONES = [{"date": "2026-01-01", "description": "First"}, {"date": "2027-01-01", "description": "Second"}]

# Rejected by the schema and by validate.py's own checks.
BOTH = [
    {"status": "maybe"}, {"status": ["enacted"]}, {"status": None}, {"status": 5},
    {"id": "fed-001"}, {"id": "state-1"}, {"id": 5}, {"id": "state-\u0660\u0660\u0661"},  # digits from another script
    {"id": DROP}, {"title": DROP}, {"status": DROP}, {"summary": DROP}, {"key_provisions": DROP},
    {"source_url": DROP}, {"tags": DROP}, {"last_verified": DROP}, {"state": DROP}, {"bill_number": DROP},
    {"title": ""}, {"title": "   "}, {"title": 5}, {"title": None}, {"summary": None}, {"summary": ["x"]},
    {"state": ["Texas"]}, {"state": ""}, {"bill_number": 123},
    {"type": 7}, {"type": ""}, {"jurisdiction": 5}, {"issuing_body": {}},
    {"effective_date": None}, {"effective_date": "2026-1-1"}, {"effective_date": 20260101},
    {"effective_date": "\u0662\u0660\u0662\u0666-\u0660\u0661-\u0660\u0661"},
    # Only the year in another script: Python's strptime accepts this one, so
    # only the ASCII-digit rule rejects it.
    {"effective_date": "\u0662\u0660\u0662\u0666-01-01"}, {"effective_date": "\uff12\uff10\uff12\uff16-01-01"},
    {"date_issued": None}, {"date_introduced": None}, {"date_enacted": None}, {"date_adopted": None},
    {"full_application_date": None}, {"date_rescinded": None}, {"date_vetoed": None},
    {"date_superseded": None}, {"date_expired": None}, {"date_enjoined": None},
    {"date_enjoined": "soon"}, {"last_verified": "yesterday"}, {"last_verified": None},
    {"verification": None}, {"verification": "tertiary"}, {"verification": ["primary"]},
    {"superseded_by": None}, {"superseded_by": ""}, {"superseded_by": "state-1"}, {"supersedes": 5},
    {"amends": ["state-002"]}, {"amended_by": "x"},
    {"status": "superseded"}, {"status": "vetoed"}, {"status": "enjoined"},
    {"status": "vetoed", "veto_reason": ""}, {"status": "enjoined", "injunction": ""},
    {"veto_reason": 5}, {"injunction": None},
    {"tags": "t"}, {"tags": []}, {"tags": ["bad tag"]}, {"tags": ["Employment"]}, {"tags": ["ai-safety"]},
    {"tags": [5]},
    {"key_provisions": "one"}, {"key_provisions": []}, {"key_provisions": [""]},
    {"key_provisions": ["  "]}, {"key_provisions": [5]},
    {"covered_decisions": "hiring"}, {"covered_decisions": [5]}, {"covered_decisions": [""]},
    {"principles": "fairness"},
    {"signatories": "28"}, {"signatories": True}, {"signatories": 2.5}, {"signatories": None},
    {"enforcement": "AG"}, {"enforcement": ["x"]},
    {"source_url": "https://example.gov"}, {"source_url": "https://example.gov/"},
    {"source_url": "https://example.gov//"}, {"source_url": "ftp://example.gov/x"},
    {"source_url": 5}, {"source_url": "example.gov/x"},
    # A homepage with only a fragment, whitespace or an empty query after it.
    {"source_url": "https://example.gov/#main-content"}, {"source_url": "https://example.gov/ "},
    {"source_url": "https://example.gov/\n"}, {"source_url": "https://example.gov/?"},
    {"source_url": "https://example.gov/\u00a0"}, {"source_url": "https://example.gov/\ufeff"},
    {"source_url": "https://example.gov/#?x=1"}, {"source_url": "https://example.gov/a b"},
    {"efective_date": "2026-01-01"}, {"name": "Old Name"}, {"date_effective": "2026-01-01"},
    {"milestones": []}, {"milestones": "x"}, {"milestones": [5]},
    {"milestones": [{"date": "2026-01-01"}]},
    {"milestones": [{"date": "2026-1-1", "description": "x"}]},
    {"milestones": [{"date": "2026-01-01", "description": ""}]},
    {"milestones": [{"date": "2026-01-01", "description": "x", "note": "y"}]},
    {"milestones": GOOD_MILESTONES, "effective_date": DROP},
]

# Rejected by validate.py only: rules a JSON Schema cannot express.
VALIDATOR_ONLY = [
    {"effective_date": "2026-02-30"},                                   # not a real calendar date
    {"last_verified": "2026-02-30"},
    {"milestones": [{"date": "2026-02-30", "description": "x"}]},
    {"milestones": list(reversed(GOOD_MILESTONES))},                    # not oldest first
    {"milestones": GOOD_MILESTONES, "effective_date": "2025-06-01"},    # first stage is not effective_date
    {"signatories": 28.0},                                              # an integer to JSON Schema
]

# Accepted by both.
NEITHER = [
    {}, {"verification": DROP}, {"effective_date": DROP}, {"last_verified": "needs_verification"},
    {"source_url": "https://example.gov?bill=1"}, {"source_url": "http://example.gov/x"},
    {"source_url": "https://example.gov/x#section-2"}, {"source_url": "https://example.gov/?bill=1#top"},
    {"signatories": 28}, {"enforcement": {"fines": 1}}, {"covered_decisions": []},
    {"principles": ["Fairness"]}, {"type": "statute"}, {"milestones": GOOD_MILESTONES},
    {"status": "vetoed", "veto_reason": "Too broad"},
    {"status": "enjoined", "injunction": "Example v. State, D. Test, 2026-03-01", "date_enjoined": "2026-03-01"},
    {"status": "superseded", "superseded_by": "state-002"}, {"amends": "intl-001"},
]

# Where JavaScript patterns and Python patterns differ: "$" before a final
# newline. The schema is the JavaScript reading; so is validate.py.
END_OF_STRING = [{"effective_date": "2026-01-01\n"}, {"tags": ["ok\n"]}, {"last_verified": "2026-01-01\n"},
                 {"id": "state-001\n"}, {"superseded_by": "state-002\n"}]

PER_FILE = [
    ("us_federal_actions.json", {"type": DROP}), ("us_federal_actions.json", {"issuing_body": DROP}),
    ("us_federal_actions.json", {"date_issued": DROP}), ("us_federal_actions.json", {"id": "state-001"}),
    ("international_frameworks.json", {"jurisdiction": DROP}), ("international_frameworks.json", {"type": DROP}),
    ("international_frameworks.json", {"id": "fed-001"}),
]


def changed(base, change):
    record = copy.deepcopy(base)
    for key, value in change.items():
        if value is DROP:
            record.pop(key, None)
        else:
            record[key] = copy.deepcopy(value)
    return record


def describe(change):
    return {k: ("<removed>" if v is DROP else v) for k, v in change.items()}


class AgreementTests(unittest.TestCase):
    """Each changed record gets the verdict the table says, from both layers."""

    def verdicts(self, filename, change):
        definition, base = BASES[filename]
        record = changed(base, change)
        return bool(errors(record, definition)), bool(friendly(filename, record))

    def test_rejected_by_both(self):
        for change in BOTH + END_OF_STRING:
            with self.subTest(change=describe(change)):
                self.assertEqual(self.verdicts("us_state_bills.json", change), (True, True))

    def test_per_file_rules_rejected_by_both(self):
        for filename, change in PER_FILE:
            with self.subTest(file=filename, change=describe(change)):
                self.assertEqual(self.verdicts(filename, change), (True, True))

    def test_rejected_by_the_validator_only(self):
        for change in VALIDATOR_ONLY:
            with self.subTest(change=describe(change)):
                self.assertEqual(self.verdicts("us_state_bills.json", change), (False, True))

    def test_accepted_by_both(self):
        for filename in BASES:
            with self.subTest(file=filename, change="base record"):
                self.assertEqual(self.verdicts(filename, {}), (False, False))
        for change in NEITHER:
            with self.subTest(change=describe(change)):
                self.assertEqual(self.verdicts("us_state_bills.json", change), (False, False))

    def test_nothing_the_schema_rejects_passes_the_validator(self):
        """The promise in README and CLAUDE.md, checked over every case in the table."""
        for change in BOTH + VALIDATOR_ONLY + NEITHER + END_OF_STRING:
            schema_rejects, validator_rejects = self.verdicts("us_state_bills.json", change)
            if schema_rejects:
                self.assertTrue(validator_rejects, describe(change))


class SourceUrlRuleTests(unittest.TestCase):
    """The schema's source_url pattern and validate.is_specific_url are one rule written twice."""

    URLS = [
        "https://example.gov", "https://example.gov/", "https://example.gov//", "https://example.gov///x",
        "https://example.gov/x", "https://example.gov/x/", "https://example.gov?x=1", "https://example.gov/?x=1",
        "https://example.gov/?", "https://example.gov?", "http://example.gov/x", "http://example.gov",
        "ftp://example.gov/x", "example.gov/x", "//example.gov/x", "https:/example.gov/x", "https://",
        "https:///x", "https://?", "HTTPS://example.gov/x", " https://example.gov/x", "https://example.gov/ ",
        "https://example.gov/\n", "https://example.gov/x\ny", "https://a/b?c#d", "https://a#frag", "https://a/#frag",
        "", "https", "https://example.gov:8443/doc.pdf", "https://example.gov/a%20b", "https://xn--e1afmkfd.example/x",
        "https://example.gov/#main-content", "https://example.gov/#?x=1", "https://example.gov/?#x",
        "https://example.gov/??", "https://example.gov/x#section-2", "https://example.gov/\u00a0",
        "https://example.gov/\u2028", "https://example.gov/\ufeff", "https://example.gov/a b", "https://ex\tample.gov/x",
    ]

    pattern = SCHEMA["$defs"]["record"]["properties"]["source_url"]["pattern"]

    def agree(self, url):
        schema_says = validate._pattern_matches(self.pattern, url)
        self.assertEqual(re.search(self.pattern, url) is not None, schema_says, url)
        self.assertEqual(schema_says, validate.is_specific_url(url), url)
        return schema_says

    def test_pattern_and_function_agree(self):
        for url in self.URLS:
            with self.subTest(url=url):
                self.agree(url)

    def test_they_agree_on_generated_urls(self):
        hosts = ["", "a", "a.gov", "a:8080", "u@a"]
        paths = ["", "/", "//", "/x", "//x", "/x/", "/%20", "/?"]
        queries = ["", "?", "?q", "??", "?#"]
        fragments = ["", "#", "#f", "#/x", "#?q"]
        extras = ["", " ", "\t", "\n", "\u00a0", "\u2028", "\u3000", "\ufeff", "\x7f", "\x85", "x"]
        count = 0
        for scheme in ("https://", "http://", "HTTP://", "ftp://"):
            for host in hosts:
                for path in paths:
                    for query in queries:
                        for fragment in fragments:
                            for extra in extras:
                                for url in (scheme + host + path + query + fragment + extra,
                                            scheme + host + extra + path + query + fragment):
                                    self.agree(url)
                                    count += 1
        self.assertGreater(count, 20000)

    def test_verdicts(self):
        """Agreement alone would pass if both copies of the rule were wrong."""
        for url in ("https://example.gov/#main-content", "https://example.gov/ ", "https://example.gov/\n",
                    "https://example.gov/?", "https://example.gov", "https://example.gov/#/bill/1",
                    "https://example.gov/\u00a0", " https://example.gov/x", "https://exa mple.gov/x"):
            self.assertFalse(self.agree(url), url)
        for url in ("https://example.gov/x", "https://example.gov/?bill=1", "https://example.gov?bill=1",
                    "https://example.gov/x#top", "https://example.gov/a%20b", "http://example.gov//x"):
            self.assertTrue(self.agree(url), url)


class SchemaMatchesValidatorTests(unittest.TestCase):
    record = SCHEMA["$defs"]["record"]

    def test_status_values_match(self):
        self.assertEqual(set(self.record["properties"]["status"]["enum"]), validate.VALID_STATUS)

    def test_verification_values_match(self):
        self.assertEqual(set(self.record["properties"]["verification"]["enum"]), validate.VALID_VERIFICATION)

    def test_field_vocabulary_matches(self):
        self.assertEqual(set(self.record["properties"]), validate.KNOWN_FIELDS)

    def test_common_required_fields_match(self):
        self.assertEqual(set(self.record["required"]), set(validate.REQUIRED))

    def test_per_file_required_fields_match(self):
        for filename, definition in validate.SCHEMA_DEF_BY_FILE.items():
            extra = set(SCHEMA["$defs"][definition]["allOf"][1]["required"])
            self.assertEqual(extra, set(validate.REQUIRED_BY_FILE[filename]), filename)

    def test_per_file_id_prefixes_match(self):
        for filename, definition in validate.SCHEMA_DEF_BY_FILE.items():
            pattern = SCHEMA["$defs"][definition]["allOf"][1]["properties"]["id"]["pattern"]
            self.assertTrue(pattern.startswith("^" + validate.ID_PREFIX_BY_FILE[filename]), filename)

    def test_status_rules_match(self):
        rules = {}
        for rule in self.record["allOf"]:
            status = rule["if"]["properties"]["status"]["const"]
            rules[status] = rule["then"]["required"]
        self.assertEqual(rules, validate.REQUIRED_BY_STATUS)

    def test_date_fields_are_dates_in_the_schema(self):
        for field in validate.DATE_FIELDS:
            if field == "last_verified":
                continue
            self.assertEqual(self.record["properties"][field].get("$ref"), "#/$defs/date", field)

    def test_link_fields_are_record_ids_in_the_schema(self):
        for field in validate.RECIPROCAL:
            self.assertEqual(self.record["properties"][field].get("$ref"), "#/$defs/recordId", field)

    def test_text_fields_are_non_empty_strings_in_the_schema(self):
        for field in validate.STRING_FIELDS:
            self.assertEqual(self.record["properties"][field].get("$ref"), "#/$defs/nonEmptyString", field)


class CheckerTests(unittest.TestCase):
    """The small JSON Schema checker inside validate.py."""

    def test_every_keyword_in_the_schema_is_implemented(self):
        allowed = validate.SCHEMA_RULES | validate.SCHEMA_ANNOTATIONS

        def walk(node, where):
            self.assertIsInstance(node, dict, where)
            self.assertEqual(set(node) - allowed, set(), f"unsupported keyword at {where}")
            for name in ("$defs", "properties"):
                for key, sub in node.get(name, {}).items():
                    walk(sub, f"{where}/{name}/{key}")
            for name in ("items", "if", "then"):
                if name in node:
                    walk(node[name], f"{where}/{name}")
            for name in ("allOf", "anyOf"):
                for index, sub in enumerate(node.get(name, [])):
                    walk(sub, f"{where}/{name}/{index}")

        walk(SCHEMA, "#")

    def test_an_unsupported_keyword_is_an_error_not_a_silent_pass(self):
        with self.assertRaises(validate.SchemaError):
            validate.schema_errors("abc", {"maxLength": 2}, {})
        with self.assertRaises(validate.SchemaError):
            validate.schema_errors("abc", {"type": ["string", "null"]}, {})
        with self.assertRaises(validate.SchemaError):
            validate.schema_errors({}, {"additionalProperties": {"type": "string"}}, {})

    def test_dollar_means_the_very_end(self):
        self.assertEqual(validate.schema_errors("ab", {"pattern": "^ab$"}, {}), [])
        self.assertNotEqual(validate.schema_errors("ab\n", {"pattern": "^ab$"}, {}), [])
        # An escaped backslash before the final "$" leaves it an anchor.
        self.assertEqual(validate.schema_errors("a\\", {"pattern": "^a\\\\$"}, {}), [])
        self.assertNotEqual(validate.schema_errors("a\\\n", {"pattern": "^a\\\\$"}, {}), [])
        # A literal dollar is just a character.
        self.assertEqual(validate.schema_errors("a$b", {"pattern": "^a\\$b"}, {}), [])
        self.assertEqual(validate.schema_errors("a$", {"pattern": "^a[$]"}, {}), [])
        self.assertEqual(validate.schema_errors("]$", {"pattern": "^[]$]+"}, {}), [])

    def test_a_dollar_anchor_before_the_end_is_refused(self):
        for pattern in ("^a$|^ab$", "^(a$)", "^(?:a$|b)", "a$|b"):
            with self.subTest(pattern=pattern):
                with self.assertRaises(validate.SchemaError):
                    validate.schema_errors("a", {"pattern": pattern}, {})

    def test_equality_is_json_equality_at_any_depth(self):
        reject = [({"const": [1]}, [True]), ({"const": {"a": True}}, {"a": 1}), ({"enum": [[1, 2]]}, [True, 2]),
                  ({"const": [False]}, [0]), ({"const": [[True]]}, [[1]]), ({"const": [1]}, 1),
                  ({"const": {"a": 1}}, {"a": 1, "b": 2}), ({"const": [1, 2]}, [1])]
        accept = [({"const": [1]}, [1.0]), ({"const": {"a": [True, None]}}, {"a": [True, None]}),
                  ({"enum": ["x", [1, {"b": False}]]}, [1.0, {"b": False}])]
        for schema, value in reject:
            self.assertNotEqual(validate.schema_errors(value, schema, {}), [], (schema, value))
        for schema, value in accept:
            self.assertEqual(validate.schema_errors(value, schema, {}), [], (schema, value))

    def test_json_number_and_boolean_rules(self):
        self.assertEqual(validate.schema_errors(28, {"type": "integer"}, {}), [])
        self.assertEqual(validate.schema_errors(28.0, {"type": "integer"}, {}), [])
        self.assertNotEqual(validate.schema_errors(True, {"type": "integer"}, {}), [])
        self.assertNotEqual(validate.schema_errors(2.5, {"type": "integer"}, {}), [])
        self.assertNotEqual(validate.schema_errors(1, {"const": True}, {}), [])
        self.assertEqual(validate.schema_errors(1.0, {"enum": [1]}, {}), [])

    def test_if_then_and_dependent_required(self):
        rule = {"if": {"properties": {"a": {"const": 1}}, "required": ["a"]}, "then": {"required": ["b"]}}
        self.assertNotEqual(validate.schema_errors({"a": 1}, rule, {}), [])
        self.assertEqual(validate.schema_errors({"a": 1, "b": 2}, rule, {}), [])
        self.assertEqual(validate.schema_errors({"a": 2}, rule, {}), [])
        dependent = {"dependentRequired": {"a": ["b"]}}
        self.assertNotEqual(validate.schema_errors({"a": 1}, dependent, {}), [])
        self.assertEqual(validate.schema_errors({"c": 1}, dependent, {}), [])


class DataMatchesSchemaTests(unittest.TestCase):
    def test_every_file_validates(self):
        for filename, definition in FILE_DEFS.items():
            data = json.loads((ROOT / "data" / filename).read_text(encoding="utf-8"))
            problems = errors(data, definition)
            self.assertEqual(problems, [], f"{filename}:\n" + "\n".join(problems[:20]))

    def test_root_accepts_every_file(self):
        for filename in FILE_DEFS:
            data = json.loads((ROOT / "data" / filename).read_text(encoding="utf-8"))
            self.assertEqual(validate.schema_errors(data, SCHEMA, SCHEMA), [], filename)


class ValidatorUsesTheSchemaTests(unittest.TestCase):
    """validate.py runs the schema itself, so a gap in its own checks cannot let bad data through."""

    def run_validator(self, records, schema_path=None):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "us_state_bills.json").write_text(json.dumps(records), encoding="utf-8")
            saved = validate.DATA_DIR, validate.SCHEMA_PATH
            validate.DATA_DIR = Path(tmp)
            if schema_path is not None:
                validate.SCHEMA_PATH = schema_path
            out = io.StringIO()
            try:
                with contextlib.redirect_stdout(out):
                    code = validate.main(["--quiet"])
            finally:
                validate.DATA_DIR, validate.SCHEMA_PATH = saved
        return code, out.getvalue()

    def test_schema_catches_what_the_other_checks_miss(self):
        original = validate.check_record
        validate.check_record = lambda filename, record, problems: None
        try:
            code, output = self.run_validator([changed(STATE, {"signatories": "28"})])
        finally:
            validate.check_record = original
        self.assertEqual(code, 1, output)
        self.assertIn("does not match schema/legislation.schema.json", output)

    def test_a_problem_is_reported_once(self):
        code, output = self.run_validator([changed(STATE, {"signatories": "28"})])
        self.assertEqual(code, 1, output)
        self.assertIn("1 problem(s) found", output)
        self.assertNotIn("does not match schema", output)

    def test_good_record_passes_both_layers(self):
        code, output = self.run_validator([STATE])
        self.assertEqual(code, 0, output)

    def test_a_schema_the_checker_cannot_read_fails_loudly(self):
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp, "legislation.schema.json")
            broken.write_text(json.dumps({"$defs": {"stateRecord": {"maxLength": 3}}}), encoding="utf-8")
            code, output = self.run_validator([STATE], schema_path=broken)
            self.assertEqual(code, 1, output)
            self.assertIn("unsupported schema keyword", output)

            missing = Path(tmp, "nowhere.json")
            code, output = self.run_validator([STATE], schema_path=missing)
            self.assertEqual(code, 1, output)
            self.assertIn("cannot read as JSON", output)


@unittest.skipIf(jsonschema is None, "the optional jsonschema package is not installed")
class AgainstJsonschemaLibraryTests(unittest.TestCase):
    """Compare the small checker with a full implementation, when one is available."""

    def library_rejects(self, value, definition):
        wrapper = {"$schema": SCHEMA["$schema"], "$defs": SCHEMA["$defs"], "$ref": f"#/$defs/{definition}"}
        return not jsonschema.Draft202012Validator(wrapper).is_valid(value)

    def test_the_schema_is_a_valid_schema(self):
        jsonschema.Draft202012Validator.check_schema(SCHEMA)

    def test_same_verdict_on_every_case_in_the_table(self):
        # END_OF_STRING is left out: the jsonschema package uses Python patterns,
        # where "$" also matches before a final newline. The standard, and
        # validate.py, follow JavaScript.
        for change in BOTH + VALIDATOR_ONLY + NEITHER:
            record = changed(STATE, change)
            with self.subTest(change=describe(change)):
                self.assertEqual(bool(errors(record, "stateRecord")), self.library_rejects(record, "stateRecord"))
        for filename, change in PER_FILE:
            definition, base = BASES[filename]
            record = changed(base, change)
            with self.subTest(file=filename, change=describe(change)):
                self.assertEqual(bool(errors(record, definition)), self.library_rejects(record, definition))

    def test_same_verdict_on_the_real_data(self):
        for filename, definition in FILE_DEFS.items():
            data = json.loads((ROOT / "data" / filename).read_text(encoding="utf-8"))
            self.assertFalse(self.library_rejects(data, definition), filename)
            self.assertEqual(errors(data, definition), [])


if __name__ == "__main__":
    unittest.main()
