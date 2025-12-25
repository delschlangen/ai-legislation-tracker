#!/usr/bin/env python3
"""
query_legislation.py

Simple CLI to query the AI legislation database.

Usage:
    python query_legislation.py --tag employment
    python query_legislation.py --status enacted
    python query_legislation.py --jurisdiction California
    python query_legislation.py --search "frontier"
    python query_legislation.py --list-tags
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict


def load_all_data(data_dir: Path) -> List[Dict]:
    """Load and merge all JSON data files."""
    all_items = []
    
    for json_file in data_dir.glob("*.json"):
        with open(json_file) as f:
            items = json.load(f)
            # Add source file info
            for item in items:
                item["_source"] = json_file.stem
            all_items.extend(items)
    
    return all_items


def filter_by_tag(items: List[Dict], tag: str) -> List[Dict]:
    """Filter items by tag."""
    return [i for i in items if tag.lower() in [t.lower() for t in i.get("tags", [])]]


def filter_by_status(items: List[Dict], status: str) -> List[Dict]:
    """Filter items by status."""
    return [i for i in items if i.get("status", "").lower() == status.lower()]


def filter_by_jurisdiction(items: List[Dict], jurisdiction: str) -> List[Dict]:
    """Filter items by jurisdiction/state."""
    results = []
    for item in items:
        j = item.get("jurisdiction", item.get("state", item.get("issuing_body", "")))
        if jurisdiction.lower() in j.lower():
            results.append(item)
    return results


def search_text(items: List[Dict], query: str) -> List[Dict]:
    """Full-text search across key fields."""
    results = []
    query = query.lower()
    
    for item in items:
        searchable = " ".join([
            str(item.get("title", "")),
            str(item.get("name", "")),
            str(item.get("summary", "")),
            " ".join(item.get("key_provisions", [])),
            " ".join(item.get("tags", []))
        ]).lower()
        
        if query in searchable:
            results.append(item)
    
    return results


def get_all_tags(items: List[Dict]) -> Dict[str, int]:
    """Get all unique tags with counts."""
    tags = {}
    for item in items:
        for tag in item.get("tags", []):
            tags[tag] = tags.get(tag, 0) + 1
    return dict(sorted(tags.items(), key=lambda x: -x[1]))


def format_item(item: Dict) -> str:
    """Format a single item for display."""
    lines = []
    
    # Title/name
    title = item.get("title") or item.get("name")
    lines.append(f"\n{'='*60}")
    lines.append(f"📋 {title}")
    lines.append(f"{'='*60}")
    
    # Jurisdiction
    jurisdiction = item.get("jurisdiction") or item.get("state") or item.get("issuing_body")
    if jurisdiction:
        lines.append(f"📍 Jurisdiction: {jurisdiction}")
    
    # Status
    status = item.get("status", "unknown")
    status_emoji = {"enacted": "✅", "active": "✅", "vetoed": "❌", "pending": "⏳", "rescinded": "❌"}.get(status, "")
    lines.append(f"📊 Status: {status_emoji} {status}")
    
    # Type
    if item.get("type"):
        lines.append(f"📁 Type: {item['type']}")
    
    # Dates
    if item.get("date_enacted"):
        lines.append(f"📅 Enacted: {item['date_enacted']}")
    if item.get("date_adopted"):
        lines.append(f"📅 Adopted: {item['date_adopted']}")
    if item.get("effective_date"):
        lines.append(f"📅 Effective: {item['effective_date']}")
    
    # Summary
    if item.get("summary"):
        lines.append(f"\n📝 Summary:\n   {item['summary']}")
    
    # Key provisions
    if item.get("key_provisions"):
        lines.append(f"\n🔑 Key Provisions:")
        for provision in item["key_provisions"][:5]:
            lines.append(f"   • {provision}")
        if len(item["key_provisions"]) > 5:
            lines.append(f"   • ... and {len(item['key_provisions']) - 5} more")
    
    # Tags
    if item.get("tags"):
        lines.append(f"\n🏷️  Tags: {', '.join(item['tags'])}")
    
    # Source URL
    if item.get("source_url"):
        lines.append(f"\n🔗 {item['source_url']}")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Query AI legislation database")
    parser.add_argument("--tag", "-t", help="Filter by tag")
    parser.add_argument("--status", "-s", help="Filter by status (enacted, pending, vetoed, active)")
    parser.add_argument("--jurisdiction", "-j", help="Filter by jurisdiction/state")
    parser.add_argument("--search", "-q", help="Full-text search")
    parser.add_argument("--list-tags", action="store_true", help="List all tags with counts")
    parser.add_argument("--count", action="store_true", help="Show only count, not details")
    
    args = parser.parse_args()
    
    # Find data directory
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data"
    
    if not data_dir.exists():
        print(f"ERROR: Data directory not found at {data_dir}")
        return
    
    # Load data
    items = load_all_data(data_dir)
    print(f"Loaded {len(items)} items from {data_dir}\n")
    
    # List tags mode
    if args.list_tags:
        tags = get_all_tags(items)
        print("Available tags:\n")
        for tag, count in tags.items():
            print(f"  {tag}: {count}")
        return
    
    # Apply filters
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
    
    # Output
    if args.count:
        print(f"\nTotal matching items: {len(results)}")
    else:
        for item in results:
            print(format_item(item))
        
        print(f"\n{'='*60}")
        print(f"Total: {len(results)} items")


if __name__ == "__main__":
    main()
