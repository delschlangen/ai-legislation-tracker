#!/usr/bin/env python3
"""
update_tracker.py

Main orchestrator script to fetch AI legislation updates from multiple sources
and update the tracker's JSON data files.

Sources:
- Federal Register API (free, no key) - federal rulemaking
- Congress.gov API (free, key required) - congressional bills
- LegiScan API (free tier, key required) - state legislation

Usage:
    # Run with no API keys (Federal Register only)
    python update_tracker.py

    # Run with all sources
    export CONGRESS_API_KEY="your-key"
    export LEGISCAN_API_KEY="your-key"
    python update_tracker.py --all

    # Optionally enhance with Claude summaries
    export ANTHROPIC_API_KEY="your-key"
    python update_tracker.py --all --summarize
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Import our API modules
try:
    from federal_register import search_federal_register, format_for_tracker as format_federal
    from congress_gov import search_all_ai_bills, format_for_tracker as format_congress
    from legiscan import search_all_states, format_for_tracker as format_legiscan
    from summarize import process_legislation_batch
except ImportError:
    # Handle running from project root
    sys.path.insert(0, str(Path(__file__).parent))
    from federal_register import search_federal_register, format_for_tracker as format_federal
    from congress_gov import search_all_ai_bills, format_for_tracker as format_congress
    from legiscan import search_all_states, format_for_tracker as format_legiscan
    from summarize import process_legislation_batch


# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
CACHE_DIR = SCRIPT_DIR.parent / ".cache"


def ensure_dirs():
    """Ensure required directories exist."""
    CACHE_DIR.mkdir(exist_ok=True)


def load_existing_data() -> dict:
    """Load existing tracker data."""
    data = {
        "federal": [],
        "state": [],
        "international": []
    }

    federal_path = DATA_DIR / "us_federal_actions.json"
    state_path = DATA_DIR / "us_state_bills.json"
    intl_path = DATA_DIR / "international_frameworks.json"

    if federal_path.exists():
        with open(federal_path) as f:
            data["federal"] = json.load(f)

    if state_path.exists():
        with open(state_path) as f:
            data["state"] = json.load(f)

    if intl_path.exists():
        with open(intl_path) as f:
            data["international"] = json.load(f)

    return data


def get_existing_ids(data: dict) -> set:
    """Get set of all existing IDs to avoid duplicates."""
    ids = set()
    for category in data.values():
        for item in category:
            ids.add(item.get("id", ""))
            # Also track by source URL
            if item.get("source_url"):
                ids.add(item["source_url"])
    return ids


def filter_new_items(items: list[dict], existing_ids: set) -> list[dict]:
    """Filter out items that already exist in the tracker."""
    new_items = []
    for item in items:
        item_id = item.get("id", "")
        source_url = item.get("source_url", "")

        if item_id not in existing_ids and source_url not in existing_ids:
            new_items.append(item)

    return new_items


def fetch_federal_register(days: int = 90) -> list[dict]:
    """Fetch from Federal Register API (no key needed)."""
    print("\n" + "=" * 60)
    print("FEDERAL REGISTER (No API key required)")
    print("=" * 60)

    try:
        raw = search_federal_register(days_back=days)
        formatted = format_federal(raw)
        print(f"Fetched {len(formatted)} AI-related documents")
        return formatted
    except Exception as e:
        print(f"Error fetching from Federal Register: {e}")
        return []


def fetch_congress_gov(congress: int = 118) -> list[dict]:
    """Fetch from Congress.gov API (key required)."""
    print("\n" + "=" * 60)
    print("CONGRESS.GOV (API key required)")
    print("=" * 60)

    api_key = os.environ.get("CONGRESS_API_KEY")
    if not api_key:
        print("Skipping - CONGRESS_API_KEY not set")
        print("Get free key at: https://api.congress.gov/sign-up/")
        return []

    try:
        raw = search_all_ai_bills(api_key, congress)
        formatted = format_congress(raw, api_key)
        print(f"Fetched {len(formatted)} AI-related bills")
        return formatted
    except Exception as e:
        print(f"Error fetching from Congress.gov: {e}")
        return []


def fetch_legiscan(states: list[str] = None) -> list[dict]:
    """Fetch from LegiScan API (key required)."""
    print("\n" + "=" * 60)
    print("LEGISCAN (API key required)")
    print("=" * 60)

    api_key = os.environ.get("LEGISCAN_API_KEY")
    if not api_key:
        print("Skipping - LEGISCAN_API_KEY not set")
        print("Get free key at: https://legiscan.com/legiscan")
        return []

    # Default to most active AI legislation states
    if not states:
        states = ["CA", "NY", "TX", "CO", "IL", "VA", "WA", "MA", "FL", "NJ"]

    try:
        raw = search_all_states(api_key, states)
        formatted = format_legiscan(raw)
        print(f"Fetched {len(formatted)} AI-related state bills")
        return formatted
    except Exception as e:
        print(f"Error fetching from LegiScan: {e}")
        return []


def enhance_with_summaries(items: list[dict]) -> list[dict]:
    """Enhance items with Claude-generated summaries."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Skipping summarization - ANTHROPIC_API_KEY not set")
        return items

    print("\nEnhancing with Claude summaries...")
    return process_legislation_batch(api_key, items)


def save_new_items(items: list[dict], output_path: Path):
    """Save new items to a JSON file."""
    with open(output_path, "w") as f:
        json.dump(items, f, indent=2)
    print(f"Saved {len(items)} items to {output_path}")


def generate_report(federal: list, congress: list, legiscan: list, existing_ids: set) -> str:
    """Generate a summary report of new items found."""
    new_federal = filter_new_items(federal, existing_ids)
    new_congress = filter_new_items(congress, existing_ids)
    new_legiscan = filter_new_items(legiscan, existing_ids)

    report = []
    report.append("\n" + "=" * 60)
    report.append("UPDATE SUMMARY")
    report.append("=" * 60)
    report.append(f"Run date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("")
    report.append(f"Federal Register: {len(new_federal)} new items (of {len(federal)} fetched)")
    report.append(f"Congress.gov:     {len(new_congress)} new items (of {len(congress)} fetched)")
    report.append(f"LegiScan:         {len(new_legiscan)} new items (of {len(legiscan)} fetched)")
    report.append(f"")
    report.append(f"TOTAL NEW ITEMS: {len(new_federal) + len(new_congress) + len(new_legiscan)}")

    if new_federal:
        report.append("\n--- New Federal Items ---")
        for item in new_federal[:5]:
            report.append(f"  - {item.get('title', 'Untitled')[:60]}")
        if len(new_federal) > 5:
            report.append(f"  ... and {len(new_federal) - 5} more")

    if new_congress:
        report.append("\n--- New Congressional Bills ---")
        for item in new_congress[:5]:
            report.append(f"  - {item.get('bill_number', '')}: {item.get('title', 'Untitled')[:50]}")
        if len(new_congress) > 5:
            report.append(f"  ... and {len(new_congress) - 5} more")

    if new_legiscan:
        report.append("\n--- New State Bills ---")
        for item in new_legiscan[:5]:
            report.append(f"  - [{item.get('state_abbrev', '')}] {item.get('bill_number', '')}: {item.get('title', 'Untitled')[:40]}")
        if len(new_legiscan) > 5:
            report.append(f"  ... and {len(new_legiscan) - 5} more")

    return "\n".join(report)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Update AI Legislation Tracker from APIs")
    parser.add_argument("--all", action="store_true", help="Fetch from all available sources")
    parser.add_argument("--federal-only", action="store_true", help="Only fetch Federal Register")
    parser.add_argument("--days", type=int, default=90, help="Days back to search (default: 90)")
    parser.add_argument("--congress", type=int, default=118, help="Congress number (default: 118)")
    parser.add_argument("--states", type=str, help="Comma-separated list of states for LegiScan")
    parser.add_argument("--summarize", action="store_true", help="Enhance with Claude summaries")
    parser.add_argument("--output-dir", type=str, help="Output directory for new items")
    parser.add_argument("--dry-run", action="store_true", help="Don't save anything, just show what would be found")
    args = parser.parse_args()

    ensure_dirs()

    print("AI Legislation Tracker - Update Script")
    print(f"Run date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Load existing data
    existing_data = load_existing_data()
    existing_ids = get_existing_ids(existing_data)
    print(f"\nExisting items in tracker: {sum(len(v) for v in existing_data.values())}")

    # Fetch from sources
    federal_items = []
    congress_items = []
    legiscan_items = []

    # Always fetch Federal Register (no key needed)
    if args.all or args.federal_only or not (os.environ.get("CONGRESS_API_KEY") or os.environ.get("LEGISCAN_API_KEY")):
        federal_items = fetch_federal_register(args.days)

    # Fetch from Congress.gov if key available and requested
    if args.all and not args.federal_only:
        congress_items = fetch_congress_gov(args.congress)

    # Fetch from LegiScan if key available and requested
    if args.all and not args.federal_only:
        states = args.states.split(",") if args.states else None
        legiscan_items = fetch_legiscan(states)

    # Generate report
    report = generate_report(federal_items, congress_items, legiscan_items, existing_ids)
    print(report)

    if args.dry_run:
        print("\n[DRY RUN] No files saved.")
        return

    # Save new items
    output_dir = Path(args.output_dir) if args.output_dir else CACHE_DIR
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    all_new = []

    if federal_items:
        new_federal = filter_new_items(federal_items, existing_ids)
        if new_federal:
            if args.summarize:
                new_federal = enhance_with_summaries(new_federal)
            save_new_items(new_federal, output_dir / f"new_federal_{timestamp}.json")
            all_new.extend(new_federal)

    if congress_items:
        new_congress = filter_new_items(congress_items, existing_ids)
        if new_congress:
            if args.summarize:
                new_congress = enhance_with_summaries(new_congress)
            save_new_items(new_congress, output_dir / f"new_congress_{timestamp}.json")
            all_new.extend(new_congress)

    if legiscan_items:
        new_legiscan = filter_new_items(legiscan_items, existing_ids)
        if new_legiscan:
            if args.summarize:
                new_legiscan = enhance_with_summaries(new_legiscan)
            save_new_items(new_legiscan, output_dir / f"new_legiscan_{timestamp}.json")
            all_new.extend(new_legiscan)

    if all_new:
        save_new_items(all_new, output_dir / f"all_new_{timestamp}.json")

    print(f"\nOutput saved to: {output_dir}")
    print("\nTo add new items to the tracker:")
    print("1. Review the generated JSON files")
    print("2. Copy relevant items to data/us_federal_actions.json or data/us_state_bills.json")
    print("3. Run: python src/generate_dashboard.py")


if __name__ == "__main__":
    main()
