"""
Keeps schema/legislation.schema.json and validate.py in agreement, and checks
the real data against the schema. Standard library only.

    python3 -m unittest discover -s tests

The project has no dependencies, so instead of a JSON Schema library this file
carries a small checker for the parts of JSON Schema the schema uses: type,
enum, const, pattern, minLength, minItems, required, properties,
additionalProperties, items, allOf, anyOf, if/then and local $ref.
"""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import validate  # noqa: E402

SCHEMA = json.loads((ROOT / "schema" / "legislation.schema.json").read_text(encoding="utf-8"))

FILE_DEFS = {
    "us_federal_actions.json": "federalFile",
    "us_state_bills.json": "stateFile",
    "international_frameworks.json": "internationalFile",
}

TYPES = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
}


def resolve(ref):
    assert ref.startswith("#/"), ref
    node = SCHEMA
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def errors(value, schema, path="$"):
    """Return a list of human-readable problems; empty means valid."""
    found = []
    if "$ref" in schema:
        found += errors(value, resolve(schema["$ref"]), path)
    if "type" in schema and not TYPES[schema["type"]](value):
        return found + [f"{path}: expected {schema['type']}"]
    if "enum" in schema and value not in schema["enum"]:
        found.append(f"{path}: {value!r} not in enum")
    if "const" in schema and value != schema["const"]:
        found.append(f"{path}: {value!r} is not {schema['const']!r}")
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            found.append(f"{path}: {value!r} does not match {schema['pattern']}")
        if "minLength" in schema and len(value) < schema["minLength"]:
            found.append(f"{path}: too short")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            found.append(f"{path}: needs at least {schema['minItems']} item(s)")
        if "items" in schema:
            for index, item in enumerate(value):
                found += errors(item, schema["items"], f"{path}[{index}]")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                found.append(f"{path}: missing {key}")
        properties = schema.get("properties", {})
        for key, sub in properties.items():
            if key in value:
                found += errors(value[key], sub, f"{path}.{key}")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    found.append(f"{path}: unexpected property {key}")
    for sub in schema.get("allOf", []):
        found += errors(value, sub, path)
    if "anyOf" in schema and not any(not errors(value, sub, path) for sub in schema["anyOf"]):
        found.append(f"{path}: matches none of anyOf")
    if "if" in schema and not errors(value, schema["if"], path) and "then" in schema:
        found += errors(value, schema["then"], path)
    return found


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
        for filename, definition in FILE_DEFS.items():
            record_def = resolve(SCHEMA["$defs"][definition]["items"]["$ref"])
            extra = set(record_def["allOf"][1]["required"])
            self.assertEqual(extra, set(validate.REQUIRED_BY_FILE[filename]), filename)

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


class DataMatchesSchemaTests(unittest.TestCase):
    def test_every_file_validates(self):
        for filename, definition in FILE_DEFS.items():
            data = json.loads((ROOT / "data" / filename).read_text(encoding="utf-8"))
            problems = errors(data, SCHEMA["$defs"][definition])
            self.assertEqual(problems, [], f"{filename}:\n" + "\n".join(problems[:20]))

    def test_root_accepts_every_file(self):
        for filename in FILE_DEFS:
            data = json.loads((ROOT / "data" / filename).read_text(encoding="utf-8"))
            self.assertEqual(errors(data, SCHEMA), [], filename)

    def test_checker_rejects_bad_records(self):
        """The checker above must actually catch problems, or the test proves nothing."""
        state = SCHEMA["$defs"]["stateRecord"]
        good = {"id": "state-001", "state": "X", "bill_number": "HB 1", "title": "T", "status": "enacted",
                "summary": "S", "key_provisions": ["P"], "source_url": "https://example.gov/bill/1",
                "tags": ["t"], "last_verified": "2026-01-01"}
        self.assertEqual(errors(good, state), [])
        for change in ({"status": "maybe"}, {"id": "fed-001"}, {"effective_date": "2026-1-1"},
                       {"efective_date": "2026-01-01"}, {"status": "vetoed"}, {"status": "enjoined"},
                       {"tags": "t"}, {"source_url": "https://example.gov"},
                       {"milestones": [{"date": "2026-01-01"}]}):
            bad = dict(good, **change)
            self.assertNotEqual(errors(bad, state), [], f"accepted {change}")
        missing = dict(good)
        del missing["bill_number"]
        self.assertNotEqual(errors(missing, state), [])


if __name__ == "__main__":
    unittest.main()
