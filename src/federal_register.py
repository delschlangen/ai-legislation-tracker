#!/usr/bin/env python3
"""
federal_register.py

Fetch AI-related documents from the Federal Register API.
Free API, no key required.

API Documentation: https://www.federalregister.gov/developers/documentation/api/v1

Usage:
    python federal_register.py [--days 30] [--output results.json]
"""

import json
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path


# AI-related search terms
AI_SEARCH_TERMS = [
    "artificial intelligence",
    "machine learning",
    "algorithm",
    "automated decision",
    "generative AI",
    "large language model",
    "neural network",
    "deep learning",
    "AI system",
    "algorithmic"
]

# Document types to track
DOCUMENT_TYPES = [
    "RULE",           # Final rules
    "PRORULE",        # Proposed rules
    "NOTICE",         # Notices
    "PRESDOCU"        # Presidential documents (executive orders)
]

# Agencies most likely to issue AI-related documents
PRIORITY_AGENCIES = [
    "Commerce Department",
    "Federal Trade Commission",
    "Securities and Exchange Commission",
    "Department of Defense",
    "Office of Management and Budget",
    "National Institute of Standards and Technology",
    "Department of Health and Human Services",
    "Department of Labor",
    "Consumer Financial Protection Bureau",
    "Equal Employment Opportunity Commission",
    "Department of Homeland Security",
    "Executive Office of the President"
]

BASE_URL = "https://www.federalregister.gov/api/v1/documents.json"


def search_federal_register(
    terms: list[str] = None,
    days_back: int = 90,
    document_types: list[str] = None,
    per_page: int = 100
) -> list[dict]:
    """
    Search the Federal Register for AI-related documents.

    Args:
        terms: Search terms (defaults to AI_SEARCH_TERMS)
        days_back: How many days back to search
        document_types: Document types to include
        per_page: Results per page (max 1000)

    Returns:
        List of document dictionaries
    """
    terms = terms or AI_SEARCH_TERMS
    document_types = document_types or DOCUMENT_TYPES

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    all_results = []

    for term in terms:
        params = {
            "conditions[term]": term,
            "conditions[publication_date][gte]": start_date.strftime("%Y-%m-%d"),
            "conditions[publication_date][lte]": end_date.strftime("%Y-%m-%d"),
            "conditions[type][]": document_types,
            "per_page": per_page,
            "order": "newest",
            "fields[]": [
                "document_number",
                "title",
                "type",
                "abstract",
                "publication_date",
                "effective_on",
                "agencies",
                "html_url",
                "pdf_url",
                "action",
                "dates",
                "citation"
            ]
        }

        # Build URL with proper encoding for arrays
        url_parts = [BASE_URL + "?"]
        for key, value in params.items():
            if isinstance(value, list):
                for v in value:
                    url_parts.append(f"{urllib.parse.quote(key)}={urllib.parse.quote(str(v))}&")
            else:
                url_parts.append(f"{urllib.parse.quote(key)}={urllib.parse.quote(str(value))}&")

        url = "".join(url_parts).rstrip("&")

        try:
            print(f"Searching for: {term}...")
            with urllib.request.urlopen(url, timeout=30) as response:
                data = json.loads(response.read().decode())
                results = data.get("results", [])
                print(f"  Found {len(results)} results")
                all_results.extend(results)
        except Exception as e:
            print(f"  Error searching for '{term}': {e}")

    # Deduplicate by document number
    seen = set()
    unique_results = []
    for doc in all_results:
        doc_num = doc.get("document_number")
        if doc_num and doc_num not in seen:
            seen.add(doc_num)
            unique_results.append(doc)

    print(f"\nTotal unique documents found: {len(unique_results)}")
    return unique_results


def format_for_tracker(documents: list[dict]) -> list[dict]:
    """
    Format Federal Register documents to match the tracker's JSON schema.

    Args:
        documents: Raw API results

    Returns:
        List of formatted entries matching us_federal_actions.json schema
    """
    formatted = []

    for doc in documents:
        # Determine document type
        doc_type = doc.get("type", "").lower()
        type_mapping = {
            "rule": "regulation",
            "proposed rule": "proposed_rule",
            "notice": "notice",
            "presidential document": "executive_order"
        }
        formatted_type = type_mapping.get(doc_type, doc_type)

        # Get agency info
        agencies = doc.get("agencies", [])
        issuing_body = agencies[0].get("name", "Unknown") if agencies else "Unknown"

        # Determine status
        action = doc.get("action", "").lower()
        if "final" in action:
            status = "active"
        elif "proposed" in action or "notice of proposed" in action:
            status = "proposed"
        elif "interim" in action:
            status = "interim"
        else:
            status = "active"

        # Build entry
        entry = {
            "id": f"fed-fr-{doc.get('document_number', 'unknown')}",
            "title": doc.get("title", "Untitled"),
            "type": formatted_type,
            "status": status,
            "date_issued": doc.get("publication_date"),
            "effective_date": doc.get("effective_on"),
            "issuing_body": issuing_body,
            "summary": doc.get("abstract", "No abstract available."),
            "key_provisions": [],  # Would need Claude API to extract
            "source_url": doc.get("html_url", ""),
            "pdf_url": doc.get("pdf_url", ""),
            "citation": doc.get("citation", ""),
            "tags": generate_tags(doc),
            "last_verified": datetime.now().strftime("%Y-%m-%d"),
            "_source": "federal_register_api",
            "_document_number": doc.get("document_number")
        }

        formatted.append(entry)

    return formatted


def generate_tags(doc: dict) -> list[str]:
    """Generate relevant tags based on document content."""
    tags = []

    title = (doc.get("title", "") + " " + doc.get("abstract", "")).lower()

    tag_keywords = {
        "ai": ["artificial intelligence", "ai system", "ai-based"],
        "machine_learning": ["machine learning", "ml model"],
        "algorithm": ["algorithm", "algorithmic"],
        "automated_decision": ["automated decision", "automated system"],
        "disclosure": ["disclosure", "transparency"],
        "privacy": ["privacy", "data protection"],
        "discrimination": ["discrimination", "bias", "fairness"],
        "safety": ["safety", "risk management"],
        "genai": ["generative ai", "large language model", "llm", "chatbot"],
        "healthcare": ["health", "medical", "fda"],
        "finance": ["financial", "securities", "banking"],
        "employment": ["employment", "hiring", "workforce"],
        "export_controls": ["export", "chips", "semiconductor"],
        "enforcement": ["enforcement", "penalty", "violation"]
    }

    for tag, keywords in tag_keywords.items():
        if any(kw in title for kw in keywords):
            tags.append(tag)

    # Add agency-based tags
    agencies = doc.get("agencies", [])
    for agency in agencies:
        agency_name = agency.get("name", "").lower()
        if "ftc" in agency_name or "trade commission" in agency_name:
            tags.append("ftc")
        elif "sec" in agency_name or "securities" in agency_name:
            tags.append("sec")
        elif "commerce" in agency_name:
            tags.append("commerce")
        elif "defense" in agency_name:
            tags.append("dod")

    return list(set(tags)) if tags else ["federal"]


def filter_ai_relevant(documents: list[dict], min_relevance: int = 2) -> list[dict]:
    """
    Filter documents to only include AI-relevant ones.

    Args:
        documents: List of formatted documents
        min_relevance: Minimum number of AI-related tags required

    Returns:
        Filtered list
    """
    ai_tags = {"ai", "machine_learning", "algorithm", "automated_decision", "genai"}

    filtered = []
    for doc in documents:
        doc_tags = set(doc.get("tags", []))
        ai_overlap = len(doc_tags & ai_tags)
        if ai_overlap >= 1:  # At least one AI-related tag
            filtered.append(doc)

    return filtered


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fetch AI documents from Federal Register")
    parser.add_argument("--days", type=int, default=90, help="Days back to search (default: 90)")
    parser.add_argument("--output", type=str, help="Output JSON file path")
    parser.add_argument("--raw", action="store_true", help="Output raw API results")
    args = parser.parse_args()

    print(f"Searching Federal Register for AI-related documents (last {args.days} days)...\n")

    # Fetch documents
    documents = search_federal_register(days_back=args.days)

    if not documents:
        print("No documents found.")
        return

    # Format for tracker
    if not args.raw:
        formatted = format_for_tracker(documents)
        filtered = filter_ai_relevant(formatted)
        output = filtered
        print(f"AI-relevant documents: {len(filtered)}")
    else:
        output = documents

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
        for doc in output[:10]:  # Show first 10
            print(f"\n{doc.get('title', 'Untitled')[:80]}")
            print(f"  Type: {doc.get('type')} | Status: {doc.get('status')}")
            print(f"  Date: {doc.get('date_issued')}")
            print(f"  Agency: {doc.get('issuing_body')}")
            print(f"  Tags: {', '.join(doc.get('tags', []))}")
            print(f"  URL: {doc.get('source_url')}")

        if len(output) > 10:
            print(f"\n... and {len(output) - 10} more documents")


if __name__ == "__main__":
    main()
