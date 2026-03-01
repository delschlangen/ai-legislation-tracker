#!/usr/bin/env python3
"""
Fetch AI-related state legislation from OpenStates API.

OpenStates provides free access to state legislature data.
Get your free API key at: https://openstates.org/accounts/signup/

Usage:
    python fetch_openstates.py

Environment:
    OPENSTATES_API_KEY: Your OpenStates API key (optional for limited queries)
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

OPENSTATES_API_URL = "https://v3.openstates.org/graphql"

# AI-related search terms
AI_SEARCH_TERMS = [
    "artificial intelligence",
    "machine learning",
    "algorithmic",
    "automated decision",
    "facial recognition",
    "deepfake",
]

# States we're most interested in (active AI legislation)
PRIORITY_STATES = [
    "CA", "CO", "CT", "IL", "NY", "TX", "UT", "TN", "WA", "VA", "MA", "NJ"
]


def fetch_bills(api_key: str, state: str, search_term: str, session: str = None) -> list:
    """Fetch bills from OpenStates GraphQL API."""

    headers = {"X-API-KEY": api_key} if api_key else {}

    query = """
    query($state: String!, $searchQuery: String!, $first: Int!) {
        bills(
            jurisdiction: $state
            searchQuery: $searchQuery
            first: $first
            sort: "updated_desc"
        ) {
            edges {
                node {
                    id
                    identifier
                    title
                    classification
                    subject
                    updatedAt
                    createdAt
                    legislativeSession {
                        identifier
                        name
                    }
                    fromOrganization {
                        name
                    }
                    abstracts {
                        abstract
                    }
                    actions {
                        description
                        date
                        classification
                    }
                    sources {
                        url
                    }
                }
            }
        }
    }
    """

    variables = {
        "state": state.lower(),
        "searchQuery": search_term,
        "first": 25
    }

    try:
        response = requests.post(
            OPENSTATES_API_URL,
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            print(f"  API errors: {data['errors']}")
            return []

        bills = data.get("data", {}).get("bills", {}).get("edges", [])
        return [edge["node"] for edge in bills]

    except requests.exceptions.RequestException as e:
        print(f"  Request error for {state}: {e}")
        return []


def determine_status(actions: list) -> str:
    """Determine bill status from actions."""
    if not actions:
        return "pending"

    action_text = " ".join([a.get("description", "").lower() for a in actions])
    classifications = []
    for a in actions:
        classifications.extend(a.get("classification", []))

    if "became-law" in classifications or "signed" in action_text or "enacted" in action_text:
        return "enacted"
    if "governor-veto" in classifications or "vetoed" in action_text:
        return "vetoed"
    if "passage" in classifications:
        return "active"  # Passed one chamber

    return "pending"


def transform_bill(bill: dict, state: str) -> dict:
    """Transform OpenStates bill to our schema."""

    # Get abstract/summary
    abstracts = bill.get("abstracts", [])
    summary = abstracts[0]["abstract"] if abstracts else bill.get("title", "")

    # Get source URL
    sources = bill.get("sources", [])
    source_url = sources[0]["url"] if sources else ""

    # Determine status
    status = determine_status(bill.get("actions", []))

    # Get dates from actions
    actions = bill.get("actions", [])
    date_introduced = None
    date_enacted = None
    effective_date = None

    for action in actions:
        action_date = action.get("date")
        classifications = action.get("classification", [])

        if "introduction" in classifications and not date_introduced:
            date_introduced = action_date
        if "became-law" in classifications:
            date_enacted = action_date

    # Generate unique ID
    bill_id = f"openstates-{state.lower()}-{bill['identifier'].replace(' ', '-').lower()}"

    return {
        "id": bill_id,
        "state": state,
        "bill_number": bill.get("identifier", ""),
        "title": bill.get("title", ""),
        "status": status,
        "date_introduced": date_introduced,
        "date_enacted": date_enacted,
        "effective_date": effective_date,
        "summary": summary[:500] if summary else "",  # Truncate long summaries
        "key_provisions": [],  # Would need NLP to extract
        "source_url": source_url,
        "tags": ["openstates", "ai"],
        "last_verified": datetime.now().strftime("%Y-%m-%d"),
        "data_source": "openstates"
    }


def fetch_all_state_bills(api_key: str) -> list:
    """Fetch AI-related bills from all priority states."""
    all_bills = []
    seen_ids = set()

    for state in PRIORITY_STATES:
        print(f"Fetching bills for {state}...")

        for term in AI_SEARCH_TERMS[:3]:  # Limit searches to avoid rate limits
            bills = fetch_bills(api_key, state, term)

            for bill in bills:
                bill_key = f"{state}-{bill['identifier']}"
                if bill_key not in seen_ids:
                    seen_ids.add(bill_key)
                    transformed = transform_bill(bill, state)
                    all_bills.append(transformed)

        print(f"  Found {len([b for b in all_bills if b['state'] == state])} unique bills")

    return all_bills


def main():
    api_key = os.environ.get("OPENSTATES_API_KEY", "")

    if not api_key:
        print("Warning: No OPENSTATES_API_KEY set. API may be rate limited.")
        print("Get a free key at: https://openstates.org/accounts/signup/")
        print()

    print("Fetching AI-related state legislation from OpenStates...")
    print("=" * 50)

    bills = fetch_all_state_bills(api_key)

    print()
    print(f"Total bills found: {len(bills)}")

    # Save to file
    output_path = Path(__file__).parent.parent / "data" / "openstates_bills.json"
    with open(output_path, "w") as f:
        json.dump(bills, f, indent=2)

    print(f"Saved to: {output_path}")

    # Print summary by state
    print()
    print("Bills by state:")
    from collections import Counter
    state_counts = Counter(b["state"] for b in bills)
    for state, count in state_counts.most_common():
        print(f"  {state}: {count}")


if __name__ == "__main__":
    main()
