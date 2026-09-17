# Contributing to AI Legislation Tracker

Thank you for your interest in helping track AI legislation worldwide. This guide will help you contribute effectively.

## The Easiest Way to Help

**You do not need to know Git or JSON.** If you have spotted something wrong, open an issue:

- [Report an incorrect or out-of-date entry](https://github.com/delschlangen/ai-legislation-tracker/issues/new?template=stale-entry.yml)
- [Suggest a law to add](https://github.com/delschlangen/ai-legislation-tracker/issues/new?template=new-law.yml)

Corrections matter more than additions here. A tracker that is confidently wrong is worse than one that is visibly incomplete.

The rest of this guide is for editing the data directly.

---

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
  "tags": ["relevant", "topic", "tags"],
  "last_verified": "2026-09-17",
  "verification": "primary"
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
  "tags": ["relevant", "tags"],
  "last_verified": "2026-09-17",
  "verification": "primary"
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
  "tags": ["relevant", "tags"],
  "last_verified": "2026-09-17",
  "verification": "primary"
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
| `tags` | Yes | 2-5 relevant topic tags, lowercase with underscores |
| `last_verified` | Yes | `YYYY-MM-DD` date you checked it, or `needs_verification` |
| `verification` | No | `primary`, `secondary` or `unconfirmed` — how you checked it |
| `effective_date` | If enacted | When obligations begin |
| `superseded_by` / `supersedes` | If applicable | The id of the related record |

### Step 4: Valid Status Values

| Status | Use When |
|:-------|:---------|
| `enacted` | Signed into law, has effective date |
| `active` | Currently in effect (frameworks, guidance) |
| `pending` | Introduced but not yet passed |
| `vetoed` | Passed legislature but vetoed |
| `rescinded` | Was active but later revoked |
| `adopted` | International agreements, resolutions |
| `superseded` | Replaced by a later instrument. Set `superseded_by` to its id |
| `expired` | Died without being enacted, or lapsed. For example a bill that died at prorogation |

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

## Superseded and Repealed Law

**Never delete a record and never reuse an id.** When a law is replaced:

1. Set the old record's `status` to `superseded`, `expired` or `rescinded`
2. Add `date_superseded` and `superseded_by` pointing at the successor's id
3. Add `supersedes` on the new record pointing back
4. Rewrite the old summary to say what happened

Colorado `state-001` is the worked example: SB 24-205 was delayed, enforcement-stayed and then repealed before it ever took effect, so it is marked `superseded` and points at `state-011`. Anyone who cited it in 2024 can still resolve that id and see what changed.

---

## Testing Your Changes

```bash
# Run this first. It checks structure, required fields, dates,
# duplicate ids, bare-domain URLs and cross-references.
python3 validate.py

# Confirm your entry appears in queries
python3 src/query_legislation.py --search "your entry title"

# Confirm the dashboard still generates
python3 src/generate_dashboard.py

# Check tag assignment
python3 src/query_legislation.py --list-tags
```

`validate.py` runs automatically on every pull request. It only reads files and
reports what is wrong; it never edits or commits anything. If it fails, the
message names the record and the problem.

The website reads `data/*.json` directly, so there is no second copy to update.
Your entry appears on the site as soon as the change is on `main`.

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
