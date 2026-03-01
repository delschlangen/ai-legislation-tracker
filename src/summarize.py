#!/usr/bin/env python3
"""
summarize.py

Use Claude API to summarize legislation and extract key provisions.
Requires API key from: https://console.anthropic.com/

Usage:
    export ANTHROPIC_API_KEY="your-api-key"
    python summarize.py --input new_bills.json --output summarized.json
"""

import json
import os
import sys
import urllib.request
from pathlib import Path


CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"


def get_api_key() -> str:
    """Get API key from environment variable."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        print("Get your key at: https://console.anthropic.com/")
        sys.exit(1)
    return key


def summarize_legislation(api_key: str, title: str, full_text: str) -> dict:
    """
    Use Claude to summarize legislation and extract key provisions.

    Args:
        api_key: Anthropic API key
        title: Legislation title
        full_text: Full text or abstract of legislation

    Returns:
        Dictionary with summary and key_provisions
    """
    prompt = f"""Analyze this legislation and provide:
1. A 1-3 sentence summary explaining what it does and why it matters
2. A list of 3-6 key provisions (requirements, obligations, or significant elements)

Title: {title}

Text: {full_text}

Respond in JSON format:
{{
  "summary": "...",
  "key_provisions": ["...", "...", "..."]
}}"""

    data = {
        "model": MODEL,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}]
    }

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }

    try:
        req = urllib.request.Request(
            CLAUDE_API_URL,
            data=json.dumps(data).encode(),
            headers=headers,
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode())
            content = result.get("content", [{}])[0].get("text", "{}")

            # Parse JSON from response
            try:
                # Handle potential markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                parsed = json.loads(content.strip())
                return {
                    "summary": parsed.get("summary", ""),
                    "key_provisions": parsed.get("key_provisions", [])
                }
            except json.JSONDecodeError:
                return {"summary": content.strip(), "key_provisions": []}

    except Exception as e:
        print(f"  Error calling Claude API: {e}")
        return {"summary": "", "key_provisions": []}


def process_legislation_batch(api_key: str, items: list[dict], text_field: str = "summary") -> list[dict]:
    """
    Process a batch of legislation items, adding summaries and provisions.

    Args:
        api_key: Anthropic API key
        items: List of legislation items
        text_field: Field containing text to summarize

    Returns:
        Updated items with summaries and provisions
    """
    processed = []

    for i, item in enumerate(items):
        title = item.get("title", item.get("name", "Untitled"))
        text = item.get(text_field, "")

        if not text or len(text) < 50:
            print(f"  [{i+1}/{len(items)}] Skipping '{title[:40]}...' (no text)")
            processed.append(item)
            continue

        print(f"  [{i+1}/{len(items)}] Summarizing: {title[:50]}...")

        result = summarize_legislation(api_key, title, text)

        # Update item
        if result.get("summary"):
            item["summary"] = result["summary"]
        if result.get("key_provisions"):
            item["key_provisions"] = result["key_provisions"]

        processed.append(item)

    return processed


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Summarize legislation using Claude API")
    parser.add_argument("--input", type=str, required=True, help="Input JSON file with legislation")
    parser.add_argument("--output", type=str, help="Output JSON file (default: overwrites input)")
    parser.add_argument("--text-field", type=str, default="summary", help="Field containing text to summarize")
    parser.add_argument("--limit", type=int, help="Limit number of items to process")
    args = parser.parse_args()

    api_key = get_api_key()

    # Load input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    with open(input_path) as f:
        items = json.load(f)

    if not isinstance(items, list):
        items = [items]

    if args.limit:
        items = items[:args.limit]

    print(f"Processing {len(items)} items with Claude API...\n")

    # Process
    processed = process_legislation_batch(api_key, items, args.text_field)

    # Output
    output_path = Path(args.output) if args.output else input_path
    with open(output_path, "w") as f:
        json.dump(processed, f, indent=2)

    print(f"\nResults written to {output_path}")


if __name__ == "__main__":
    main()
