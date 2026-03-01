#!/usr/bin/env python3
"""
legiscan.py

Fetch AI-related state legislation from the LegiScan API.
Requires free API key from: https://legiscan.com/legiscan (30k queries/month free)

API Documentation: https://legiscan.com/gaits/documentation/legiscan

Usage:
    export LEGISCAN_API_KEY="your-api-key"
    python legiscan.py [--state CA] [--output results.json]
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path


# AI-related search terms
AI_SEARCH_TERMS = [
    "artificial intelligence",
    "machine learning",
    "algorithm",
    "automated decision",
    "facial recognition",
    "deepfake",
    "generative AI"
]

# State abbreviations
US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR"
]

# State names for display
STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia", "PR": "Puerto Rico"
}

BASE_URL = "https://api.legiscan.com/"


def get_api_key() -> str:
    """Get API key from environment variable."""
    key = os.environ.get("LEGISCAN_API_KEY")
    if not key:
        print("Error: LEGISCAN_API_KEY environment variable not set.")
        print("Get a free key at: https://legiscan.com/legiscan")
        sys.exit(1)
    return key


def api_request(api_key: str, operation: str, params: dict = None) -> dict:
    """
    Make a request to the LegiScan API.

    Args:
        api_key: LegiScan API key
        operation: API operation name
        params: Additional parameters

    Returns:
        API response dictionary
    """
    params = params or {}
    params["key"] = api_key
    params["op"] = operation

    url = BASE_URL + "?" + urllib.parse.urlencode(params)

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            if data.get("status") == "ERROR":
                print(f"  API Error: {data.get('alert', {}).get('message', 'Unknown error')}")
                return {}
            return data
    except Exception as e:
        print(f"  Request error: {e}")
        return {}


def search_state_bills(api_key: str, state: str, query: str, year: int = 2) -> list[dict]:
    """
    Search for bills in a specific state.

    Args:
        api_key: LegiScan API key
        state: State abbreviation (e.g., "CA")
        query: Search query
        year: Year filter (1=current, 2=recent, 3=prior, 4=all)

    Returns:
        List of bill dictionaries
    """
    result = api_request(api_key, "getSearch", {
        "state": state,
        "query": query,
        "year": year
    })

    search_result = result.get("searchresult", {})

    # Extract bills (keys are numeric indices)
    bills = []
    for key, value in search_result.items():
        if key.isdigit() and isinstance(value, dict):
            value["state"] = state
            bills.append(value)

    return bills


def get_bill_details(api_key: str, bill_id: int) -> dict:
    """
    Get detailed information about a specific bill.

    Args:
        api_key: LegiScan API key
        bill_id: LegiScan bill ID

    Returns:
        Bill details dictionary
    """
    result = api_request(api_key, "getBill", {"id": bill_id})
    return result.get("bill", {})


def search_all_states(api_key: str, states: list[str] = None, terms: list[str] = None) -> list[dict]:
    """
    Search for AI bills across multiple states.

    Args:
        api_key: LegiScan API key
        states: List of state abbreviations (defaults to all states)
        terms: Search terms (defaults to AI_SEARCH_TERMS)

    Returns:
        Deduplicated list of bills
    """
    states = states or US_STATES
    terms = terms or AI_SEARCH_TERMS

    all_bills = []

    for state in states:
        print(f"\nSearching {STATE_NAMES.get(state, state)}...")
        state_bills = []

        for term in terms:
            bills = search_state_bills(api_key, state, term)
            if bills:
                print(f"  '{term}': {len(bills)} bills")
                state_bills.extend(bills)

        # Deduplicate within state
        seen = set()
        for bill in state_bills:
            bill_id = bill.get("bill_id")
            if bill_id and bill_id not in seen:
                seen.add(bill_id)
                all_bills.append(bill)

    print(f"\nTotal bills found: {len(all_bills)}")
    return all_bills


def format_for_tracker(bills: list[dict], api_key: str = None, fetch_details: bool = False) -> list[dict]:
    """
    Format LegiScan bills to match the tracker's JSON schema.

    Args:
        bills: Raw API results
        api_key: Optional API key to fetch additional details
        fetch_details: Whether to fetch full bill details (uses more API quota)

    Returns:
        List of formatted entries matching us_state_bills.json schema
    """
    formatted = []

    # Status mapping from LegiScan status codes
    status_mapping = {
        1: "pending",      # Introduced
        2: "pending",      # Engrossed
        3: "pending",      # Enrolled
        4: "enacted",      # Passed
        5: "vetoed",       # Vetoed
        6: "failed"        # Failed
    }

    for bill in bills:
        state = bill.get("state", "")
        bill_number = bill.get("bill_number", "")

        # Get status
        status_code = bill.get("status")
        if isinstance(status_code, int):
            status = status_mapping.get(status_code, "pending")
        else:
            status = "pending"

        # Fetch additional details if requested
        description = bill.get("title", "")
        if fetch_details and api_key:
            details = get_bill_details(api_key, bill.get("bill_id"))
            if details:
                description = details.get("description", description)

        entry = {
            "id": f"state-legiscan-{bill.get('bill_id', 'unknown')}",
            "state": STATE_NAMES.get(state, state),
            "state_abbrev": state,
            "bill_number": bill_number,
            "title": bill.get("title", "Untitled"),
            "status": status,
            "last_action": bill.get("last_action", ""),
            "last_action_date": bill.get("last_action_date", ""),
            "summary": description,
            "key_provisions": [],  # Would need Claude API
            "source_url": bill.get("url", ""),
            "tags": generate_tags(bill),
            "last_verified": datetime.now().strftime("%Y-%m-%d"),
            "_source": "legiscan_api",
            "_bill_id": bill.get("bill_id"),
            "_relevance": bill.get("relevance", 0)
        }

        formatted.append(entry)

    # Sort by relevance
    formatted.sort(key=lambda x: x.get("_relevance", 0), reverse=True)

    return formatted


def generate_tags(bill: dict) -> list[str]:
    """Generate relevant tags based on bill content."""
    tags = ["state_legislation"]

    title = bill.get("title", "").lower()

    tag_keywords = {
        "ai": ["artificial intelligence", " ai ", "ai-"],
        "machine_learning": ["machine learning"],
        "algorithm": ["algorithm", "algorithmic"],
        "facial_recognition": ["facial recognition", "biometric"],
        "privacy": ["privacy", "data protection"],
        "discrimination": ["discrimination", "bias", "civil rights"],
        "deepfake": ["deepfake", "synthetic media", "digital replica"],
        "transparency": ["transparency", "disclosure"],
        "employment": ["employment", "hiring", "workforce"],
        "healthcare": ["health", "medical"],
        "education": ["education", "school", "student"],
        "law_enforcement": ["law enforcement", "police", "criminal justice"],
        "consumer_protection": ["consumer", "protection"]
    }

    for tag, keywords in tag_keywords.items():
        if any(kw in title for kw in keywords):
            tags.append(tag)

    return list(set(tags))


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fetch AI bills from LegiScan")
    parser.add_argument("--state", type=str, help="Specific state to search (e.g., CA)")
    parser.add_argument("--states", type=str, help="Comma-separated list of states")
    parser.add_argument("--output", type=str, help="Output JSON file path")
    parser.add_argument("--raw", action="store_true", help="Output raw API results")
    parser.add_argument("--details", action="store_true", help="Fetch full bill details (uses more API quota)")
    parser.add_argument("--limit", type=int, default=10, help="Limit number of states to search (for testing)")
    args = parser.parse_args()

    api_key = get_api_key()

    # Determine which states to search
    if args.state:
        states = [args.state.upper()]
    elif args.states:
        states = [s.strip().upper() for s in args.states.split(",")]
    else:
        # Default to searching most active AI legislation states first
        priority_states = ["CA", "NY", "TX", "CO", "IL", "VA", "WA", "MA", "FL", "NJ"]
        states = priority_states[:args.limit]

    print(f"Searching LegiScan for AI-related bills in {len(states)} state(s)...\n")

    # Fetch bills
    bills = search_all_states(api_key, states)

    if not bills:
        print("No bills found.")
        return

    # Format for tracker
    if not args.raw:
        output = format_for_tracker(bills, api_key if args.details else None, args.details)
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
        for bill in output[:20]:  # Show first 20
            print(f"\n[{bill.get('state_abbrev', '')}] {bill.get('bill_number', '')}: {bill.get('title', 'Untitled')[:60]}")
            print(f"  Status: {bill.get('status')}")
            print(f"  Last action: {bill.get('last_action', '')[:50]}")
            print(f"  Tags: {', '.join(bill.get('tags', []))}")

        if len(output) > 20:
            print(f"\n... and {len(output) - 20} more bills")


if __name__ == "__main__":
    main()
