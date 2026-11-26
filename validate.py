#!/usr/bin/env python3
"""
validate.py

Checks the legislation data in data/*.json for structural problems.

This script only READS. It never edits, commits or fetches anything. It prints
what is wrong and exits non-zero so a pull request can fail loudly instead of
merging a malformed entry.

Two layers:

1. Its own checks, which give messages a contributor can act on.
2. schema/legislation.schema.json. A record that passes layer 1 is then checked
   against the schema, so nothing the schema rejects can pass here, and the two
   cannot drift apart.

It also enforces what a schema cannot express: real calendar dates, duplicate
ids, mutual supersession and amendment links, milestones in date order, a
phased law's first milestone matching effective_date, and the hand-written
change log in data/meta/changelog.json, which the website shows as "Recently
changed".

Usage:
    python3 validate.py          # check every file in data/
    python3 validate.py --quiet  # only print problems
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
SCHEMA_PATH = ROOT / "schema" / "legislation.schema.json"
CHANGELOG_NAME = "meta/changelog.json"

# Required in every record, in every file.
REQUIRED = ["id", "title", "status", "summary", "key_provisions", "source_url", "tags", "last_verified"]

# Required in addition, per file. A file not listed here gets only the common rules.
REQUIRED_BY_FILE = {
    "us_federal_actions.json": ["type", "issuing_body", "date_issued"],
    "us_state_bills.json": ["state", "bill_number"],
    "international_frameworks.json": ["jurisdiction", "type"],
}

# Every id in a file must start with this prefix, so an id says where it lives.
ID_PREFIX_BY_FILE = {
    "us_federal_actions.json": "fed-",
    "us_state_bills.json": "state-",
    "international_frameworks.json": "intl-",
}

# The schema definition each file's records are checked against.
SCHEMA_DEF_BY_FILE = {
    "us_federal_actions.json": "federalRecord",
    "us_state_bills.json": "stateRecord",
    "international_frameworks.json": "internationalRecord",
}

VALID_STATUS = {
    "enacted", "active", "adopted", "pending",
    "vetoed", "rescinded", "superseded", "expired", "enjoined",
}

VALID_VERIFICATION = {"primary", "secondary", "unconfirmed"}

# Fields that must be present when a record has a given status.
REQUIRED_BY_STATUS = {
    "superseded": ["superseded_by"],
    "vetoed": ["veto_reason"],
    "enjoined": ["injunction"],
}

# Every field a record may carry. Anything else is reported, which catches a
# misspelling such as "efective_date" that would otherwise be silently ignored.
KNOWN_FIELDS = {
    "id", "title", "type", "status", "state", "bill_number", "jurisdiction", "issuing_body",
    "date_issued", "date_introduced", "date_enacted", "date_adopted", "effective_date",
    "full_application_date", "date_rescinded", "date_vetoed", "date_superseded",
    "date_expired", "date_enjoined", "milestones",
    "superseded_by", "supersedes", "amends", "amended_by", "veto_reason", "injunction",
    "summary", "key_provisions", "covered_decisions", "principles", "signatories", "enforcement",
    "source_url", "tags", "last_verified", "verification",
}

# Fields that were renamed. A record still using one gets told the new name.
RETIRED_FIELDS = {"name": "title", "date_effective": "effective_date"}

# Fields that hold one piece of text, and fields that hold a list of them.
STRING_FIELDS = [
    "title", "summary", "type", "state", "bill_number", "jurisdiction", "issuing_body",
    "veto_reason", "injunction",
]
STRING_LIST_FIELDS = ["covered_decisions", "principles"]

# Only last_verified may say "nobody has checked this yet". Every other date
# field must be a real date.
DATE_SENTINEL = "needs_verification"
DATE_FIELDS = [
    "date_issued", "date_introduced", "date_enacted", "date_adopted",
    "effective_date", "full_application_date",
    "date_rescinded", "date_vetoed", "date_superseded", "date_expired",
    "date_enjoined", "last_verified",
]
# ASCII digits only: \d would also accept digits from other scripts.
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
ID_RE = re.compile(r"(fed|state|intl)-[0-9]{3,}")

# Fields that must point at another record's id, and the field the target must
# point back with. A link recorded in only one direction leaves the other record
# silent about its own history.
RECIPROCAL = {
    "superseded_by": "supersedes",
    "supersedes": "superseded_by",
    "amends": "amended_by",
    "amended_by": "amends",
}

TAG_RE = re.compile(r"[a-z0-9_]+")


def is_valid_date(value, field):
    """YYYY-MM-DD, zero-padded, and a real calendar date."""
    if field == "last_verified" and value == DATE_SENTINEL:
        return True
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


# Characters that never belong in a URL as written: ASCII controls and the
# space, DEL and the C1 controls, and every character JavaScript's trim()
# removes. The site trims a link before using it, so "https://www.ftc.gov/ "
# would quietly become the agency's homepage.
URL_FORBIDDEN = re.compile("[\x00-\x20\x7f-\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]")


def is_specific_url(url):
    """Reject bare domains like https://www.sec.gov that cite no document.

    The URL needs a path segment or a query string. A fragment does not count,
    so "https://www.sec.gov/#main-content" is still the homepage, and
    whitespace or control characters are refused outright.

    The source_url pattern in the schema expresses the same rule;
    tests/test_schema.py checks the two agree."""
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return False
    if URL_FORBIDDEN.search(url):
        return False
    remainder = url.split("://", 1)[1].split("#", 1)[0]
    before_query, _, query = remainder.partition("?")
    path = before_query.split("/", 1)[1] if "/" in before_query else ""
    return bool(path.strip("/")) or bool(query)


def is_text(value):
    return isinstance(value, str) and bool(value.strip())


# ---------------------------------------------------------------------------
# Layer 2: the schema
# ---------------------------------------------------------------------------

# The project has no dependencies, so this is a small checker for the parts of
# JSON Schema (draft 2020-12) that schema/legislation.schema.json uses. A
# keyword outside these two sets raises instead of being silently ignored, so
# the schema cannot grow a rule that nothing enforces.
SCHEMA_RULES = {
    "$ref", "type", "enum", "const", "pattern", "minLength", "minItems", "required",
    "properties", "additionalProperties", "items", "allOf", "anyOf", "if", "then",
    "dependentRequired",
}
SCHEMA_ANNOTATIONS = {"$schema", "$id", "$defs", "title", "description"}

_JSON_TYPES = {
    "string": lambda v: isinstance(v, str),
    # JSON Schema counts 28.0 as an integer; Python's bool is not a number here.
    "integer": lambda v: (isinstance(v, int) and not isinstance(v, bool))
               or (isinstance(v, float) and v.is_integer()),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "null": lambda v: v is None,
}


class SchemaError(ValueError):
    """The schema itself uses something this checker does not implement."""


def _json_equal(a, b):
    """Equality as JSON Schema defines it, at any depth: true is not 1, and a
    list or object equals only one with equal members, but 1 and 1.0 are the
    same number."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, list) or isinstance(b, list):
        return (isinstance(a, list) and isinstance(b, list) and len(a) == len(b)
                and all(_json_equal(x, y) for x, y in zip(a, b)))
    if isinstance(a, dict) or isinstance(b, dict):
        return (isinstance(a, dict) and isinstance(b, dict) and set(a) == set(b)
                and all(_json_equal(a[key], b[key]) for key in a))
    return a == b


def _python_pattern(pattern):
    """A JSON Schema pattern, written for Python's re module.

    Schema patterns follow JavaScript, where "$" means the very end. In Python
    "$" also matches before a final newline, so a final "$" becomes \\Z. A "$"
    anchor anywhere else would need the same care inside the pattern, so it is
    refused rather than checked wrongly. Escapes and character classes are
    followed, so "\\$" and "[$]" stay literal and "\\\\$" is still an anchor."""
    out = []
    escaped = in_class = False
    class_start = -1
    for index, char in enumerate(pattern):
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif in_class:
            # A "]" straight after "[" or "[^" is a literal, as in Python.
            if char == "]" and index > class_start:
                in_class = False
        elif char == "[":
            in_class = True
            class_start = index + 1
            if pattern[index + 1:index + 2] == "^":
                class_start += 1
        elif char == "$":
            if index != len(pattern) - 1:
                raise SchemaError(f"a '$' anchor is supported only at the end of a pattern, not in {pattern!r}")
            out.append(r"\Z")
            continue
        out.append(char)
    return "".join(out)


def _pattern_matches(pattern, value):
    return re.search(_python_pattern(pattern), value) is not None


def _resolve(ref, root):
    if not ref.startswith("#/"):
        raise SchemaError(f"only local references are supported, not {ref!r}")
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def schema_errors(value, schema, root, path="$"):
    """Problems found checking `value` against `schema`; an empty list means valid."""
    unsupported = set(schema) - SCHEMA_RULES - SCHEMA_ANNOTATIONS
    if unsupported:
        raise SchemaError(f"unsupported schema keyword(s) {sorted(unsupported)} at {path}")

    found = []
    if "$ref" in schema:
        found += schema_errors(value, _resolve(schema["$ref"], root), root, path)
    if "type" in schema:
        is_type = _JSON_TYPES.get(schema["type"]) if isinstance(schema["type"], str) else None
        if is_type is None:
            raise SchemaError(f"unsupported type {schema['type']!r} at {path}")
        if not is_type(value):
            return found + [f"{path}: expected {schema['type']}, got {type(value).__name__}"]
    if "enum" in schema and not any(_json_equal(value, option) for option in schema["enum"]):
        found.append(f"{path}: {value!r} is not one of {schema['enum']}")
    if "const" in schema and not _json_equal(value, schema["const"]):
        found.append(f"{path}: {value!r} is not {schema['const']!r}")
    if isinstance(value, str):
        if "pattern" in schema and not _pattern_matches(schema["pattern"], value):
            found.append(f"{path}: {value!r} does not match the pattern {schema['pattern']}")
        if "minLength" in schema and len(value) < schema["minLength"]:
            found.append(f"{path}: is empty")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            found.append(f"{path}: needs at least {schema['minItems']} item(s)")
        if "items" in schema:
            for index, item in enumerate(value):
                found += schema_errors(item, schema["items"], root, f"{path}[{index}]")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                found.append(f"{path}: missing {key}")
        for key, needed in schema.get("dependentRequired", {}).items():
            if key in value:
                for other in needed:
                    if other not in value:
                        found.append(f"{path}: {key} needs {other}")
        properties = schema.get("properties", {})
        for key, sub in properties.items():
            if key in value:
                found += schema_errors(value[key], sub, root, f"{path}.{key}")
        if "additionalProperties" in schema:
            if schema["additionalProperties"] is not False:
                raise SchemaError(f"additionalProperties must be false at {path}")
            for key in value:
                if key not in properties:
                    found.append(f"{path}: unexpected property {key}")
    for sub in schema.get("allOf", []):
        found += schema_errors(value, sub, root, path)
    if "anyOf" in schema and not any(not schema_errors(value, sub, root, path) for sub in schema["anyOf"]):
        found.append(f"{path}: matches none of the allowed forms")
    if "if" in schema and "then" in schema and not schema_errors(value, schema["if"], root, path):
        found += schema_errors(value, schema["then"], root, path)
    return found


def _reject_constant(name):
    raise ValueError(f"{name} is not valid JSON")


def read_json(path):
    """Parse a JSON file the way a browser does. Python's json module accepts
    NaN, Infinity and -Infinity, which are not JSON (RFC 8259); a data file
    holding one passes every check and then fails to load on the site.
    Raises ValueError (which covers bad JSON and bad UTF-8) or OSError."""
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=_reject_constant)


def load_schema(path=None):
    """Returns (schema, problem). Exactly one of the two is None."""
    path = SCHEMA_PATH if path is None else path
    try:
        return read_json(path), None
    except (ValueError, OSError) as exc:
        return None, f"schema/{Path(path).name}: cannot read as JSON - {exc}"


def schema_problems(filename, record, schema):
    """What the schema says about one record, as validator problems."""
    definition = SCHEMA_DEF_BY_FILE.get(filename, "record")
    where = f"{filename} :: {record.get('id', '<no id>')}"
    errors = schema_errors(record, {"$ref": f"#/$defs/{definition}"}, schema)
    return [f"{where}: does not match schema/{SCHEMA_PATH.name} ({error})" for error in errors]


# ---------------------------------------------------------------------------
# Layer 1: checks with messages a contributor can act on
# ---------------------------------------------------------------------------

def check_record(filename, record, problems):
    """Per-record checks. `record` is known to be a dict."""
    where = f"{filename} :: {record.get('id', '<no id>')}"

    # A required field that is absent or empty is reported once, here, and the
    # type checks below then leave it alone.
    missing = set()
    required = REQUIRED + REQUIRED_BY_FILE.get(filename, [])
    for field in required:
        if field not in record or record[field] in (None, "", []):
            problems.append(f"{where}: missing required field '{field}'")
            missing.add(field)

    def present(field):
        return field in record and field not in missing

    for field in sorted(set(record) - KNOWN_FIELDS):
        if field in RETIRED_FIELDS:
            problems.append(
                f"{where}: uses the retired field '{field}'; rename it to '{RETIRED_FIELDS[field]}'")
        else:
            problems.append(
                f"{where}: unknown field '{field}'. Check the spelling, or add it to KNOWN_FIELDS "
                "in validate.py and to schema/legislation.schema.json")

    if present("id"):
        rid = record["id"]
        prefix = ID_PREFIX_BY_FILE.get(filename)
        if not isinstance(rid, str):
            problems.append(f"{where}: id must be a string")
        elif prefix and not re.fullmatch(re.escape(prefix) + r"[0-9]{3,}", rid):
            problems.append(
                f"{where}: id should be '{prefix}' followed by at least three digits "
                f"(for example '{prefix}018') in {filename}")
        elif not prefix and not ID_RE.fullmatch(rid):
            problems.append(f"{where}: id should look like 'state-018'")

    for field in STRING_FIELDS:
        if present(field) and not is_text(record[field]):
            hint = "" if field in required else "; leave the field out if it does not apply"
            problems.append(f"{where}: '{field}' must be text that is not blank{hint}")

    for field in STRING_LIST_FIELDS:
        if field in record:
            value = record[field]
            if not isinstance(value, list) or not all(is_text(item) for item in value):
                problems.append(f"{where}: '{field}' must be a list of non-blank strings")

    if "signatories" in record:
        value = record["signatories"]
        if isinstance(value, bool) or not isinstance(value, int):
            problems.append(f"{where}: 'signatories' must be a whole number, not {value!r}")

    if "enforcement" in record and not isinstance(record["enforcement"], dict):
        problems.append(f"{where}: 'enforcement' must be an object")

    check_milestones(where, record, problems)

    status = record.get("status")
    if present("status") and (not isinstance(status, str) or status not in VALID_STATUS):
        problems.append(f"{where}: status {status!r} is not one of {sorted(VALID_STATUS)}")
    if not isinstance(status, str):
        status = None
    for field in REQUIRED_BY_STATUS.get(status, []):
        if field not in record:
            problems.append(f"{where}: status '{status}' requires '{field}'")

    if "verification" in record:
        verification = record["verification"]
        if not isinstance(verification, str) or verification not in VALID_VERIFICATION:
            problems.append(
                f"{where}: verification {verification!r} is not one of {sorted(VALID_VERIFICATION)}. "
                "Leave the field out if the entry has not been re-checked")

    for field in DATE_FIELDS:
        if present(field) and not is_valid_date(record[field], field):
            hint = "; leave the field out if there is no date" if record[field] is None else ""
            problems.append(
                f"{where}: '{field}' is {record[field]!r}, expected a zero-padded YYYY-MM-DD date{hint}")

    for field in RECIPROCAL:
        if field in record:
            target = record[field]
            if not isinstance(target, str) or not ID_RE.fullmatch(target):
                problems.append(f"{where}: {field} is {target!r}, expected one record id such as 'state-001'")

    if present("source_url") and not is_specific_url(record["source_url"]):
        problems.append(
            f"{where}: source_url {record['source_url']!r} is not a specific http(s) link. "
            "Link the bill, rule or document, not a bare domain.")

    if present("tags"):
        tags = record["tags"]
        if not isinstance(tags, list):
            problems.append(f"{where}: 'tags' must be a list of strings, not {type(tags).__name__}")
        else:
            for tag in tags:
                if not isinstance(tag, str) or not TAG_RE.fullmatch(tag):
                    problems.append(f"{where}: tag {tag!r} should be lowercase letters, digits and underscores")

    if present("key_provisions"):
        provisions = record["key_provisions"]
        if not isinstance(provisions, list):
            problems.append(
                f"{where}: 'key_provisions' must be a list of strings, not {type(provisions).__name__}")
        elif not all(is_text(item) for item in provisions):
            problems.append(f"{where}: key_provisions contains an empty or non-string item")


def check_milestones(where, record, problems):
    """Phased dates: a non-empty list of {date, description}, oldest first, whose
    first date is the record's effective_date."""
    if "milestones" not in record:
        return
    milestones = record["milestones"]
    if not isinstance(milestones, list) or not milestones:
        problems.append(f"{where}: 'milestones' must be a non-empty list")
        return
    dates = []
    well_formed = True
    for index, item in enumerate(milestones):
        label = f"{where}: milestones[{index}]"
        if not isinstance(item, dict):
            problems.append(f"{label} must be an object with 'date' and 'description'")
            well_formed = False
            continue
        extra = sorted(set(item) - {"date", "description"})
        if extra:
            problems.append(f"{label} has unexpected field(s) {extra}; only 'date' and 'description' are allowed")
        if not is_valid_date(item.get("date"), "milestone"):
            problems.append(f"{label} date is {item.get('date')!r}, expected a zero-padded YYYY-MM-DD date")
            well_formed = False
        else:
            dates.append(item["date"])
        if not is_text(item.get("description")):
            problems.append(f"{label} needs a non-empty 'description'")
    if dates != sorted(dates):
        problems.append(f"{where}: milestones must be listed oldest first")
        well_formed = False

    # A phased law keeps its first stage in effective_date. The site's "in force
    # today" rule reads effective_date alone, so the two must not disagree.
    if "effective_date" not in record:
        problems.append(f"{where}: a record with milestones needs effective_date, set to the first milestone's date")
    elif well_formed and is_valid_date(record["effective_date"], "effective_date") \
            and record["effective_date"] != dates[0]:
        problems.append(
            f"{where}: effective_date is {record['effective_date']} but the first milestone is {dates[0]}. "
            "A phased law keeps its first stage in effective_date")


def check_changelog(path, records_by_id, problems):
    """data/meta/changelog.json: newest first, real dates, ids that exist."""
    if not path.exists():
        return
    label = f"meta/{path.name}"
    try:
        entries = read_json(path)
    except (ValueError, OSError) as exc:
        problems.append(f"{label}: cannot read as JSON - {exc}")
        return
    if not isinstance(entries, list):
        problems.append(f"{label}: expected a list of entries")
        return

    previous_date = None
    first_added = {}
    for index, entry in enumerate(entries):
        where = f"{label}[{index}]"
        if not isinstance(entry, dict):
            problems.append(f"{where}: entry is not an object")
            continue
        extra = sorted(set(entry) - {"date", "summary", "added", "updated"})
        if extra:
            problems.append(f"{where}: unexpected field(s) {extra}")
        date = entry.get("date")
        if not is_valid_date(date, "changelog"):
            problems.append(f"{where}: date is {date!r}, expected a zero-padded YYYY-MM-DD date")
        else:
            if previous_date and date > previous_date:
                problems.append(f"{where}: entries must be newest first ({date} comes after {previous_date})")
            previous_date = date
        if not is_text(entry.get("summary")):
            problems.append(f"{where}: needs a non-empty 'summary'")

        ids_seen = set()
        for kind in ("added", "updated"):
            ids = entry.get(kind, [])
            if not isinstance(ids, list):
                problems.append(f"{where}: '{kind}' must be a list of record ids")
                continue
            for rid in ids:
                if not isinstance(rid, str):
                    problems.append(f"{where}: '{kind}' must list record ids as strings, got {rid!r}")
                    continue
                if rid not in records_by_id:
                    problems.append(f"{where}: '{kind}' names unknown id {rid!r}")
                if rid in ids_seen:
                    problems.append(f"{where}: {rid} is listed more than once")
                ids_seen.add(rid)
                if kind == "added":
                    if rid in first_added:
                        problems.append(f"{where}: {rid} is listed as added twice (also {first_added[rid]})")
                    first_added[rid] = where
        if not ids_seen:
            problems.append(f"{where}: name at least one record in 'added' or 'updated'")


def check_cross_references(records_by_id, problems):
    """Every link must resolve, must not point at itself, and must be mutual."""
    for rid, (filename, record) in records_by_id.items():
        where = f"{filename} :: {rid}"
        for field, inverse in RECIPROCAL.items():
            target = record.get(field)
            if not isinstance(target, str) or not ID_RE.fullmatch(target):
                continue  # absent, or already reported by check_record
            if target == rid:
                problems.append(f"{where}: {field} points at itself")
            elif target not in records_by_id:
                problems.append(f"{where}: {field} points at unknown id '{target}'")
            else:
                back = records_by_id[target][1].get(inverse)
                if back != rid:
                    problems.append(
                        f"{where}: {field} -> {target}, but {target} has {inverse} = {back!r}. "
                        f"Add '{inverse}': '{rid}' to {target}.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check data/*.json for structural problems (read-only).")
    parser.add_argument("--quiet", "-q", action="store_true", help="only print problems")
    args = parser.parse_args(argv)
    quiet = args.quiet

    problems = []
    loaded = []  # (filename, index, record)

    files = sorted(DATA_DIR.glob("*.json"))
    if not files:
        print(f"ERROR: no JSON files found in {DATA_DIR}")
        return 1

    schema, schema_problem = load_schema()
    if schema_problem:
        problems.append(schema_problem)

    for path in files:
        try:
            data = read_json(path)
        except (ValueError, OSError) as exc:
            problems.append(f"{path.name}: cannot read as JSON - {exc}")
            continue

        if not isinstance(data, list):
            problems.append(f"{path.name}: expected a list of records")
            continue

        for index, record in enumerate(data):
            loaded.append((path.name, index, record))

        if not quiet:
            print(f"{path.name}: {len(data)} records")

    records_by_id = {}

    for filename, index, record in loaded:
        if not isinstance(record, dict):
            problems.append(f"{filename}[{index}]: record is not an object")
            continue

        found = []
        check_record(filename, record, found)
        # The schema is the backstop: it only speaks when this script's own
        # checks found nothing, so a problem is never reported twice.
        if not found and schema is not None:
            try:
                found = schema_problems(filename, record, schema)
            except (SchemaError, KeyError) as exc:
                problems.append(f"schema/{SCHEMA_PATH.name}: {exc}")
                schema = None
        problems.extend(found)

        rid = record.get("id")
        if isinstance(rid, str):
            if rid in records_by_id:
                problems.append(
                    f"{filename} :: {rid}: duplicate id, also in {records_by_id[rid][0]}")
            else:
                records_by_id[rid] = (filename, record)

    # Cross-references and the changelog are checked last, once every id is known.
    check_cross_references(records_by_id, problems)
    check_changelog(DATA_DIR / CHANGELOG_NAME, records_by_id, problems)

    if not quiet:
        print(f"\nchecked {len(loaded)} records across {len(files)} files")

    if problems:
        print(f"\n{len(problems)} problem(s) found:\n")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
