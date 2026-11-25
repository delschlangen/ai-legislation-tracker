#!/usr/bin/env python3
"""
export_csv.py

Flattens data/*.json into a single CSV for spreadsheet and BI use.

The CSV is generated on demand and deliberately NOT committed, so there is only
ever one copy of the data to keep correct. Regenerate it whenever you need it.

Every field in the data has a column. A list becomes one pipe-delimited cell,
milestones become "date: description" pairs, and a nested object becomes one
JSON cell. If a record carries a field with no
column, the script says so on stderr instead of dropping it silently.

Usage:
    python3 src/export_csv.py                 # write ai_legislation.csv
    python3 src/export_csv.py out.csv         # write to a given path
    python3 src/export_csv.py -               # write to stdout
"""

import csv
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

JURISDICTION_TYPE = {
    "us_federal_actions": "federal",
    "us_state_bills": "state",
    "international_frameworks": "international",
}

# The first block is the original column order; new columns are appended after
# it so anything already reading this CSV by position keeps working.
COLUMNS = [
    "id", "jurisdiction_type", "jurisdiction", "bill_number", "title", "type",
    "status", "date_introduced", "date_enacted", "date_issued", "date_adopted",
    "effective_date", "date_superseded", "superseded_by", "supersedes",
    "summary", "key_provisions", "tags", "source_url",
    "last_verified", "verification",
    # Added later: fields the data has always carried but the CSV used to drop.
    "issuing_body", "full_application_date",
    "date_vetoed", "veto_reason", "date_rescinded", "date_expired",
    "amended_by", "amends",
    "covered_decisions", "principles", "signatories", "enforcement",
    "milestones", "injunction", "date_enjoined",
]


def flatten(value):
    """One CSV cell per field: lists joined with ' | ', objects as JSON."""
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict) and set(item) == {"date", "description"}:
                parts.append(f"{item['date']}: {item['description']}")
            elif isinstance(item, dict):
                parts.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
            else:
                parts.append(str(item))
        return " | ".join(parts)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def load_records():
    records = []
    for path in sorted(DATA_DIR.glob("*.json")):
        jtype = JURISDICTION_TYPE.get(path.stem, path.stem)
        for record in json.loads(path.read_text(encoding="utf-8")):
            flat = {key: flatten(value) for key, value in record.items()}
            flat["jurisdiction_type"] = jtype
            flat["title"] = record.get("title") or record.get("name", "")
            flat["jurisdiction"] = (
                record.get("state")
                or record.get("jurisdiction")
                or ("US Federal" if jtype == "federal" else "")
            )
            records.append(flat)
    return records


def warn_about_unmapped_fields(records):
    unmapped = sorted({key for record in records for key in record} - set(COLUMNS) - {"state", "name"})
    if unmapped:
        print(
            "WARNING: these fields are in the data but have no CSV column, "
            f"so they were left out: {', '.join(unmapped)}. Add them to COLUMNS in {Path(__file__).name}.",
            file=sys.stderr)


def write_csv(handle, records):
    writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(records)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "ai_legislation.csv"
    if target in ("-h", "--help"):
        print(__doc__)
        return 0

    records = load_records()
    warn_about_unmapped_fields(records)

    if target == "-":
        # UTF-8, and no newline translation: the csv module writes its own \r\n.
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", newline="")
        write_csv(sys.stdout, records)
        return 0

    with open(target, "w", newline="", encoding="utf-8") as handle:
        write_csv(handle, records)

    print(f"Wrote {len(records)} records to {target}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        # Normal when piping into head or less; suppress the interpreter warning.
        try:
            sys.stdout.close()
        except Exception:
            pass
        sys.exit(0)
