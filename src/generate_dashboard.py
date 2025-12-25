#!/usr/bin/env python3
"""
generate_dashboard.py

Generates a markdown dashboard summarizing the AI legislation landscape
from the JSON data files.

Usage:
    python generate_dashboard.py [output.md]
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter


def load_data(data_dir: Path) -> dict:
    """Load all JSON data files."""
    data = {}
    
    for json_file in data_dir.glob("*.json"):
        with open(json_file) as f:
            data[json_file.stem] = json.load(f)
    
    return data


def generate_summary_stats(data: dict) -> dict:
    """Calculate summary statistics."""
    stats = {
        "federal_actions": len(data.get("us_federal_actions", [])),
        "state_bills": len(data.get("us_state_bills", [])),
        "international": len(data.get("international_frameworks", [])),
        "total": 0
    }
    stats["total"] = stats["federal_actions"] + stats["state_bills"] + stats["international"]
    
    # Status breakdown for state bills
    state_bills = data.get("us_state_bills", [])
    stats["state_enacted"] = sum(1 for b in state_bills if b.get("status") == "enacted")
    stats["state_vetoed"] = sum(1 for b in state_bills if b.get("status") == "vetoed")
    stats["state_pending"] = sum(1 for b in state_bills if b.get("status") == "pending")
    
    # Federal status
    federal = data.get("us_federal_actions", [])
    stats["federal_active"] = sum(1 for f in federal if f.get("status") == "active")
    stats["federal_rescinded"] = sum(1 for f in federal if f.get("status") == "rescinded")
    
    # Tag frequency
    all_tags = []
    for dataset in data.values():
        for item in dataset:
            all_tags.extend(item.get("tags", []))
    stats["top_tags"] = Counter(all_tags).most_common(10)
    
    return stats


def generate_dashboard(data: dict, stats: dict) -> str:
    """Generate the markdown dashboard."""
    
    lines = []
    
    # Header
    lines.append("# AI Legislation Landscape Dashboard")
    lines.append(f"\n**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"\n**Total Items Tracked:** {stats['total']}\n")
    
    # Summary stats
    lines.append("## Overview\n")
    lines.append("| Category | Count |")
    lines.append("|----------|-------|")
    lines.append(f"| US Federal Actions | {stats['federal_actions']} |")
    lines.append(f"| US State Bills | {stats['state_bills']} |")
    lines.append(f"| International Frameworks | {stats['international']} |")
    
    # US Federal
    lines.append("\n## US Federal Actions\n")
    lines.append(f"**Active:** {stats['federal_active']} | **Rescinded:** {stats['federal_rescinded']}\n")
    lines.append("| Title | Type | Status | Issuing Body |")
    lines.append("|-------|------|--------|--------------|")
    
    for item in data.get("us_federal_actions", []):
        status_emoji = "✅" if item["status"] == "active" else "❌"
        lines.append(f"| {item['title'][:50]}{'...' if len(item['title']) > 50 else ''} | {item['type']} | {status_emoji} {item['status']} | {item['issuing_body']} |")
    
    # US States
    lines.append("\n## US State Legislation\n")
    lines.append(f"**Enacted:** {stats['state_enacted']} | **Vetoed:** {stats['state_vetoed']} | **Pending:** {stats['state_pending']}\n")
    lines.append("| State | Bill | Title | Status | Effective |")
    lines.append("|-------|------|-------|--------|-----------|")
    
    for item in data.get("us_state_bills", []):
        status_emoji = {"enacted": "✅", "vetoed": "❌", "pending": "⏳"}.get(item["status"], "")
        effective = item.get("effective_date", "—")
        title_short = item['title'][:35] + ('...' if len(item['title']) > 35 else '')
        lines.append(f"| {item['state']} | {item['bill_number']} | {title_short} | {status_emoji} {item['status']} | {effective} |")
    
    # International
    lines.append("\n## International Frameworks\n")
    lines.append("| Jurisdiction | Name | Type | Status |")
    lines.append("|--------------|------|------|--------|")
    
    for item in data.get("international_frameworks", []):
        status_emoji = {"enacted": "✅", "active": "✅", "pending": "⏳", "adopted": "✅"}.get(item["status"], "")
        name_short = item['name'][:40] + ('...' if len(item['name']) > 40 else '')
        lines.append(f"| {item['jurisdiction']} | {name_short} | {item['type']} | {status_emoji} {item['status']} |")
    
    # Key themes
    lines.append("\n## Key Themes (by tag frequency)\n")
    lines.append("| Tag | Occurrences |")
    lines.append("|-----|-------------|")
    for tag, count in stats["top_tags"]:
        lines.append(f"| `{tag}` | {count} |")
    
    # Timeline of key dates
    lines.append("\n## Upcoming Effective Dates\n")
    lines.append("| Date | Jurisdiction | Item |")
    lines.append("|------|--------------|------|")
    
    upcoming = []
    today = datetime.now().strftime("%Y-%m-%d")
    
    for item in data.get("us_state_bills", []):
        if item.get("effective_date") and item.get("effective_date") > today:
            upcoming.append((item["effective_date"], item["state"], item["title"]))
    
    for item in data.get("international_frameworks", []):
        if item.get("full_application_date") and item.get("full_application_date") > today:
            upcoming.append((item["full_application_date"], item["jurisdiction"], item["name"]))
    
    for date, jurisdiction, title in sorted(upcoming)[:10]:
        lines.append(f"| {date} | {jurisdiction} | {title[:50]} |")
    
    # Footer
    lines.append("\n---")
    lines.append("*Generated by generate_dashboard.py*")
    
    return "\n".join(lines)


def main():
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data"
    
    if not data_dir.exists():
        print(f"ERROR: Data directory not found at {data_dir}")
        sys.exit(1)
    
    # Load data
    data = load_data(data_dir)
    
    if not data:
        print("ERROR: No data files found")
        sys.exit(1)
    
    # Calculate stats
    stats = generate_summary_stats(data)
    
    # Generate dashboard
    dashboard = generate_dashboard(data, stats)
    
    # Output
    if len(sys.argv) > 1:
        output_path = Path(sys.argv[1])
        with open(output_path, "w") as f:
            f.write(dashboard)
        print(f"Dashboard written to {output_path}")
    else:
        print(dashboard)


if __name__ == "__main__":
    main()
