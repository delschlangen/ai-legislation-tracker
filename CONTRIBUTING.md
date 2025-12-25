# Contributing to AI Legislation Tracker

Thank you for your interest in helping track AI legislation worldwide. This guide will help you contribute effectively.

## Ways to Contribute

| Contribution Type | Difficulty | Impact |
|:------------------|:-----------|:-------|
| Add new legislation | Easy | High |
| Update existing entries | Easy | High |
| Fix inaccuracies | Easy | High |
| Add missing source URLs | Easy | Medium |
| Improve tag coverage | Easy | Medium |
| Enhance query tool features | Medium | Medium |
| Add new data visualizations | Medium | Medium |

---

## Adding New Legislation

### Step 1: Choose the Right Data File

| File | Use For |
|:-----|:--------|
| `data/us_federal_actions.json` | Executive orders, agency guidance, federal regulations |
| `data/us_state_bills.json` | State legislation, local ordinances (e.g., NYC) |
| `data/international_frameworks.json` | Non-US laws, multi-national agreements, principles |

### Step 2: Copy an Existing Entry as Template

For state legislation:
```json
{
  "id": "state-011",
  "state": "Virginia",
  "bill_number": "HB 1234",
  "title": "Official Bill Title Here",
  "status": "enacted",
  "date_introduced": "2025-01-15",
  "date_enacted": "2025-06-01",
  "effective_date": "2026-01-01",
  "summary": "One to three sentences describing the legislation's purpose and scope.",
  "key_provisions": [
    "First key requirement or provision",
    "Second key requirement or provision",
    "Third key requirement or provision"
  ],
  "source_url": "https://official-government-source.gov/bill",
  "tags": ["relevant", "topic", "tags"]
}
```

For federal actions:
```json
{
  "id": "fed-009",
  "title": "Official Title Here",
  "type": "executive_order",
  "status": "active",
  "date_issued": "2025-01-15",
  "issuing_body": "Agency Name",
  "summary": "One to three sentences describing the action.",
  "key_provisions": [
    "First key requirement",
    "Second key requirement"
  ],
  "source_url": "https://official-source.gov",
  "tags": ["relevant", "tags"]
}
```

For international:
```json
{
  "id": "intl-011",
  "jurisdiction": "Country or Organization",
  "name": "Official Name Here",
  "type": "regulation",
  "status": "enacted",
  "date_adopted": "2025-01-15",
  "date_effective": "2025-07-01",
  "summary": "One to three sentences describing the framework.",
  "key_provisions": [
    "First key provision",
    "Second key provision"
  ],
  "source_url": "https://official-source.gov",
  "tags": ["relevant", "tags"]
}
```

### Step 3: Required Fields

| Field | Required | Notes |
|:------|:--------:|:------|
| `id` | Yes | Unique ID like `state-011`, `fed-009`, `intl-011` |
| `title` or `name` | Yes | Official name of legislation |
| `status` | Yes | See status values below |
| `summary` | Yes | 1-3 sentences, factual, neutral tone |
| `key_provisions` | Yes | Array of 3-6 main requirements |
| `source_url` | Yes | Link to official government source |
| `tags` | Yes | 2-5 relevant topic tags |

### Step 4: Valid Status Values

| Status | Use When |
|:-------|:---------|
| `enacted` | Signed into law, has effective date |
| `active` | Currently in effect (frameworks, guidance) |
| `pending` | Introduced but not yet passed |
| `vetoed` | Passed legislature but vetoed |
| `rescinded` | Was active but later revoked |
| `adopted` | International agreements, resolutions |

### Step 5: Use Existing Tags When Possible

**Topic Tags:**
- `comprehensive` — Broad regulation covering multiple sectors
- `frontier_ai` — Advanced/frontier AI systems
- `genai` — Generative AI specific
- `employment` — Hiring, workplace AI
- `discrimination` — Algorithmic bias prevention
- `safety` — Safety requirements, testing
- `disclosure` — Transparency requirements
- `high_risk` — High-risk AI system rules

**Type Tags:**
- `principles` — Non-binding principles
- `voluntary` — Voluntary frameworks
- `binding` — Legally binding regulations

**Jurisdiction Tags:**
- `china`, `eu`, `uk`, `canada`, `brazil`
- `international` — Multi-national
- `local` — City/local ordinances

---

## Updating Existing Entries

When legislation status changes (enacted, vetoed, rescinded):

1. Update the `status` field
2. Add relevant date field (`date_enacted`, `date_vetoed`, `date_rescinded`)
3. If vetoed, add `veto_reason` field with brief explanation
4. Update `summary` if needed

Example:
```json
"status": "vetoed",
"date_vetoed": "2025-03-15",
"veto_reason": "Governor cited concerns about implementation timeline"
```

---

## Verification Checklist

Before submitting:

- [ ] Entry is valid JSON (no trailing commas, proper quotes)
- [ ] `id` is unique (check existing entries)
- [ ] `source_url` links to official government source
- [ ] `summary` is factual and neutral (no advocacy)
- [ ] `key_provisions` has 3-6 items
- [ ] Tags use existing tags where applicable
- [ ] Run `python src/generate_dashboard.py` to verify no errors

---

## Quality Standards

### Do

- Use official bill/law titles
- Link to primary government sources
- Write neutral, factual summaries
- Include effective dates for enacted legislation
- Use consistent date format: YYYY-MM-DD

### Don't

- Add opinion or advocacy language
- Link to news articles as primary source
- Include speculation about future legislation
- Add entries for legislation still being drafted

---

## Testing Your Changes

```bash
# Verify JSON is valid and dashboard generates
python src/generate_dashboard.py

# Verify your entry appears in queries
python src/query_legislation.py --search "your entry title"

# Check tag assignment
python src/query_legislation.py --list-tags
```

---

## Submitting

1. Fork the repository
2. Create a branch: `git checkout -b add-virginia-hb1234`
3. Make your changes
4. Test with `python src/generate_dashboard.py`
5. Commit: `git commit -m "Add Virginia HB 1234: AI Transparency Requirements"`
6. Push and open a Pull Request

Include in your PR description:
- What legislation you're adding/updating
- Link to official source
- Any notes about the entry

---

## Questions?

Open an issue for:
- Clarification on whether legislation belongs in the tracker
- Questions about data structure
- Suggestions for new features
- Reporting inaccuracies

---

Thank you for helping maintain accurate AI legislation tracking.
