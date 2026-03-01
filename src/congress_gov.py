#!/usr/bin/env python3
"""
congress_gov.py

Fetch AI-related bills from the Congress.gov API.
Requires free API key from: https://api.congress.gov/sign-up/

API Documentation: https://api.congress.gov/

Usage:
    export CONGRESS_API_KEY="your-api-key"
    python congress_gov.py [--congress 118] [--output results.json]
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path


# AI-related search terms for bills
AI_SEARCH_TERMS = [
    "artificial intelligence",
    "machine learning",
    "algorithm",
    "automated decision",
    "deep learning",
    "generative AI",
    "facial recognition",
    "AI accountability",
    "AI safety",
    "AI transparency"
]

BASE_URL = "https://api.congress.gov/v3"


def get_api_key() -> str:
    """Get API key from environment variable."""
    key = os.environ.get("CONGRESS_API_KEY")
    if not key:
        print("Error: CONGRESS_API_KEY environment variable not set.")
        print("Get a free key at: https://api.congress.gov/sign-up/")
        sys.exit(1)
    return key


def search_bills(
    api_key: str,
    search_term: str,
    congress: int = 118,
    limit: int = 50
) -> list[dict]:
    """
    Search for bills matching a term.

    Args:
        api_key: Congress.gov API key
        search_term: Term to search for
        congress: Congress number (118 = 2023-2024)
        limit: Max results to return

    Returns:
        List of bill dictionaries
    """
    params = {
        "api_key": api_key,
        "format": "json",
        "limit": limit,
        "query": search_term
    }

    url = f"{BASE_URL}/bill/{congress}?" + urllib.parse.urlencode(params)

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            return data.get("bills", [])
    except Exception as e:
        print(f"  Error searching for '{search_term}': {e}")
        return []


def get_bill_details(api_key: str, congress: int, bill_type: str, bill_number: int) -> dict:
    """
    Get detailed information about a specific bill.

    Args:
        api_key: Congress.gov API key
        congress: Congress number
        bill_type: Bill type (hr, s, hjres, sjres, etc.)
        bill_number: Bill number

    Returns:
        Bill details dictionary
    """
    url = f"{BASE_URL}/bill/{congress}/{bill_type}/{bill_number}?api_key={api_key}&format=json"

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            return data.get("bill", {})
    except Exception as e:
        print(f"  Error getting bill details: {e}")
        return {}


def search_all_ai_bills(api_key: str, congress: int = 118) -> list[dict]:
    """
    Search for all AI-related bills across multiple search terms.

    Args:
        api_key: Congress.gov API key
        congress: Congress number

    Returns:
        Deduplicated list of bills
    """
    all_bills = []

    for term in AI_SEARCH_TERMS:
        print(f"Searching for: {term}...")
        bills = search_bills(api_key, term, congress)
        print(f"  Found {len(bills)} bills")
        all_bills.extend(bills)

    # Deduplicate by bill number
    seen = set()
    unique_bills = []
    for bill in all_bills:
        bill_id = f"{bill.get('type', '')}{bill.get('number', '')}"
        if bill_id and bill_id not in seen:
            seen.add(bill_id)
            unique_bills.append(bill)

    print(f"\nTotal unique bills found: {len(unique_bills)}")
    return unique_bills


def format_for_tracker(bills: list[dict], api_key: str = None) -> list[dict]:
    """
    Format Congress.gov bills to match the tracker's JSON schema.

    Args:
        bills: Raw API results
        api_key: Optional API key to fetch additional details

    Returns:
        List of formatted entries
    """
    formatted = []

    for bill in bills:
        bill_type = bill.get("type", "").upper()
        bill_number = bill.get("number", "")
        congress = bill.get("congress", 118)

        # Map status
        latest_action = bill.get("latestAction", {})
        action_text = latest_action.get("text", "").lower()

        if "became public law" in action_text or "signed by president" in action_text:
            status = "enacted"
        elif "passed" in action_text and "senate" in action_text and "house" in action_text:
            status = "passed_both"
        elif "passed" in action_text:
            status = "passed_one_chamber"
        elif "vetoed" in action_text:
            status = "vetoed"
        elif "introduced" in action_text or "referred" in action_text:
            status = "pending"
        else:
            status = "pending"

        # Build URL
        bill_url = f"https://www.congress.gov/bill/{congress}th-congress/{bill_type.lower()}-bill/{bill_number}"

        entry = {
            "id": f"fed-congress-{congress}-{bill_type}{bill_number}",
            "title": bill.get("title", "Untitled"),
            "type": "bill",
            "bill_number": f"{bill_type} {bill_number}",
            "congress": congress,
            "status": status,
            "date_introduced": bill.get("introducedDate"),
            "latest_action": latest_action.get("text", ""),
            "latest_action_date": latest_action.get("actionDate"),
            "summary": "",  # Would need additional API call or Claude
            "key_provisions": [],  # Would need Claude API to extract
            "source_url": bill_url,
            "tags": generate_tags(bill),
            "last_verified": datetime.now().strftime("%Y-%m-%d"),
            "_source": "congress_gov_api"
        }

        # Add sponsor info if available
        if "sponsors" in bill:
            entry["sponsors"] = [s.get("name") for s in bill.get("sponsors", [])]

        formatted.append(entry)

    return formatted


def generate_tags(bill: dict) -> list[str]:
    """Generate relevant tags based on bill content."""
    tags = ["federal", "congress"]

    title = bill.get("title", "").lower()

    tag_keywords = {
        "ai": ["artificial intelligence", " ai ", "ai-", "-ai"],
        "machine_learning": ["machine learning"],
        "algorithm": ["algorithm", "algorithmic"],
        "privacy": ["privacy", "data protection"],
        "discrimination": ["discrimination", "bias", "civil rights"],
        "safety": ["safety", "risk"],
        "transparency": ["transparency", "disclosure", "accountability"],
        "healthcare": ["health", "medical"],
        "employment": ["employment", "hiring", "workforce", "labor"],
        "national_security": ["defense", "national security", "intelligence"],
        "education": ["education", "school", "student"],
        "deepfake": ["deepfake", "synthetic media"],
        "facial_recognition": ["facial recognition", "biometric"]
    }

    for tag, keywords in tag_keywords.items():
        if any(kw in title for kw in keywords):
            tags.append(tag)

    # Determine chamber
    bill_type = bill.get("type", "").upper()
    if bill_type.startswith("S"):
        tags.append("senate")
    elif bill_type.startswith("H"):
        tags.append("house")

    return list(set(tags))


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fetch AI bills from Congress.gov")
    parser.add_argument("--congress", type=int, default=118, help="Congress number (default: 118)")
    parser.add_argument("--output", type=str, help="Output JSON file path")
    parser.add_argument("--raw", action="store_true", help="Output raw API results")
    args = parser.parse_args()

    api_key = get_api_key()

    print(f"Searching Congress.gov for AI-related bills (Congress {args.congress})...\n")

    # Fetch bills
    bills = search_all_ai_bills(api_key, args.congress)

    if not bills:
        print("No bills found.")
        return

    # Format for tracker
    if not args.raw:
        output = format_for_tracker(bills, api_key)
    else:
        output = bills

    # Output
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nResults written to {output_path}")
    else:
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        for bill in output[:15]:  # Show first 15
            print(f"\n{bill.get('bill_number', '')}: {bill.get('title', 'Untitled')[:70]}")
            print(f"  Status: {bill.get('status')}")
            print(f"  Introduced: {bill.get('date_introduced')}")
            print(f"  Latest: {bill.get('latest_action', '')[:60]}")
            print(f"  Tags: {', '.join(bill.get('tags', []))}")

        if len(output) > 15:
            print(f"\n... and {len(output) - 15} more bills")


if __name__ == "__main__":
    main()
