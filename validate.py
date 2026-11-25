#!/usr/bin/env python3
"""
validate.py

Checks the legislation data in data/*.json for structural problems.

This script only READS. It never edits, commits or fetches anything. It prints
what is wrong and exits non-zero so a pull request can fail loudly instead of
merging a malformed entry.

It also checks data/meta/changelog.json, the hand-written log of what changed
and when, which the website shows as "Recently changed".

The field vocabulary here must match schema/legislation.schema.json.
tests/test_schema.py fails if the two drift apart.

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

DATA_DIR = Path(__file__).parent / "data"
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

# Only last_verified may say "nobody has checked this yet". Every other date
# field must be a real date.
DATE_SENTINEL = "needs_verification"
DATE_FIELDS = [
    "date_issued", "date_introduced", "date_enacted", "date_adopted",
    "effective_date", "full_application_date",
    "date_rescinded", "date_vetoed", "date_superseded", "date_expired",
    "date_enjoined", "last_verified",
]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Fields that must point at another record's id, and the field the target must
# point back with. A link recorded in only one direction leaves the other record
# silent about its own history.
RECIPROCAL = {
    "superseded_by": "supersedes",
    "supersedes": "superseded_by",
    "amends": "amended_by",
    "amended_by": "amends",
}

TAG_RE = re.compile(r"^[a-z0-9_]+$")


def is_valid_date(value, field):
    """YYYY-MM-DD, zero-padded, and a real calendar date."""
    if field == "last_verified" and value == DATE_SENTINEL:
        return True
    if not isinstance(value, str) or not DATE_RE.match(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_specific_url(url):
    """Reject bare domains like https://www.sec.gov that cite no document."""
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return False
    remainder = url.split("://", 1)[1]
    path = remainder.split("/", 1)[1] if "/" in remainder else ""
    return bool(path.strip("/")) or "?" in url


def check_record(filename, record, problems):
    """Per-record checks. `record` is known to be a dict."""
    where = f"{filename} :: {record.get('id', '<no id>')}"

    required = REQUIRED + REQUIRED_BY_FILE.get(filename, [])
    for field in required:
        if field not in record or record[field] in (None, "", []):
            problems.append(f"{where}: missing required field '{field}'")

    for field in sorted(set(record) - KNOWN_FIELDS):
        if field in RETIRED_FIELDS:
            problems.append(
                f"{where}: uses the retired field '{field}'; rename it to '{RETIRED_FIELDS[field]}'")
        else:
            problems.append(
                f"{where}: unknown field '{field}'. Check the spelling, or add it to KNOWN_FIELDS "
                "in validate.py and to schema/legislation.schema.json")

    rid = record.get("id")
    if "id" in record:
        prefix = ID_PREFIX_BY_FILE.get(filename)
        if not isinstance(rid, str):
            problems.append(f"{where}: id must be a string")
        elif prefix and not re.fullmatch(re.escape(prefix) + r"\d{3,}", rid):
            problems.append(
                f"{where}: id should be '{prefix}' followed by at least three digits "
                f"(for example '{prefix}018') in {filename}")

    for field in ("title", "summary", "veto_reason", "injunction"):
        if field in record and not isinstance(record[field], str):
            problems.append(f"{where}: '{field}' must be a string")

    check_milestones(where, record, problems)

    status = record.get("status")
    if status is not None and status not in VALID_STATUS:
        problems.append(f"{where}: status '{status}' is not one of {sorted(VALID_STATUS)}")
    for field in REQUIRED_BY_STATUS.get(status, []):
        if not record.get(field):
            problems.append(f"{where}: status '{status}' requires '{field}'")

    verification = record.get("verification")
    if verification is not None and verification not in VALID_VERIFICATION:
        problems.append(
            f"{where}: verification '{verification}' is not one of {sorted(VALID_VERIFICATION)}")

    for field in DATE_FIELDS:
        if field in record and record[field] is not None:
            if not is_valid_date(record[field], field):
                problems.append(
                    f"{where}: '{field}' is {record[field]!r}, expected a zero-padded YYYY-MM-DD date")

    url = record.get("source_url")
    if url and not is_specific_url(url):
        problems.append(
            f"{where}: source_url {url!r} is not a specific http(s) link. "
            "Link the bill, rule or document, not a bare domain.")

    tags = record.get("tags")
    if "tags" in record and tags not in (None, "", []):
        if not isinstance(tags, list):
            problems.append(f"{where}: 'tags' must be a list of strings, not {type(tags).__name__}")
        else:
            for tag in tags:
                if not isinstance(tag, str) or not TAG_RE.match(tag):
                    problems.append(f"{where}: tag {tag!r} should be lowercase letters, digits and underscores")

    provisions = record.get("key_provisions")
    if "key_provisions" in record and provisions not in (None, "", []):
        if not isinstance(provisions, list):
            problems.append(
                f"{where}: 'key_provisions' must be a list of strings, not {type(provisions).__name__}")
        else:
            for item in provisions:
                if not isinstance(item, str) or not item.strip():
                    problems.append(f"{where}: key_provisions contains an empty or non-string item")
                    break


def check_milestones(where, record, problems):
    """Phased dates: a non-empty list of {date, description}, oldest first."""
    if "milestones" not in record:
        return
    milestones = record["milestones"]
    if not isinstance(milestones, list) or not milestones:
        problems.append(f"{where}: 'milestones' must be a non-empty list")
        return
    dates = []
    for index, item in enumerate(milestones):
        label = f"{where}: milestones[{index}]"
        if not isinstance(item, dict):
            problems.append(f"{label} must be an object with 'date' and 'description'")
            continue
        extra = sorted(set(item) - {"date", "description"})
        if extra:
            problems.append(f"{label} has unexpected field(s) {extra}; only 'date' and 'description' are allowed")
        if not is_valid_date(item.get("date"), "milestone"):
            problems.append(f"{label} date is {item.get('date')!r}, expected a zero-padded YYYY-MM-DD date")
        else:
            dates.append(item["date"])
        description = item.get("description")
        if not isinstance(description, str) or not description.strip():
            problems.append(f"{label} needs a non-empty 'description'")
    if dates != sorted(dates):
        problems.append(f"{where}: milestones must be listed oldest first")


def check_changelog(path, records_by_id, problems):
    """data/meta/changelog.json: newest first, real dates, ids that exist."""
    if not path.exists():
        return
    label = f"meta/{path.name}"
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
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
        if not isinstance(entry.get("summary"), str) or not entry.get("summary", "").strip():
            problems.append(f"{where}: needs a non-empty 'summary'")

        ids_seen = set()
        for kind in ("added", "updated"):
            ids = entry.get(kind, [])
            if not isinstance(ids, list):
                problems.append(f"{where}: '{kind}' must be a list of record ids")
                continue
            for rid in ids:
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
            if not target:
                continue
            if not isinstance(target, str):
                problems.append(f"{where}: {field} must be a single record id")
                continue
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

    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
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

        check_record(filename, record, problems)

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
