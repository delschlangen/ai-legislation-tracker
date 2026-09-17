<p align="center">
  <img src="https://img.shields.io/badge/Legislation%20Tracked-44-blue?style=for-the-badge" alt="Legislation Tracked"/>
  <img src="https://img.shields.io/badge/Jurisdictions-22-green?style=for-the-badge" alt="Jurisdictions"/>
  <img src="https://img.shields.io/badge/Python-3.7+-yellow?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/License-MIT-purple?style=for-the-badge" alt="License"/>
  <a href="https://delschlangen.github.io/ai-legislation-tracker/">
    <img src="https://img.shields.io/badge/Try%20It%20Live-Visit%20Site-ff6b6b?style=for-the-badge" alt="Try It Live"/>
  </a>
</p>

<h1 align="center">AI Legislation Tracker</h1>

<p align="center">
  <strong>A structured, queryable database tracking AI laws, regulations, and governance frameworks worldwide.</strong>
</p>

<p align="center">
  <a href="https://delschlangen.github.io/ai-legislation-tracker/">🚀 <strong>Use this tool live</strong></a> — No installation required. Search and filter legislation in your browser.
</p>

<p align="center">
  <a href="#data-currency">Data Currency</a> •
  <a href="#what-makes-this-different">What's Different</a> •
  <a href="#quick-reference">Quick Reference</a> •
  <a href="#getting-started">Getting Started</a> •
  <a href="#use-the-data">Use the Data</a> •
  <a href="#contributing">Contribute</a>
</p>

---

## Why This Exists

AI governance is fragmenting fast, and it does not hold still. The EU AI Act's high-risk obligations were pushed from 2026 to 2027. Colorado's law — the first comprehensive US state AI statute — was delayed, enforcement-stayed, then repealed and replaced before it ever took effect. Canada's AIDA died at prorogation. Keeping track requires **structured data with a history**, not news alerts.

This repo provides:
- **Machine-readable JSON datasets** with a consistent schema and permanent record ids
- **Supersession tracking** — what replaced what, and when
- **CLI tools** for querying across jurisdictions
- **A browser interface** with no install and no account
- **Zero dependencies** — pure Python standard library

---

## Data Currency

> **Last review: September 2026. 44 entries across 22 jurisdictions.**

Each entry carries its own `last_verified` date and a `verification` field saying how it was checked:

| `verification` | Meaning |
|:---|:---|
| `primary` | Confirmed against the official legislature, agency or gazette text |
| `secondary` | Confirmed against multiple independent published legal analyses, not the primary text |
| `unconfirmed` | Provisional. Corroboration was thin. Treat with caution |
| *(absent)* | As originally recorded; not re-checked since |

**This is a research and tracking tool, not legal advice.** Always confirm against the official source before making a compliance decision. Every entry links to one.

| Resource | Description |
|:---------|:------------|
| [CITATION.md](CITATION.md) | How to cite this dataset |
| [MAINTENANCE.md](MAINTENANCE.md) | Review cadence, verification method, status vocabulary |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to add or correct an entry |

---

## What Makes This Different

Most AI law trackers are web pages or PDFs published by law firms and membership bodies. They tell you what a law says **today**. They are excellent, and they are not reusable — you cannot query them, diff them, or cite a stable identifier.

This project is built around two things those cannot offer:

**1. The data is yours.** MIT licensed, plain JSON, fetchable from a stable URL. Load it into a notebook, a spreadsheet, a compliance tool or a retrieval index without asking anyone.

**2. Records have a history.** Ids are permanent. `state-001` means Colorado SB 24-205 forever, including now that it has been repealed — the record stays, its status becomes `superseded`, and `superseded_by` points at the statute that replaced it. A citation written in 2024 still resolves, and tells you what changed underneath it. Every change is a git commit with a source link.

This dataset deliberately tracks **notable frameworks and instruments with operative legal effect**, not every introduced bill. Depth and accuracy over volume.

---

## Quick Reference

### At a glance

| Category | Total | In force / active | Pending | Superseded, expired, vetoed or rescinded |
|:---------|:-----:|:-----------------:|:-------:|:----------------------------------------:|
| US Federal | 12 | 10 | — | 2 |
| US State | 17 | 15 | — | 2 |
| International | 15 | 12 | 2 | 1 |
| **Total** | **44** | **37** | **2** | **5** |

### Key legislation you should know

| What | Where | Status | Why it matters |
|:-----|:------|:------:|:---------------|
| **EU AI Act** | EU | Enacted | First comprehensive AI regulation. Amended by the Digital Omnibus: Annex III high-risk duties now apply from Dec 2027, Annex I from Aug 2028. |
| **Colorado SB 26-189** | CO | Enacted | Replaced the repealed Colorado AI Act with a narrower transparency regime. Effective Jan 2027. |
| **California SB 53** | CA | Enacted | First US state frontier AI safety law. In force since Jan 2026. |
| **Texas HB 149 (TRAIGA)** | TX | Enacted | Third state comprehensive AI law, built on intent rather than risk tiers. |
| **Connecticut CART Act** | CT | Enacted | Broadest US state AI law to date. First obligations bite Oct 2026. |
| **TAKE IT DOWN Act** | US Federal | Enacted | First federal statute placing AI duties on private platforms. |
| **South Korea AI Framework Act** | KR | Enacted | World's second comprehensive national AI statute. In force since Jan 2026. |

### Upcoming effective dates

| Date | Jurisdiction | Legislation | What happens |
|:-----|:-------------|:------------|:-------------|
| **2026-10-01** | Connecticut | CART Act | First obligations begin, including AI-related layoff disclosure |
| **2027-01-01** | Colorado | SB 26-189 | Replacement AI law takes effect |
| **2027-01-01** | New York | RAISE Act | Frontier model safety duties begin |
| **2027-12-02** | European Union | EU AI Act | Annex III stand-alone high-risk obligations apply |
| **2028-08-02** | European Union | EU AI Act | Annex I embedded high-risk obligations apply |

Run `python3 src/generate_dashboard.py` for the current version of this table, generated from the data.

---

## Getting Started

```bash
git clone https://github.com/delschlangen/ai-legislation-tracker.git
cd ai-legislation-tracker

# Full dashboard report
python3 src/generate_dashboard.py

# Query by topic, status or jurisdiction
python3 src/query_legislation.py --tag employment
python3 src/query_legislation.py --status superseded
python3 src/query_legislation.py --jurisdiction Colorado
python3 src/query_legislation.py --search "frontier"
python3 src/query_legislation.py --list-tags

# Check the data is well formed
python3 validate.py

# Export everything to one CSV for a spreadsheet
python3 src/export_csv.py
```

**Requirements:** Python 3.7+. No external dependencies.

---

## Use the Data

The three JSON files are the whole dataset and are stable URLs:

```
https://raw.githubusercontent.com/delschlangen/ai-legislation-tracker/main/data/us_federal_actions.json
https://raw.githubusercontent.com/delschlangen/ai-legislation-tracker/main/data/us_state_bills.json
https://raw.githubusercontent.com/delschlangen/ai-legislation-tracker/main/data/international_frameworks.json
```

```python
import json, urllib.request

BASE = "https://raw.githubusercontent.com/delschlangen/ai-legislation-tracker/main/data"
state = json.load(urllib.request.urlopen(f"{BASE}/us_state_bills.json"))

for law in state:
    if law["status"] == "enacted":
        print(law["bill_number"], "-", law["title"])
```

Prefer a spreadsheet? `python3 src/export_csv.py` flattens all three files into one CSV. It is generated on demand rather than committed, so there is never a stale second copy of the data in the repository.

### Record schema

```json
{
  "id": "state-013",
  "state": "California",
  "bill_number": "SB 53",
  "title": "Transparency in Frontier Artificial Intelligence Act",
  "status": "enacted",
  "date_enacted": "2025-09-29",
  "effective_date": "2026-01-01",
  "summary": "First US state frontier AI safety law...",
  "key_provisions": ["Publish a frontier AI framework...", "..."],
  "source_url": "https://leginfo.legislature.ca.gov/...",
  "tags": ["frontier_ai", "safety", "transparency"],
  "last_verified": "2026-09-17",
  "verification": "secondary"
}
```

| Field | Required | Notes |
|:------|:--------:|:------|
| `id` | Yes | Permanent. Never reused or renumbered |
| `title` | Yes | Official name |
| `status` | Yes | `enacted`, `active`, `adopted`, `pending`, `vetoed`, `rescinded`, `superseded`, `expired` |
| `summary` | Yes | One to three sentences |
| `key_provisions` | Yes | Array of the main obligations |
| `source_url` | Yes | A specific document, never a bare agency homepage |
| `tags` | Yes | Lowercase with underscores |
| `last_verified` | Yes | `YYYY-MM-DD`, or `needs_verification` |
| `verification` | No | `primary`, `secondary` or `unconfirmed` |
| `effective_date` | If enacted | When obligations begin |
| `superseded_by` / `supersedes` | If applicable | The id of the related record |
| `amends` / `amended_by` | If applicable | The id of the related record |

---

## Project Structure

```
ai-legislation-tracker/
├── data/                            # The dataset — the single source of truth
│   ├── us_federal_actions.json
│   ├── us_state_bills.json
│   └── international_frameworks.json
├── docs/                            # GitHub Pages site; reads data/ at runtime
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── src/
│   ├── generate_dashboard.py        # Markdown summary report
│   ├── query_legislation.py         # CLI filtering and search
│   └── export_csv.py                # Flatten the dataset to CSV on demand
├── .github/
│   ├── ISSUE_TEMPLATE/              # Forms for reporting or suggesting entries
│   └── workflows/validate.yml       # Read-only data check on pull requests
├── examples/current_landscape.md    # Sample generated dashboard
├── validate.py                      # Data validator (read-only)
├── CITATION.md · CONTRIBUTING.md · MAINTENANCE.md · LICENSE
└── README.md
```

---

## Contributing

**You do not need to know Git.** If you spot something wrong, open an issue:

- [Report an incorrect or out-of-date entry](https://github.com/delschlangen/ai-legislation-tracker/issues/new?template=stale-entry.yml)
- [Suggest a law to add](https://github.com/delschlangen/ai-legislation-tracker/issues/new?template=new-law.yml)

Corrections are the most valuable contribution here. A tracker that is confidently wrong is worse than one that is visibly incomplete.

If you would rather edit the data directly, see [CONTRIBUTING.md](CONTRIBUTING.md) for the schema and the submission checklist. Run `python3 validate.py` before opening a pull request — the same check runs automatically and will tell you what is wrong.

---

## Roadmap

- [x] ~~Track supersession and repeal, not just current status~~
- [x] ~~Single source of truth for the website and the dataset~~
- [x] ~~Read-only validation on pull requests~~
- [x] ~~Issue forms for non-technical contributors~~
- [x] ~~CSV export for spreadsheet users~~
- [ ] Re-verify every entry against primary sources and move `verification` to `primary`
- [ ] Publish a JSON Schema file
- [ ] Broaden state coverage, prioritising laws with operative obligations

---

## License

**MIT License** — See [LICENSE](LICENSE)

Data is curated from public government sources.

---

<p align="center">
  <strong>Built by Del Schlangen</strong><br/>
  <a href="https://linkedin.com/in/del-s-759557175/">LinkedIn</a>
</p>
