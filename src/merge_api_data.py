#!/usr/bin/env python3
"""
merge_api_data.py

Merges data fetched from APIs into the main tracker JSON files.
Handles deduplication and updates existing entries.
"""

import json
from datetime import datetime
from pathlib import Path

# Paths
ROOT = Path(__file__).parent.parent
CACHE_DIR = ROOT / ".cache"
DATA_DIR = ROOT / "data"

# Data files
FEDERAL_FILE = DATA_DIR / "us_federal_actions.json"
STATE_FILE = DATA_DIR / "us_state_bills.json"
OPENSTATES_FILE = DATA_DIR / "openstates_bills.json"
LEGISCAN_FILE = DATA_DIR / "legiscan_bills.json"
CACHE_CONGRESS = CACHE_DIR / "congress_gov.json"
CACHE_FEDERAL_REG = CACHE_DIR / "federal_register.json"


def load_json(path: Path) -> list:
    """Load JSON file, return empty list if not found."""
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def save_json(path: Path, data: list):
    """Save data to JSON file with pretty formatting."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {len(data)} entries to {path}")


def merge_entries(existing: list, new_entries: list) -> tuple[list, int]:
    """
    Merge new entries into existing data.
    Updates existing entries if found, adds new ones otherwise.

    Returns:
        Tuple of (merged list, count of new entries added)
    """
    # Index existing by ID
    by_id = {e.get("id"): e for e in existing}
    new_count = 0
    updated_count = 0

    for entry in new_entries:
        entry_id = entry.get("id")
        if not entry_id:
            continue

        if entry_id in by_id:
            # Update existing entry with new data
            old_entry = by_id[entry_id]
            # Keep manual fields, update API fields
            for key in ["status", "latest_action", "latest_action_date", "last_verified"]:
                if key in entry and entry[key]:
                    old_entry[key] = entry[key]
            updated_count += 1
        else:
            # Add new entry
            by_id[entry_id] = entry
            new_count += 1

    print(f"  Updated {updated_count} existing entries")
    print(f"  Added {new_count} new entries")

    return list(by_id.values()), new_count


def main():
    print("Merging API data into tracker...\n")
    today = datetime.now().strftime("%Y-%m-%d")

    # Load existing federal data
    federal_data = load_json(FEDERAL_FILE)
    print(f"Existing federal entries: {len(federal_data)}")

    total_new = 0

    # Merge Congress.gov data
    if CACHE_CONGRESS.exists():
        print("\nMerging Congress.gov data...")
        congress_data = load_json(CACHE_CONGRESS)
        federal_data, new_count = merge_entries(federal_data, congress_data)
        total_new += new_count
    else:
        print("\nNo Congress.gov cache found, skipping...")

    # Merge Federal Register data
    if CACHE_FEDERAL_REG.exists():
        print("\nMerging Federal Register data...")
        fed_reg_data = load_json(CACHE_FEDERAL_REG)
        federal_data, new_count = merge_entries(federal_data, fed_reg_data)
        total_new += new_count
    else:
        print("\nNo Federal Register cache found, skipping...")

    # Merge OpenStates data into state bills
    state_data = load_json(STATE_FILE)
    state_updated = False

    if OPENSTATES_FILE.exists():
        print("\nMerging OpenStates data...")
        openstates_data = load_json(OPENSTATES_FILE)
        print(f"  Existing state entries: {len(state_data)}")
        print(f"  OpenStates entries: {len(openstates_data)}")
        state_data, new_count = merge_entries(state_data, openstates_data)
        total_new += new_count
        state_updated = True
    else:
        print("\nNo OpenStates data found, skipping...")

    # Merge LegiScan data into state bills
    if LEGISCAN_FILE.exists():
        print("\nMerging LegiScan data...")
        legiscan_data = load_json(LEGISCAN_FILE)
        print(f"  LegiScan entries: {len(legiscan_data)}")
        state_data, new_count = merge_entries(state_data, legiscan_data)
        total_new += new_count
        state_updated = True
    else:
        print("\nNo LegiScan data found, skipping...")

    if state_updated:
        save_json(STATE_FILE, state_data)

    # Update last_verified on all entries
    for entry in federal_data:
        if entry.get("_source") in ["congress_gov_api", "federal_register_api"]:
            entry["last_verified"] = today

    # Save merged data
    print(f"\nTotal entries after merge: {len(federal_data)}")
    save_json(FEDERAL_FILE, federal_data)

    # Regenerate docs/data.js for GitHub Pages
    regenerate_docs_data()

    print(f"\nDone! Added {total_new} new entries total.")


def regenerate_docs_data():
    """Regenerate the docs/data.js file from all JSON sources."""
    print("\nRegenerating docs/data.js...")

    all_entries = []

    # Load all data files
    for json_file in DATA_DIR.glob("*.json"):
        data = load_json(json_file)
        all_entries.extend(data)

    # Sort by date (newest first)
    def get_date(entry):
        return entry.get("date_introduced") or entry.get("effective_date") or entry.get("date") or "1900-01-01"

    all_entries.sort(key=get_date, reverse=True)

    # Write as JavaScript
    docs_data = ROOT / "docs" / "data.js"
    with open(docs_data, "w") as f:
        f.write("// Auto-generated from data/*.json files\n")
        f.write(f"// Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
        f.write("const LEGISLATION_DATA = ")
        json.dump(all_entries, f, indent=2)
        f.write(";\n\n")

        # Add helper functions required by app.js
        f.write("""// Helper functions required by app.js
function getAllLegislation() {
  return LEGISLATION_DATA.map(item => {
    let jurisdiction_type;
    if (item.state) {
      jurisdiction_type = 'state';
    } else if (item.issuing_body || item.id?.startsWith('fed-')) {
      jurisdiction_type = 'federal';
    } else {
      jurisdiction_type = 'international';
    }
    return { ...item, jurisdiction_type };
  });
}

function getTagCounts() {
  const tagCounts = {};
  LEGISLATION_DATA.forEach(item => {
    (item.tags || []).forEach(tag => {
      tagCounts[tag] = (tagCounts[tag] || 0) + 1;
    });
  });
  return Object.entries(tagCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);
}
""")

    print(f"  Updated {docs_data} with {len(all_entries)} entries")


if __name__ == "__main__":
    main()
