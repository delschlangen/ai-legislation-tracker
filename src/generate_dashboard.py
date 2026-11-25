#!/usr/bin/env python3
"""
generate_dashboard.py

Generates a markdown dashboard summarizing the AI legislation landscape
from the JSON data files.

Usage:
    python3 src/generate_dashboard.py              # print to the terminal
    python3 src/generate_dashboard.py report.md    # write to a file
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Only instruments that are law or policy have dates still to come. A superseded
# or vetoed law's old effective date will never arrive. The website and
# scripts/maintenance_report.py use the same rule.
IN_FORCE_STATUSES = {"enacted", "active", "adopted"}

# One map for every table, so a status never prints with a blank glyph in one
# place and a symbol in another.
STATUS_EMOJI = {
    "enacted": "✅", "active": "✅", "adopted": "✅",
    "pending": "⏳",
    "vetoed": "❌", "rescinded": "❌",
    "superseded": "📦", "expired": "⌛",
    "enjoined": "⚖️",
}


def load_data(data_dir: Path) -> dict:
    """Load all JSON data files, keyed by file name without the extension."""
    data = {}
    for json_file in sorted(data_dir.glob("*.json")):
        with open(json_file, encoding="utf-8") as f:
            data[json_file.stem] = json.load(f)
    return data


def title_of(item: dict) -> str:
    return str(item.get("title") or item.get("name") or "Untitled")


def status_of(item: dict) -> str:
    return str(item.get("status") or "unknown")


def status_cell(item: dict) -> str:
    status = status_of(item)
    emoji = STATUS_EMOJI.get(status, "")
    return f"{emoji} {status}".strip()


def shorten(text: str, limit: int) -> str:
    return text[:limit] + ("..." if len(text) > limit else "")


def md_cell(text) -> str:
    """Make a value safe to place in a markdown table cell."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def is_iso_date(value) -> bool:
    return isinstance(value, str) and bool(DATE_RE.match(value))


def format_status_counts(items: list) -> str:
    """'**Active:** 9 | **Rescinded:** 1', covering every status actually present."""
    counts = Counter(status_of(i) for i in items)
    ordered = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return " | ".join(f"**{status.title()}:** {n}" for status, n in ordered)


def generate_summary_stats(data: dict) -> dict:
    """Calculate summary statistics."""
    federal = data.get("us_federal_actions", [])
    states = data.get("us_state_bills", [])
    international = data.get("international_frameworks", [])

    stats = {
        "federal_actions": len(federal),
        "state_bills": len(states),
        "international": len(international),
    }
    stats["total"] = stats["federal_actions"] + stats["state_bills"] + stats["international"]

    # Tag frequency
    all_tags = []
    for dataset in data.values():
        for item in dataset:
            tags = item.get("tags", [])
            if isinstance(tags, list):
                all_tags.extend(t for t in tags if isinstance(t, str))
    stats["top_tags"] = Counter(all_tags).most_common(10)

    # Verification date range. Only real dates count; the needs_verification
    # sentinel is tallied separately.
    verification_dates = []
    needs_verification_count = 0
    for dataset in data.values():
        for item in dataset:
            last_verified = item.get("last_verified", "")
            if is_iso_date(last_verified):
                verification_dates.append(last_verified)
            elif last_verified == "needs_verification":
                needs_verification_count += 1

    if verification_dates:
        stats["earliest_verified"] = min(verification_dates)
        stats["latest_verified"] = max(verification_dates)
    else:
        stats["earliest_verified"] = None
        stats["latest_verified"] = None
    stats["needs_verification_count"] = needs_verification_count

    return stats


def key_dates(item: dict) -> list:
    """(date, what happens) for every dated stage of a record."""
    dates = []
    for milestone in item.get("milestones") or []:
        if isinstance(milestone, dict) and is_iso_date(milestone.get("date")):
            dates.append((milestone["date"], str(milestone.get("description") or "")))
    recorded = {d for d, _ in dates}
    for field, label in (("effective_date", "Takes effect"), ("full_application_date", "Applies in full")):
        when = item.get(field)
        if is_iso_date(when) and when not in recorded:
            dates.append((when, label))
            recorded.add(when)
    return sorted(dates)


def upcoming_effective_dates(data: dict, today: str, limit: int = 10) -> list:
    """(date, jurisdiction, title, what happens) still in the future, soonest first."""
    upcoming = []
    for filename, jurisdiction_of in (
        ("us_federal_actions", lambda i: "US Federal"),
        ("us_state_bills", lambda i: i.get("state") or "—"),
        ("international_frameworks", lambda i: i.get("jurisdiction") or "—"),
    ):
        for item in data.get(filename, []):
            if status_of(item).lower() not in IN_FORCE_STATUSES:
                continue
            for when, what in key_dates(item):
                if when > today:
                    upcoming.append((when, jurisdiction_of(item), title_of(item), what))
    return sorted(upcoming)[:limit]


def generate_dashboard(data: dict, stats: dict) -> str:
    """Generate the markdown dashboard."""
    federal = data.get("us_federal_actions", [])
    states = data.get("us_state_bills", [])
    international = data.get("international_frameworks", [])

    lines = []

    # Header
    lines.append("# AI Legislation Landscape Dashboard")
    lines.append(f"\n**Report generated:** {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"\n**Total Items Tracked:** {stats['total']}")

    # Verification date range
    if stats.get("earliest_verified") and stats.get("latest_verified"):
        if stats["earliest_verified"] == stats["latest_verified"]:
            lines.append(f"\n**Data Verified:** {stats['latest_verified']}")
        else:
            lines.append(f"\n**Data Verified:** {stats['earliest_verified']} to {stats['latest_verified']}")
    if stats.get("needs_verification_count", 0) > 0:
        lines.append(f" ({stats['needs_verification_count']} entries need verification)")
    lines.append("\n")

    # Summary stats
    lines.append("## Overview\n")
    lines.append("| Category | Count |")
    lines.append("|----------|-------|")
    lines.append(f"| US Federal Actions | {stats['federal_actions']} |")
    lines.append(f"| US State Bills | {stats['state_bills']} |")
    lines.append(f"| International Frameworks | {stats['international']} |")

    # US Federal
    lines.append("\n## US Federal Actions\n")
    lines.append(f"{format_status_counts(federal)}\n")
    lines.append("| Title | Type | Status | Issuing Body |")
    lines.append("|-------|------|--------|--------------|")
    for item in federal:
        lines.append(
            f"| {md_cell(shorten(title_of(item), 50))} | {md_cell(item.get('type', '—'))} "
            f"| {status_cell(item)} | {md_cell(item.get('issuing_body', '—'))} |")

    # US States
    lines.append("\n## US State Legislation\n")
    lines.append(f"{format_status_counts(states)}\n")
    lines.append("| State | Bill | Title | Status | Effective |")
    lines.append("|-------|------|-------|--------|-----------|")
    for item in states:
        lines.append(
            f"| {md_cell(item.get('state', '—'))} | {md_cell(item.get('bill_number', '—'))} "
            f"| {md_cell(shorten(title_of(item), 35))} | {status_cell(item)} "
            f"| {md_cell(item.get('effective_date', '—'))} |")

    # International
    lines.append("\n## International Frameworks\n")
    lines.append(f"{format_status_counts(international)}\n")
    lines.append("| Jurisdiction | Name | Type | Status |")
    lines.append("|--------------|------|------|--------|")
    for item in international:
        lines.append(
            f"| {md_cell(item.get('jurisdiction', '—'))} | {md_cell(shorten(title_of(item), 40))} "
            f"| {md_cell(item.get('type', '—'))} | {status_cell(item)} |")

    # Key themes
    lines.append("\n## Key Themes (by tag frequency)\n")
    lines.append("| Tag | Occurrences |")
    lines.append("|-----|-------------|")
    for tag, count in stats["top_tags"]:
        lines.append(f"| `{tag}` | {count} |")

    # Timeline of key dates
    lines.append("\n## Upcoming Effective Dates\n")
    lines.append("| Date | Jurisdiction | Item | What happens |")
    lines.append("|------|--------------|------|--------------|")
    today = datetime.now().strftime("%Y-%m-%d")
    for date, jurisdiction, title, what in upcoming_effective_dates(data, today):
        lines.append(f"| {date} | {md_cell(jurisdiction)} | {md_cell(title[:50])} | {md_cell(what)} |")

    # Footer
    lines.append("\n---")
    lines.append("*Generated by generate_dashboard.py*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate a markdown dashboard from data/*.json.")
    parser.add_argument("output", nargs="?", help="write to this file instead of the terminal")
    args = parser.parse_args()

    # The report contains emoji. Without this, a console using a legacy code page
    # (common on Windows) raises UnicodeEncodeError instead of printing.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    data_dir = Path(__file__).parent.parent / "data"

    if not data_dir.exists():
        print(f"ERROR: Data directory not found at {data_dir}", file=sys.stderr)
        return 1

    data = load_data(data_dir)

    if not data:
        print("ERROR: No data files found", file=sys.stderr)
        return 1

    stats = generate_summary_stats(data)
    dashboard = generate_dashboard(data, stats)

    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(dashboard)
        print(f"Dashboard written to {output_path}")
    else:
        print(dashboard)
    return 0


if __name__ == "__main__":
    sys.exit(main())
