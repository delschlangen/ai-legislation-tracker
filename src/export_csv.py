#!/usr/bin/env python3
"""
export_csv.py

Flattens data/*.json into a single CSV for spreadsheet and BI use.

The CSV is generated on demand and deliberately NOT committed, so there is only
ever one copy of the data to keep correct. Regenerate it whenever you need it.

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

COLUMNS = [
    "id", "jurisdiction_type", "jurisdiction", "bill_number", "title", "type",
    "status", "date_introduced", "date_enacted", "date_issued", "date_adopted",
    "effective_date", "date_superseded", "superseded_by", "supersedes",
    "summary", "key_provisions", "tags", "source_url",
    "last_verified", "verification",
]


def load_records():
    records = []
    for path in sorted(DATA_DIR.glob("*.json")):
        jtype = JURISDICTION_TYPE.get(path.stem, path.stem)
        for record in json.loads(path.read_text()):
            flat = dict(record)
            flat["jurisdiction_type"] = jtype
            flat["title"] = record.get("title") or record.get("name", "")
            flat["jurisdiction"] = (
                record.get("state")
                or record.get("jurisdiction")
                or ("US Federal" if jtype == "federal" else "")
            )
            # Lists become pipe-delimited so a single cell stays readable.
            flat["key_provisions"] = " | ".join(record.get("key_provisions", []))
            flat["tags"] = " | ".join(record.get("tags", []))
            records.append(flat)
    return records


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "ai_legislation.csv"
    records = load_records()

    if target == "-":
        writer = csv.DictWriter(sys.stdout, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
        return 0

    with open(target, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

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
