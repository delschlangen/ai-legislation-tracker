<p align="center">
  <img src="https://img.shields.io/badge/Legislation%20Tracked-47-blue?style=for-the-badge" alt="Legislation Tracked"/>
  <img src="https://img.shields.io/badge/Jurisdictions-22-green?style=for-the-badge" alt="Jurisdictions"/>
  <img src="https://img.shields.io/badge/Python-3.7+-yellow?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-purple?style=for-the-badge" alt="License: MIT"/>
  </a>
  <a href="https://orcid.org/0009-0005-5116-9564">
    <img src="https://img.shields.io/badge/ORCID-0009--0005--5116--9564-A6CE39?style=for-the-badge&logo=orcid&logoColor=white" alt="ORCID"/>
  </a>
  <a href="https://delschlangen.github.io/ai-legislation-tracker/">
    <img src="https://img.shields.io/badge/Try%20It%20Live-Visit%20Site-ff6b6b?style=for-the-badge" alt="Try It Live"/>
  </a>
</p>

<h1 align="center">AI Legislation Tracker</h1>

<p align="center">
  <strong>An open-source, machine-readable dataset and CLI toolkit for tracking AI legislation, AI regulation, and AI governance frameworks across US federal, US state, and international jurisdictions — including the EU AI Act, state AI laws, executive orders, and global AI policy.</strong>
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

> **Last full review: September 2026. 47 entries across 22 jurisdictions.**
>
> A targeted update on 2026-11-24 added three entries and corrected one. Each entry's own `last_verified` date says when it was last checked; the site shows the range, and the weekly report lists any entry not checked in six months.

Each entry carries its own `last_verified` date and may carry a `verification` field saying how it was checked:

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
| [Change log](data/meta/changelog.json) | What was added or corrected, and when |

**The dataset checks itself every week.** A scheduled job opens a GitHub issue titled "Maintenance report" listing stale entries, dates that just passed, broken source links, and anything the Federal Register or Congress.gov report as newer than the record. It needs no API keys or setup, and it never edits the data: every change is still made, and verified, by a person. See [MAINTENANCE.md](MAINTENANCE.md#automated-maintenance-report).

---

## What Makes This Different

Most AI law trackers are web pages or PDFs published by law firms and membership bodies. They tell you what a law says **today**. They are excellent, and they are not reusable — you cannot query them, diff them, or cite a stable identifier.

This project is built around two things those cannot offer:

**1. The data is yours.** MIT licensed, plain JSON, fetchable from a stable URL. Load it into a notebook, a spreadsheet, a compliance tool or a retrieval index without asking anyone.

**2. Records have a history.** Ids are permanent. `state-001` means Colorado SB 24-205 forever, including now that it has been repealed — the record stays, its status becomes `superseded`, and `superseded_by` points at the statute that replaced it. A citation written before the repeal still resolves, and tells you what changed underneath it. Every change is a git commit with a source link.

This dataset deliberately tracks **notable frameworks and instruments with operative legal effect**, not every introduced bill. Depth and accuracy over volume.

---

## Quick Reference

### At a glance

| Category | Total | Enacted, active or adopted | Pending | Superseded, expired, vetoed, rescinded or enjoined |
|:---------|:-----:|:--------------------------:|:-------:|:--------------------------------------------------:|
| US Federal | 13 | 11 | — | 2 |
| US State | 19 | 17 | — | 2 |
| International | 15 | 12 | 2 | 1 |
| **Total** | **47** | **40** | **2** | **5** |

Enacted does not always mean in force yet: some enacted laws have an effective date still to come. For what applies today, use the "In force today" filter on the [live site](https://delschlangen.github.io/ai-legislation-tracker/) or `python3 src/query_legislation.py --in-force`.

### Key legislation you should know

| What | Where | Status | Why it matters |
|:-----|:------|:------:|:---------------|
| **EU AI Act** | EU | Enacted | First comprehensive AI regulation. Amended by the Digital Omnibus: Annex III high-risk duties now apply from Dec 2027, Annex I from Aug 2028. |
| **Colorado SB 26-189** | CO | Enacted | Replaced the repealed Colorado AI Act with a narrower transparency regime. Effective Jan 2027. |
| **California SB 53** | CA | Enacted | First US state frontier AI safety law. In force since Jan 2026. |
| **Texas HB 149 (TRAIGA)** | TX | Enacted | Third state comprehensive AI law, built on intent rather than risk tiers. |
| **Connecticut CART Act** | CT | Enacted | One of the most comprehensive US state AI laws. First obligations were scheduled for Oct 2026. |
| **TAKE IT DOWN Act** | US Federal | Enacted | First federal statute placing AI duties on private platforms. |
| **South Korea AI Framework Act** | KR | Enacted | World's second comprehensive national AI statute. In force since Jan 2026. |

### Upcoming effective dates

| Date | Jurisdiction | Legislation | What happens |
|:-----|:-------------|:------------|:-------------|
| **2026-12-02** | European Union | [EU AI Act](https://delschlangen.github.io/ai-legislation-tracker/#intl-001) | Prohibitions on non-consensual intimate imagery and CSAM-generating systems apply |
| **2027-01-01** | Colorado | [SB 26-189](https://delschlangen.github.io/ai-legislation-tracker/#state-011) | Replacement AI law takes effect |
| **2027-01-01** | New York | [RAISE Act](https://delschlangen.github.io/ai-legislation-tracker/#state-016) | Frontier model safety duties begin |
| **2027-01-01** | Illinois | [SB 315](https://delschlangen.github.io/ai-legislation-tracker/#state-018) | Frontier AI safety duties and third-party audits begin |
| **2027-01-01** | California | [AI Transparency Act](https://delschlangen.github.io/ai-legislation-tracker/#state-019) | Large online platform and hosting platform duties begin |
| **2027-08-02** | European Union | [EU AI Act](https://delschlangen.github.io/ai-legislation-tracker/#intl-001) | National regulatory sandboxes due |
| **2027-12-02** | European Union | [EU AI Act](https://delschlangen.github.io/ai-legislation-tracker/#intl-001) | Annex III stand-alone high-risk obligations apply |
| **2028-01-01** | California | [AI Transparency Act](https://delschlangen.github.io/ai-legislation-tracker/#state-019) | Capture-device makers must offer a latent disclosure option |
| **2028-01-01** | Connecticut | [CART Act](https://delschlangen.github.io/ai-legislation-tracker/#state-017) | Last of the staggered obligations begin |
| **2028-08-02** | European Union | [EU AI Act](https://delschlangen.github.io/ai-legislation-tracker/#intl-001) | Annex I embedded high-risk obligations apply |

This table is the one list of dates kept by hand, so two things guard it. Each row links to its record, and the tests fail if a row names a date that record does not have, or if the data has a future date with no row here. The weekly maintenance report flags a row once its date has passed. The [live site](https://delschlangen.github.io/ai-legislation-tracker/) computes the next six dates from the data on every visit, and `python3 src/generate_dashboard.py` prints the next ten.

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
python3 src/query_legislation.py --in-force --jurisdiction California
python3 src/query_legislation.py --list-tags

# Check the data is well formed
python3 validate.py

# Run the test suite (standard library only)
python3 -m unittest discover -s tests

# Export everything to one CSV for a spreadsheet
python3 src/export_csv.py

# The weekly maintenance report, offline parts only
python3 scripts/maintenance_report.py
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

Validating your own copy or a fork? [`schema/legislation.schema.json`](schema/legislation.schema.json) is a JSON Schema (draft 2020-12) for all three files. Use `#/$defs/federalFile`, `#/$defs/stateFile` or `#/$defs/internationalFile` for one file. It lists every field a record may carry, so a misspelled field fails validation. `validate.py` checks every record against this schema, so nothing the schema rejects can pass it. It then adds rules a schema cannot express: real calendar dates, mutual supersession and amendment links, milestones in date order, and a phased law's first milestone matching `effective_date`.

### Using the site

The [live site](https://delschlangen.github.io/ai-legislation-tracker/) needs no install. Beyond search and filters:

- **Coming up** lists the next effective dates and phased obligations, computed from the data each time the page loads.
- **Recently changed** shows the latest entries in the change log.
- **In force today** narrows the list to laws and policies that apply now. A law that is enacted but not yet effective is marked "Not yet in force".
- **Sort by** effective date, jurisdiction, name or status.
- **Every view is a link.** Filters and sort order live in the address bar, so a copied URL reproduces what you see. Adding `#state-001` opens that record.
- **Each record** lists every date it carries, from introduction to each stage of a phased law, with a countdown for those still to come. A stage is stated as fact only where the status supports it: for a bill that is pending or was vetoed, or a law that was blocked, repealed or replaced first, the date is shown as the date in the text, with no countdown. Each record also shows the full line of succession and any amendments, with links to each.
- **Back returns from a record you followed a link to.** Following a link to a record, from Coming up, Recently changed or another record, adds a step to the browser's history. Back returns to the view you left, with keyboard focus on the link you used. Filters, sorting, search and opening a row by clicking it update the address in place and add no step, so Back does not undo them.

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
| `id` | Yes | Permanent. Never reused or renumbered. `fed-`, `state-` or `intl-` plus digits |
| `title` | Yes | Official name |
| `status` | Yes | `enacted`, `active`, `adopted`, `pending`, `vetoed`, `rescinded`, `superseded`, `expired`, `enjoined` |
| `summary` | Yes | One to three sentences |
| `key_provisions` | Yes | Array of the main obligations |
| `source_url` | Yes | A specific document, never a bare agency homepage |
| `tags` | Yes | Lowercase with underscores |
| `last_verified` | Yes | `YYYY-MM-DD`, or `needs_verification` |
| `verification` | No | `primary`, `secondary` or `unconfirmed` |
| `effective_date` | If enacted | When obligations begin. For a phased law, the first stage |
| `milestones` | No | Phased dates, oldest first: a list of `{"date", "description"}` |
| `injunction` | If enjoined | The court action blocking enforcement: court, case and date |
| `superseded_by` / `supersedes` | If applicable | The id of the related record. Recorded on both sides |
| `amends` / `amended_by` | If applicable | The id of the related record. Recorded on both sides |

The full vocabulary, including per-file fields such as `state`, `bill_number`, `jurisdiction` and `issuing_body`, is in [`schema/legislation.schema.json`](schema/legislation.schema.json).

---

## Project Structure

```
ai-legislation-tracker/
├── data/                            # The dataset — the single source of truth
│   ├── us_federal_actions.json
│   ├── us_state_bills.json
│   ├── international_frameworks.json
│   └── meta/changelog.json          # What changed and when; shown on the site
├── schema/legislation.schema.json   # JSON Schema for the three data files
├── docs/                            # GitHub Pages site; reads data/ at runtime
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── src/
│   ├── generate_dashboard.py        # Markdown summary report
│   ├── query_legislation.py         # CLI filtering and search
│   └── export_csv.py                # Flatten the dataset to CSV on demand
├── scripts/                         # Weekly maintenance report (read-only)
│   ├── maintenance_report.py        # Stale entries, passed dates, README dates
│   ├── link_check.py                # Do the source links still answer?
│   ├── upstream_check.py            # Federal Register and Congress.gov, no keys
│   ├── timebox.py                   # A time limit on each network check
│   └── publish_report.py            # Posts the report as one GitHub issue
├── .github/
│   ├── ISSUE_TEMPLATE/              # Forms for reporting or suggesting entries
│   └── workflows/
│       ├── validate.yml             # Read-only data check and tests on every pull request
│       └── maintenance.yml          # Weekly report, posted as a GitHub issue
├── examples/current_landscape.md    # Sample generated dashboard
├── tests/                           # Standard-library unittest suite (run by CI)
├── validate.py                      # Data validator (read-only)
├── CITATION.cff                     # Machine-readable citation metadata (GitHub "Cite this repository")
├── CLAUDE.md                        # Conventions for AI-assisted contributions
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
- [x] ~~Publish a JSON Schema file~~
- [x] ~~Weekly automated report: stale entries, broken links, upstream changes~~
- [x] ~~Phased dates, an `enjoined` status, and a change log~~
- [ ] Re-verify every entry against primary sources and move `verification` to `primary`
- [ ] Broaden state coverage, prioritising laws with operative obligations

---

## Citing This Dataset

GitHub's **"Cite this repository"** button (top right of the repo page) reads [CITATION.cff](CITATION.cff) and produces APA and BibTeX entries. [CITATION.md](CITATION.md) has Chicago, Bluebook and IEEE formats, plus guidance on citing a specific commit for reproducibility.

---

## License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for the full text.

Copyright (c) 2024 Del Schlangen. The dataset is curated from public government sources; cite the primary source for any individual law.

---

<p align="center">
  <strong>Built by <a href="https://orcid.org/0009-0005-5116-9564">Del Schlangen</a></strong><br/>
  <a href="https://linkedin.com/in/del-s-759557175/">LinkedIn</a> · <a href="https://orcid.org/0009-0005-5116-9564">ORCID</a>
</p>
