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
| `data/us_federal_actions.json` | Executive orders, agency guidance, federal regulations, federal statutes |
| `data/us_state_bills.json` | State legislation, local ordinances (e.g., NYC) |
| `data/international_frameworks.json` | Non-US laws, multi-national agreements, principles |

### Step 2: Copy an Existing Entry as Template

Give the new record the next unused id in its file: the highest existing number plus one (`state-018` if the last state record is `state-017`). The `NNN` in the templates below is a placeholder and `validate.py` rejects it until you replace it. Never reuse or renumber an id.

For state legislation:
```json
{
  "id": "state-NNN",
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
  "source_url": "https://official-government-source.gov/path/to/the/bill",
  "tags": ["relevant", "topic", "tags"],
  "last_verified": "2026-09-17",
  "verification": "primary"
}
```

For federal actions:
```json
{
  "id": "fed-NNN",
  "title": "Official Title Here",
  "type": "executive_order",
  "status": "active",
  "date_issued": "2025-01-15",
  "issuing_body": "Agency Name",
  "summary": "One to three sentences describing the action.",
  "key_provisions": [
    "First key requirement",
    "Second key requirement",
    "Third key requirement"
  ],
  "source_url": "https://official-source.gov/path/to/the/document",
  "tags": ["relevant", "tags"],
  "last_verified": "2026-09-17",
  "verification": "primary"
}
```

For international:
```json
{
  "id": "intl-NNN",
  "jurisdiction": "Country or Organization",
  "title": "Official Name Here",
  "type": "regulation",
  "status": "enacted",
  "date_adopted": "2025-01-15",
  "effective_date": "2025-07-01",
  "summary": "One to three sentences describing the framework.",
  "key_provisions": [
    "First key provision",
    "Second key provision",
    "Third key provision"
  ],
  "source_url": "https://official-source.gov/path/to/the/document",
  "tags": ["relevant", "tags"],
  "last_verified": "2026-09-17",
  "verification": "primary"
}
```

### Step 3: Required Fields

| Field | Required | Notes |
|:------|:--------:|:------|
| `id` | Yes | Unique and permanent. `fed-`, `state-` or `intl-` plus at least three digits, matching the file |
| `title` | Yes | Official name of legislation. The older `name` field is retired |
| `status` | Yes | See status values below |
| `summary` | Yes | 1-3 sentences, factual, neutral tone |
| `key_provisions` | Yes | Array of 3-6 main requirements |
| `source_url` | Yes | Link to official government source |
| `tags` | Yes | 2-5 relevant topic tags, lowercase with underscores |
| `last_verified` | Yes | `YYYY-MM-DD` date you checked it, or `needs_verification` |
| `verification` | No | `primary`, `secondary` or `unconfirmed` — how you checked it |
| `effective_date` | If enacted | When obligations begin. For a law that applies in stages, the first stage |
| `milestones` | If phased | Every stage, oldest first: `[{"date": "2027-01-01", "description": "Platform duties begin"}]`. The first stage's date must equal `effective_date`. Only record a stage you have read a source for |
| `injunction` / `date_enjoined` | If enjoined | The court, case and date of the order blocking enforcement |
| `superseded_by` / `supersedes` | If applicable | The id of the related record. Set both sides: the validator fails a one-way link |
| `amends` / `amended_by` | If applicable | The id of the related record. Also set on both sides |

A few fields are required per file as well:

| File | Also required |
|:-----|:--------------|
| `us_federal_actions.json` | `type`, `issuing_body`, `date_issued` |
| `us_state_bills.json` | `state`, `bill_number` |
| `international_frameworks.json` | `jurisdiction`, `type` |

A record with status `superseded` must have `superseded_by`, one with status `vetoed` must have `veto_reason`, and one with status `enjoined` must have `injunction`. Any field not in [`schema/legislation.schema.json`](schema/legislation.schema.json) is rejected, which catches misspellings such as `efective_date`. Dates must be zero-padded (`2026-01-05`, not `2026-1-5`), and `tags` and `key_provisions` must be lists.

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
| `enjoined` | A court has blocked enforcement. Set `injunction` and `date_enjoined` |

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

When legislation status changes (enacted, vetoed, rescinded, enjoined):

1. Update the `status` field
2. Add relevant date field (`date_enacted`, `date_vetoed`, `date_rescinded`, `date_enjoined`)
3. If vetoed, add `veto_reason`. If enjoined, add `injunction`
4. Update `summary` if needed
5. Add an entry at the top of `data/meta/changelog.json`:

```json
{"date": "2026-12-01", "summary": "Recorded the veto of Example HB 1.", "updated": ["state-020"]}
```

Use `added` instead of `updated` for a new record. The site shows the latest entries under "Recently changed".

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
- [ ] An entry at the top of `data/meta/changelog.json` says what you added or changed
- [ ] Run `python3 validate.py` and fix everything it reports
- [ ] Run `python3 -m unittest discover -s tests`. It checks the hand-written numbers below against the data and says which one is out of date

If you added a record, or changed a status or a date, these hand-written places must follow. The tests fail until they do:

- [ ] README badges at the top: `Legislation Tracked`, and `Jurisdictions` if the jurisdiction is new
- [ ] README "Data Currency" line: "N entries across M jurisdictions"
- [ ] README "At a glance" table
- [ ] README "Upcoming effective dates" table: one row for each future date, including each milestone, with the Legislation cell linking to the record on the site (copy an existing row). Remove the row if the date changed or the law was superseded
- [ ] `examples/current_landscape.md`: regenerate it with `python3 src/generate_dashboard.py examples/current_landscape.md`

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
3. Add `supersedes` on the new record pointing back. `validate.py` fails if either side is missing
4. Rewrite the old summary to say what happened

Colorado `state-001` is the worked example: SB 24-205 was delayed, enforcement-stayed and then repealed before it ever took effect, so it is marked `superseded` and points at `state-011`. Anyone who cited it before the repeal can still resolve that id and see what changed.

---

## Testing Your Changes

```bash
# Run this first. It checks structure, field types, required fields, dates,
# duplicate ids, bare-domain URLs and that every supersession link is mutual.
python3 validate.py

# Confirm your entry appears in queries (id, bill number and title all work)
python3 src/query_legislation.py --search "your entry title"

# Confirm the dashboard still generates
python3 src/generate_dashboard.py

# Check tag assignment
python3 src/query_legislation.py --list-tags

# Run this after any change to data/, schema/ or code. It also checks the
# README's counts and its upcoming-dates table against the data.
python3 -m unittest discover -s tests
```

`validate.py` and the tests run automatically on every pull request. They only read
files and report what is wrong; they never edit or commit anything. If one fails,
the message names the record and the problem.

The website reads `data/*.json` directly, so there is no second copy to update.
Your entry appears on the site as soon as the change is on `main`.

---

## Submitting

1. Fork the repository
2. Create a branch: `git checkout -b add-virginia-hb1234`
3. Make your changes
4. Run `python3 validate.py` and `python3 -m unittest discover -s tests`, and fix anything they report
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
