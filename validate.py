#!/usr/bin/env python3
"""
validate.py

Checks the legislation data in data/*.json for structural problems.

This script only READS. It never edits, commits or fetches anything. It prints
what is wrong and exits non-zero so a pull request can fail loudly instead of
merging a malformed entry.

Usage:
    python3 validate.py          # check every file in data/
    python3 validate.py --quiet  # only print problems
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

REQUIRED = ["id", "status", "summary", "key_provisions", "source_url", "tags", "last_verified"]

VALID_STATUS = {
    "enacted", "active", "adopted", "pending",
    "vetoed", "rescinded", "superseded", "expired",
}

VALID_VERIFICATION = {"primary", "secondary", "unconfirmed"}

# Dates may be a real date or the sentinel meaning "nobody has checked this yet".
DATE_SENTINEL = "needs_verification"
DATE_FIELDS = [
    "date_issued", "date_introduced", "date_enacted", "date_adopted",
    "date_effective", "effective_date", "full_application_date",
    "date_rescinded", "date_vetoed", "date_superseded", "date_expired",
    "last_verified",
]

# Fields that must point at another record's id.
CROSS_REFS = ["superseded_by", "supersedes", "amends", "amended_by"]

TAG_RE = re.compile(r"^[a-z0-9_]+$")


def is_valid_date(value):
    if value == DATE_SENTINEL:
        return True
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def is_specific_url(url):
    """Reject bare domains like https://www.sec.gov that cite no document."""
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return False
    remainder = url.split("://", 1)[1]
    path = remainder.split("/", 1)[1] if "/" in remainder else ""
    return bool(path.strip("/")) or "?" in url


def main():
    quiet = "--quiet" in sys.argv
    problems = []
    records = []

    files = sorted(DATA_DIR.glob("*.json"))
    if not files:
        print(f"ERROR: no JSON files found in {DATA_DIR}")
        return 1

    for path in files:
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            problems.append(f"{path.name}: invalid JSON - {exc}")
            continue

        if not isinstance(data, list):
            problems.append(f"{path.name}: expected a list of records")
            continue

        for index, record in enumerate(data):
            records.append((path.name, index, record))

        if not quiet:
            print(f"{path.name}: {len(data)} records")

    seen_ids = {}

    for filename, index, record in records:
        rid = record.get("id", f"{filename}[{index}]")
        where = f"{filename} :: {rid}"

        if not isinstance(record, dict):
            problems.append(f"{where}: record is not an object")
            continue

        for field in REQUIRED:
            if field not in record or record[field] in (None, "", []):
                problems.append(f"{where}: missing required field '{field}'")

        if not (record.get("title") or record.get("name")):
            problems.append(f"{where}: needs a 'title' (or legacy 'name')")

        if "id" in record:
            if record["id"] in seen_ids:
                problems.append(f"{where}: duplicate id, also in {seen_ids[record['id']]}")
            else:
                seen_ids[record["id"]] = filename

        status = record.get("status")
        if status and status not in VALID_STATUS:
            problems.append(
                f"{where}: status '{status}' is not one of {sorted(VALID_STATUS)}")

        verification = record.get("verification")
        if verification and verification not in VALID_VERIFICATION:
            problems.append(
                f"{where}: verification '{verification}' is not one of {sorted(VALID_VERIFICATION)}")

        for field in DATE_FIELDS:
            if field in record and record[field] is not None:
                if not is_valid_date(record[field]):
                    problems.append(
                        f"{where}: '{field}' is '{record[field]}', expected YYYY-MM-DD")

        url = record.get("source_url")
        if url and not is_specific_url(url):
            problems.append(
                f"{where}: source_url '{url}' looks like a bare domain. "
                "Link the specific bill, rule or document.")

        tags = record.get("tags")
        if isinstance(tags, list):
            for tag in tags:
                if not isinstance(tag, str) or not TAG_RE.match(tag):
                    problems.append(
                        f"{where}: tag '{tag}' should be lowercase with underscores")

        provisions = record.get("key_provisions")
        if isinstance(provisions, list) and not provisions:
            problems.append(f"{where}: key_provisions is empty")

    # Cross-references must resolve, and are checked after every id is known.
    for filename, index, record in records:
        where = f"{filename} :: {record.get('id')}"
        for field in CROSS_REFS:
            target = record.get(field)
            if target and target not in seen_ids:
                problems.append(f"{where}: {field} points at unknown id '{target}'")

    if not quiet:
        print(f"\nchecked {len(records)} records across {len(files)} files")

    if problems:
        print(f"\n{len(problems)} problem(s) found:\n")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
