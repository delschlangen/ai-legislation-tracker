#!/usr/bin/env python3
"""
Fetch AI-related state legislation from LegiScan API.

LegiScan provides 50 free API calls per day.
Get your free API key at: https://legiscan.com/user/register

Usage:
    LEGISCAN_API_KEY=your_key python fetch_legiscan.py
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("Installing requests...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

LEGISCAN_API_URL = "https://api.legiscan.com/"

# AI-related search terms
AI_SEARCH_TERMS = [
    "artificial intelligence",
    "machine learning",
    "algorithmic discrimination",
]

# Map LegiScan status IDs to our status values
STATUS_MAP = {
    1: "pending",      # Introduced
    2: "active",       # Engrossed
    3: "active",       # Enrolled
    4: "enacted",      # Passed
    5: "vetoed",       # Vetoed
    6: "pending",      # Failed/Dead
}


def search_bills(api_key: str, query: str, year: int = 2) -> list:
    """
    Search for bills matching query.
    year: 1=current, 2=recent, 3=prior, 4=all
    """
    params = {
        "key": api_key,
        "op": "search",
        "query": query,
        "year": year,
    }

    try:
        response = requests.get(LEGISCAN_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK":
            results = data.get("searchresult", {})
            # Remove summary key, keep only bill entries
            bills = [v for k, v in results.items() if k.isdigit()]
            return bills
        else:
            print(f"  API error: {data.get('alert', {}).get('message', 'Unknown error')}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"  Request error: {e}")
        return []


def get_bill_details(api_key: str, bill_id: int) -> dict:
    """Get full bill details."""
    params = {
        "key": api_key,
        "op": "getBill",
        "id": bill_id,
    }

    try:
        response = requests.get(LEGISCAN_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK":
            return data.get("bill", {})
        return {}

    except requests.exceptions.RequestException as e:
        print(f"  Error getting bill {bill_id}: {e}")
        return {}


def transform_bill(bill: dict, details: dict = None) -> dict:
    """Transform LegiScan bill to our schema."""

    # Use details if available, otherwise use search result
    if details:
        bill = {**bill, **details}

    # Get state from state_id or state field
    state = bill.get("state", "")

    # Map status
    status_id = bill.get("status", 1)
    status = STATUS_MAP.get(status_id, "pending")

    # Get dates
    date_introduced = bill.get("status_date") or bill.get("last_action_date")

    # Generate unique ID
    bill_id = f"legiscan-{state.lower()}-{bill.get('bill_number', '').replace(' ', '-').lower()}"

    # Get source URL
    source_url = bill.get("url", "") or bill.get("state_link", "")

    return {
        "id": bill_id,
        "state": state,
        "bill_number": bill.get("bill_number", ""),
        "title": bill.get("title", ""),
        "status": status,
        "date_introduced": date_introduced,
        "summary": bill.get("description", bill.get("title", ""))[:500],
        "key_provisions": [],
        "source_url": source_url,
        "tags": ["legiscan", "ai"],
        "last_verified": datetime.now().strftime("%Y-%m-%d"),
        "data_source": "legiscan"
    }


def fetch_all_bills(api_key: str) -> list:
    """Fetch AI-related bills from LegiScan."""
    all_bills = []
    seen_ids = set()

    for term in AI_SEARCH_TERMS:
        print(f"Searching for: {term}")
        bills = search_bills(api_key, term)
        print(f"  Found {len(bills)} results")

        for bill in bills:
            bill_key = f"{bill.get('state')}-{bill.get('bill_number')}"
            if bill_key not in seen_ids:
                seen_ids.add(bill_key)
                transformed = transform_bill(bill)
                all_bills.append(transformed)

    return all_bills


def main():
    api_key = os.environ.get("LEGISCAN_API_KEY", "")

    if not api_key:
        print("Error: LEGISCAN_API_KEY environment variable required")
        print("Get a free key at: https://legiscan.com/user/register")
        print("(50 free API calls per day)")
        sys.exit(1)

    print("Fetching AI-related state legislation from LegiScan...")
    print("=" * 50)

    bills = fetch_all_bills(api_key)

    print()
    print(f"Total unique bills found: {len(bills)}")

    # Save to file
    output_path = Path(__file__).parent.parent / "data" / "legiscan_bills.json"
    with open(output_path, "w") as f:
        json.dump(bills, f, indent=2)

    print(f"Saved to: {output_path}")

    # Print summary by state
    if bills:
        print()
        print("Bills by state:")
        from collections import Counter
        state_counts = Counter(b["state"] for b in bills)
        for state, count in state_counts.most_common(10):
            print(f"  {state}: {count}")


if __name__ == "__main__":
    main()
