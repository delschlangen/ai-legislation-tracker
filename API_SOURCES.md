# API Data Sources

This document describes the APIs used to fetch AI legislation updates.

## Quick Start

```bash
# Run with Federal Register only (no API key needed)
python src/update_tracker.py

# Run with all sources (requires API keys)
export CONGRESS_API_KEY="your-key"
export LEGISCAN_API_KEY="your-key"
python src/update_tracker.py --all

# Optionally enhance with Claude summaries
export ANTHROPIC_API_KEY="your-key"
python src/update_tracker.py --all --summarize
```

---

## Data Sources

### 1. Federal Register API

**Status:** No API key required

The Federal Register is the official daily publication for rules, proposed rules, and notices of federal agencies and organizations, as well as executive orders and other presidential documents.

| Detail | Value |
|:-------|:------|
| API Docs | https://www.federalregister.gov/developers/documentation/api/v1 |
| Cost | Free |
| Rate Limit | 1,000 requests/day |
| Key Required | No |

**What it tracks:**
- Executive orders
- Final rules and regulations
- Proposed rules
- Agency notices and guidance

**Usage:**
```bash
python src/federal_register.py --days 90 --output results.json
```

---

### 2. Congress.gov API

**Status:** Free API key required

The official API for the United States Congress, providing access to legislation, members, and congressional activity.

| Detail | Value |
|:-------|:------|
| API Docs | https://api.congress.gov/ |
| Sign Up | https://api.congress.gov/sign-up/ |
| Cost | Free |
| Rate Limit | 5,000 requests/hour |
| Key Required | Yes |

**What it tracks:**
- Bills introduced in Congress (HR, S, etc.)
- Bill status and actions
- Sponsors and cosponsors
- Committee activity

**Usage:**
```bash
export CONGRESS_API_KEY="your-api-key"
python src/congress_gov.py --congress 118 --output results.json
```

---

### 3. LegiScan API

**Status:** Free tier available (30k queries/month)

LegiScan provides comprehensive state-level legislation tracking across all 50 states.

| Detail | Value |
|:-------|:------|
| API Docs | https://legiscan.com/gaits/documentation/legiscan |
| Sign Up | https://legiscan.com/legiscan |
| Cost | Free tier: 30,000 queries/month |
| Rate Limit | 30,000/month on free tier |
| Key Required | Yes |

**What it tracks:**
- State bills across all 50 states
- Bill status and actions
- Bill text and amendments
- Votes and roll calls

**Usage:**
```bash
export LEGISCAN_API_KEY="your-api-key"

# Search specific states
python src/legiscan.py --state CA --output results.json

# Search multiple states
python src/legiscan.py --states "CA,NY,TX,CO" --output results.json
```

---

### 4. Claude API (Optional)

**Status:** API key required, pay-per-use

Used to automatically summarize legislation and extract key provisions.

| Detail | Value |
|:-------|:------|
| API Docs | https://docs.anthropic.com/claude/reference |
| Sign Up | https://console.anthropic.com/ |
| Cost | Pay per token |
| Key Required | Yes |

**What it does:**
- Generates 1-3 sentence summaries
- Extracts 3-6 key provisions
- Analyzes legislative text

**Usage:**
```bash
export ANTHROPIC_API_KEY="your-api-key"
python src/summarize.py --input new_bills.json --output summarized.json
```

---

## Search Terms

All APIs search for these AI-related terms:

- artificial intelligence
- machine learning
- algorithm / algorithmic
- automated decision
- generative AI
- facial recognition
- deepfake
- large language model

---

## Output Format

All scripts output JSON matching the tracker's schema:

```json
{
  "id": "fed-fr-2024-12345",
  "title": "AI Risk Management Requirements",
  "type": "regulation",
  "status": "active",
  "date_issued": "2024-12-01",
  "summary": "...",
  "key_provisions": ["...", "..."],
  "source_url": "https://...",
  "tags": ["ai", "safety", "federal"],
  "last_verified": "2024-12-24",
  "_source": "federal_register_api"
}
```

---

## Workflow

1. **Fetch new items:**
   ```bash
   python src/update_tracker.py --all --days 30
   ```

2. **Review output in `.cache/` directory**

3. **Copy relevant items to data files:**
   - Federal items → `data/us_federal_actions.json`
   - State items → `data/us_state_bills.json`

4. **Regenerate dashboard:**
   ```bash
   python src/generate_dashboard.py
   ```

5. **Update GitHub Pages data:**
   ```bash
   # Rebuild docs/data.js with new items
   ```

---

## Rate Limits & Best Practices

| API | Limit | Recommendation |
|:----|:------|:---------------|
| Federal Register | 1,000/day | Run weekly |
| Congress.gov | 5,000/hour | Run daily OK |
| LegiScan | 30,000/month | Run weekly, limit states |
| Claude | Pay per use | Only for final items |

**Tips:**
- Start with `--dry-run` to see what would be found
- Use `--days 30` for regular updates instead of 90
- For LegiScan, focus on active AI legislation states
- Only use Claude summarization for items you'll keep

---

## Environment Variables

```bash
# Required for Congress.gov
export CONGRESS_API_KEY="your-key"

# Required for LegiScan
export LEGISCAN_API_KEY="your-key"

# Optional for summarization
export ANTHROPIC_API_KEY="your-key"
```

You can add these to your shell profile (`~/.bashrc`, `~/.zshrc`) or create a `.env` file (don't commit it).
