#!/usr/bin/env python3
"""
query_legislation.py

Simple CLI to query the AI legislation database.

Usage:
    python3 src/query_legislation.py --tag employment
    python3 src/query_legislation.py --status enacted
    python3 src/query_legislation.py --jurisdiction California
    python3 src/query_legislation.py --jurisdiction federal
    python3 src/query_legislation.py --search "frontier"
    python3 src/query_legislation.py --search "SB 24-205"
    python3 src/query_legislation.py --in-force --jurisdiction California
    python3 src/query_legislation.py --list-tags

Filters combine: each one narrows the results of the one before it.
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List

STATUS_EMOJI = {
    "enacted": "✅", "active": "✅", "adopted": "✅",
    "pending": "⏳",
    "vetoed": "❌", "rescinded": "❌",
    "superseded": "📦", "expired": "⌛",
    "enjoined": "⚖️",
}

# Statuses that mean the instrument is law or policy now, if its date has come.
IN_FORCE_STATUSES = {"enacted", "active", "adopted"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Federal records carry issuing_body but no jurisdiction or state, so the file
# they came from is what says they are federal.
FEDERAL_SOURCE = "us_federal_actions"


def load_all_data(data_dir: Path) -> List[Dict]:
    """Load and merge all JSON data files."""
    all_items = []

    for json_file in sorted(data_dir.glob("*.json")):
        with open(json_file, encoding="utf-8") as f:
            items = json.load(f)
        for item in items:
            item["_source"] = json_file.stem
        all_items.extend(items)

    return all_items


def as_list(value) -> list:
    """Tolerate a missing field or a malformed one; never raise on bad data."""
    return value if isinstance(value, list) else []


def jurisdiction_names(item: Dict) -> List[str]:
    """Every name this record can be found under when filtering by jurisdiction."""
    names = [item.get("state"), item.get("jurisdiction"), item.get("issuing_body")]
    if item.get("_source") == FEDERAL_SOURCE:
        names.append("US Federal")
    return [str(n) for n in names if n]


def is_in_force(item: Dict, today: str) -> bool:
    """In force today: an in-force status, and no effective date still to come.
    The website uses the same rule."""
    if str(item.get("status", "")).lower() not in IN_FORCE_STATUSES:
        return False
    effective = item.get("effective_date")
    return not (isinstance(effective, str) and DATE_RE.match(effective) and effective > today)


def filter_in_force(items: List[Dict], today: str) -> List[Dict]:
    return [i for i in items if is_in_force(i, today)]


def filter_by_tag(items: List[Dict], tag: str) -> List[Dict]:
    """Filter items by tag."""
    wanted = tag.lower()
    return [i for i in items if wanted in [str(t).lower() for t in as_list(i.get("tags"))]]


def filter_by_status(items: List[Dict], status: str) -> List[Dict]:
    """Filter items by status."""
    return [i for i in items if str(i.get("status", "")).lower() == status.lower()]


def filter_by_jurisdiction(items: List[Dict], jurisdiction: str) -> List[Dict]:
    """Filter items by state, jurisdiction or issuing body. Matches part of a name."""
    wanted = jurisdiction.lower()
    return [
        item for item in items
        if any(wanted in name.lower() for name in jurisdiction_names(item))
    ]


def searchable_text(item: Dict) -> str:
    """Everything a search looks through, lower-cased.

    This is the website's search (matchesFilters in docs/app.js) plus one field,
    last_verified, so that `--search needs_verification` finds unchecked entries.
    Keep the two lists in step. Tags and types are searchable as written
    ("frontier_ai") and as displayed ("frontier ai")."""
    tags = [str(t) for t in as_list(item.get("tags"))]
    kind = str(item.get("type") or "")
    parts = (
        [str(item.get(field) or "") for field in (
            "id", "title", "name", "summary", "bill_number", "type",
            "state", "jurisdiction", "issuing_body", "injunction",
            "verification", "last_verified")]
        # Federal records have no jurisdiction field; the site calls them this.
        + (["US Federal"] if item.get("_source") == FEDERAL_SOURCE else [])
        + [str(m.get("description") or "") for m in as_list(item.get("milestones")) if isinstance(m, dict)]
        + [str(p) for p in as_list(item.get("key_provisions"))]
        + tags
        + [t.replace("_", " ") for t in tags + [kind]]
    )
    return " ".join(part for part in parts if part).lower()


def search_text(items: List[Dict], query: str) -> List[Dict]:
    """Full-text search over the fields listed in searchable_text."""
    query = query.lower().strip()
    return [item for item in items if query in searchable_text(item)]


def get_all_tags(items: List[Dict]) -> Dict[str, int]:
    """Get all unique tags with counts."""
    tags = {}
    for item in items:
        for tag in as_list(item.get("tags")):
            tags[tag] = tags.get(tag, 0) + 1
    return dict(sorted(tags.items(), key=lambda x: (-x[1], x[0])))


def format_item(item: Dict) -> str:
    """Format a single item for display."""
    lines = []

    title = item.get("title") or item.get("name") or "Untitled"
    lines.append(f"\n{'='*60}")
    lines.append(f"📋 {title}")
    lines.append(f"{'='*60}")

    if item.get("id"):
        lines.append(f"🆔 {item['id']}")

    names = jurisdiction_names(item)
    if names:
        lines.append(f"📍 Jurisdiction: {names[0]}")

    status = item.get("status", "unknown")
    status_emoji = STATUS_EMOJI.get(status, "")
    lines.append(f"📊 Status: {status_emoji} {status}")

    if item.get("type"):
        lines.append(f"📁 Type: {item['type']}")

    for field, label in (
        ("date_introduced", "Introduced"), ("date_issued", "Issued"), ("date_adopted", "Adopted"),
        ("date_enacted", "Enacted"), ("effective_date", "Effective"),
        ("full_application_date", "Applies in full"), ("date_vetoed", "Vetoed"),
        ("date_enjoined", "Enjoined"), ("date_rescinded", "Rescinded"),
        ("date_superseded", "Superseded"), ("date_expired", "Expired"),
    ):
        if item.get(field):
            lines.append(f"📅 {label}: {item[field]}")

    milestones = [m for m in as_list(item.get("milestones")) if isinstance(m, dict)]
    if milestones:
        lines.append("🗓️  Key dates:")
        for milestone in milestones:
            lines.append(f"   {milestone.get('date', '?')}  {milestone.get('description', '')}")

    if item.get("injunction"):
        lines.append(f"⚖️  Injunction: {item['injunction']}")

    for field, label in (
        ("superseded_by", "Superseded by"), ("supersedes", "Replaces"),
        ("amended_by", "Amended by"), ("amends", "Amends"),
    ):
        if item.get(field):
            lines.append(f"🔁 {label}: {item[field]}")

    if item.get("summary"):
        lines.append(f"\n📝 Summary:\n   {item['summary']}")

    provisions = as_list(item.get("key_provisions"))
    if provisions:
        lines.append("\n🔑 Key Provisions:")
        for provision in provisions[:5]:
            lines.append(f"   • {provision}")
        if len(provisions) > 5:
            lines.append(f"   • ... and {len(provisions) - 5} more")

    tags = as_list(item.get("tags"))
    if tags:
        lines.append(f"\n🏷️  Tags: {', '.join(str(t) for t in tags)}")

    if item.get("verification") or item.get("last_verified"):
        how = item.get("verification", "not recorded")
        lines.append(f"\n🔎 Verified: {item.get('last_verified', 'unknown')} ({how})")

    if item.get("source_url"):
        lines.append(f"🔗 {item['source_url']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Query the AI legislation database. Filters combine.")
    parser.add_argument("--tag", "-t", help="Filter by tag (see --list-tags)")
    parser.add_argument(
        "--status", "-s",
        help="Filter by status: enacted, active, adopted, pending, vetoed, rescinded, superseded, expired, enjoined")
    parser.add_argument(
        "--in-force", action="store_true",
        help="Only records in force today: enacted, active or adopted, with no effective date still to come")
    parser.add_argument(
        "--jurisdiction", "-j",
        help="Filter by state, country, issuing body, or 'federal'. Matches part of a name.")
    parser.add_argument(
        "--search", "-q",
        help="Full-text search across title, summary, provisions, key dates, tags, id, bill number, "
             "jurisdiction and verification (try 'us federal', 'secondary' or 'needs_verification')")
    parser.add_argument("--list-tags", action="store_true", help="List all tags with counts")
    parser.add_argument("--count", action="store_true", help="Show only count, not details")

    args = parser.parse_args()

    # The output contains emoji. Without this, a console using a legacy code page
    # (common on Windows) raises UnicodeEncodeError instead of printing.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    data_dir = Path(__file__).parent.parent / "data"

    if not data_dir.exists():
        print(f"ERROR: Data directory not found at {data_dir}", file=sys.stderr)
        return 1

    items = load_all_data(data_dir)
    print(f"Loaded {len(items)} items from {data_dir}\n")

    if args.list_tags:
        print("Available tags:\n")
        for tag, count in get_all_tags(items).items():
            print(f"  {tag}: {count}")
        return 0

    results = items

    if args.tag:
        results = filter_by_tag(results, args.tag)
        print(f"Filtered by tag '{args.tag}': {len(results)} results")

    if args.status:
        results = filter_by_status(results, args.status)
        print(f"Filtered by status '{args.status}': {len(results)} results")

    if args.jurisdiction:
        results = filter_by_jurisdiction(results, args.jurisdiction)
        print(f"Filtered by jurisdiction '{args.jurisdiction}': {len(results)} results")

    if args.search:
        results = search_text(results, args.search)
        print(f"Search for '{args.search}': {len(results)} results")

    if args.in_force:
        results = filter_in_force(results, date.today().isoformat())
        print(f"In force today: {len(results)} results")

    if args.count:
        print(f"\nTotal matching items: {len(results)}")
    else:
        for item in results:
            print(format_item(item))

        print(f"\n{'='*60}")
        print(f"Total: {len(results)} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
