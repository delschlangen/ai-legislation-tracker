<p align="center">
  <img src="https://img.shields.io/badge/Legislation%20Tracked-28-blue?style=for-the-badge" alt="Legislation Tracked"/>
  <img src="https://img.shields.io/badge/Jurisdictions-21-green?style=for-the-badge" alt="Jurisdictions"/>
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
  <a href="#quick-reference">Quick Reference</a> •
  <a href="#getting-started">Getting Started</a> •
  <a href="#whats-tracked">Coverage</a> •
  <a href="#query-examples">Query</a> •
  <a href="#contributing">Contribute</a> •
  <a href="#live-demo">Live Demo</a>
</p>

---

## Why This Exists

AI governance is fragmenting fast. EU AI Act enforcement begins 2026. Colorado's SB 205 is the first comprehensive US state law. EO 14110 was rescinded. China has multiple active GenAI regulations. Keeping track requires **structured data**, not news alerts.

This repo provides:
- **Machine-readable JSON datasets** with standardized schemas
- **CLI tools** for querying across jurisdictions
- **Dashboard generation** for at-a-glance status reports
- **Zero dependencies** — pure Python standard library

---

## Data Currency

> **This dataset reflects AI legislation status as of December 2024.**

All 28 entries were verified against official government sources on **2024-12-24**. Each entry includes a `last_verified` field indicating when it was last checked.

**Important:** Legislation changes frequently. Always verify current status with official sources before making compliance decisions.

| Resource | Description |
|:---------|:------------|
| [CITATION.md](CITATION.md) | How to cite this dataset (BibTeX, APA, Chicago, Bluebook) |
| [MAINTENANCE.md](MAINTENANCE.md) | Update schedule, verification methodology, how to report corrections |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to add new legislation or submit updates |

---

## Quick Reference

### At a Glance (December 2025)

| Category | Total | Enacted/Active | Pending | Vetoed/Rescinded |
|:---------|:-----:|:--------------:|:-------:|:----------------:|
| US Federal | 8 | 7 | — | 1 |
| US State | 10 | 9 | — | 1 |
| International | 10 | 8 | 2 | — |
| **Total** | **28** | **24** | **2** | **2** |

### Key Legislation You Should Know

| What | Where | Status | Why It Matters |
|:-----|:------|:------:|:---------------|
| **EU AI Act** | EU | Enacted | First comprehensive AI regulation globally. Risk-based framework with fines up to €35M or 7% revenue. |
| **Colorado SB 205** | CO | Enacted | First comprehensive US state AI law. Covers high-risk AI discrimination. Effective Feb 2026. |
| **EO 14110** | US Federal | Rescinded | Was the main US federal AI policy. Rescinded Jan 2025. |
| **NIST AI RMF** | US Federal | Active | Voluntary risk management framework. De facto US standard. |
| **NYC Local Law 144** | NYC | Active | Requires bias audits for hiring AI. In effect now. |

---

## Getting Started

```bash
# Clone the repository
git clone https://github.com/delschlangen/ai-legislation-tracker.git
cd ai-legislation-tracker

# Generate a full dashboard report
python src/generate_dashboard.py

# Query legislation by topic
python src/query_legislation.py --tag employment

# Search across all fields
python src/query_legislation.py --search "frontier"

# List all available tags
python src/query_legislation.py --list-tags

# Get counts only
python src/query_legislation.py --tag comprehensive --count
```

**Requirements:** Python 3.7+ (no external dependencies)

---

## What's Tracked

### US Federal Actions (8 items)

| Title | Type | Status | Agency |
|:------|:-----|:------:|:-------|
| Executive Order 14110 | Executive Order | Rescinded | White House |
| NIST AI Risk Management Framework 1.0 | Framework | Active | NIST |
| OMB M-24-10: AI Governance | Guidance | Active | OMB |
| Blueprint for an AI Bill of Rights | Guidance | Active | OSTP |
| SEC AI-Related Disclosure Guidance | Guidance | Active | SEC |
| FTC AI and Algorithm Enforcement | Enforcement | Active | FTC |
| DoD AI Adoption Strategy | Strategy | Active | DoD |
| Commerce AI Export Controls | Regulation | Active | BIS |

### US State Legislation (10 items)

| State | Bill | Title | Status | Effective |
|:------|:-----|:------|:------:|:---------:|
| Colorado | SB 24-205 | Consumer Protections for AI | Enacted | 2026-02-01 |
| California | SB 1047 | Frontier AI Safety | Vetoed | — |
| California | AB 2013 | AI Training Data Transparency | Enacted | 2026-01-01 |
| California | AB 2885 | AI Definition Standardization | Enacted | 2025-01-01 |
| Illinois | HB 3773 | AI Video Interview Act | Enacted | 2020-01-01 |
| NYC | Local Law 144 | Automated Employment Decision Tools | Enacted | 2023-07-05 |
| Texas | HB 2060 | AI Advisory Council | Enacted | 2023-09-01 |
| Utah | SB 149 | AI Policy Act | Enacted | 2024-05-01 |
| Tennessee | HB 2959 | ELVIS Act (AI Voice Protection) | Enacted | 2024-07-01 |
| Connecticut | SB 1103 | AI Inventory and Assessment | Enacted | 2023-10-01 |

### International Frameworks (10 items)

| Jurisdiction | Name | Type | Status |
|:-------------|:-----|:-----|:------:|
| European Union | EU AI Act | Regulation | Enacted |
| United Kingdom | UK AI Regulation Framework | Framework | Active |
| China | Interim Measures for GenAI Services | Regulation | Active |
| China | Algorithm Recommendation Regulations | Regulation | Active |
| Canada | AIDA (Bill C-27) | Proposed | Pending |
| Brazil | AI Bill (PL 2338/2023) | Proposed | Pending |
| OECD | OECD AI Principles | Principles | Active |
| United Nations | Global Digital Compact | Resolution | Adopted |
| G7 | Hiroshima AI Process | Framework | Active |
| International | Bletchley Declaration | Declaration | Active |

---

## Upcoming Deadlines

| Date | Jurisdiction | Legislation | What Happens |
|:-----|:-------------|:------------|:-------------|
| **2025-01-01** | California | AB 2885 | AI definition standardization takes effect |
| **2026-01-01** | California | AB 2013 | Training data transparency requirements begin |
| **2026-02-01** | Colorado | SB 24-205 | First comprehensive state AI law takes effect |
| **2026-08-01** | European Union | EU AI Act | Full application of all provisions |

---

## Query Examples

### Find Employment AI Laws
```bash
python src/query_legislation.py --tag employment
```
Returns: Illinois HB 3773, NYC Local Law 144

### Find Enacted Legislation Only
```bash
python src/query_legislation.py --status enacted
```

### Search for Frontier AI Mentions
```bash
python src/query_legislation.py --search "frontier"
```
Returns: California SB 1047, EO 14110, Hiroshima AI Process, Bletchley Declaration

### Filter by State
```bash
python src/query_legislation.py --jurisdiction California
```

### Generate Full Dashboard
```bash
python src/generate_dashboard.py output.md
```

---

## Sample Output

```
📋 Colorado Consumer Protections for Artificial Intelligence
================================================================
📍 Jurisdiction: Colorado
📊 Status: ✅ enacted
📅 Effective: 2026-02-01

📝 Summary:
   First comprehensive state AI regulation in the US. Requires deployers
   and developers of high-risk AI systems to use reasonable care to avoid
   algorithmic discrimination.

🔑 Key Provisions:
   • High-risk AI system definition
   • Developer duties (documentation, disclosure)
   • Deployer duties (risk management, impact assessments)
   • Consumer notification and opt-out rights
   • Attorney General enforcement

🏷️  Tags: comprehensive, high_risk, discrimination, first_state
```

---

## Data Structure

All legislation entries follow a consistent JSON schema:

```json
{
  "id": "state-001",
  "state": "Colorado",
  "bill_number": "SB 24-205",
  "title": "Consumer Protections for Artificial Intelligence",
  "status": "enacted",
  "date_enacted": "2024-05-17",
  "effective_date": "2026-02-01",
  "summary": "First comprehensive state AI regulation...",
  "key_provisions": [
    "High-risk AI system definition",
    "Developer duties (documentation, disclosure)",
    "Deployer duties (risk management, impact assessments)"
  ],
  "source_url": "https://leg.colorado.gov/bills/sb24-205",
  "tags": ["comprehensive", "high_risk", "discrimination"],
  "last_verified": "2024-12-24"
}
```

---

## Project Structure

```
ai-legislation-tracker/
├── .github/workflows/
│   └── update-legislation.yml       # Weekly auto-update workflow
├── data/
│   ├── us_federal_actions.json      # Federal executive orders, guidance, frameworks
│   ├── us_state_bills.json          # State legislation across 10 jurisdictions
│   └── international_frameworks.json # EU, UK, China, OECD, UN, G7, etc.
├── src/
│   ├── generate_dashboard.py        # Creates markdown summary reports
│   ├── query_legislation.py         # CLI tool for filtering and searching
│   ├── merge_api_data.py            # Merges API data into tracker
│   ├── federal_register.py          # Federal Register API integration
│   └── congress_gov.py              # Congress.gov API integration
├── docs/                            # GitHub Pages site
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── data.js
├── API_SOURCES.md                   # API documentation
├── CITATION.md                      # How to cite this dataset
├── CONTRIBUTING.md                  # Contribution guidelines
├── MAINTENANCE.md                   # Update schedule and verification info
├── README.md
└── LICENSE
```

---

## Top Tags by Frequency

| Tag | Count | Description |
|:----|:-----:|:------------|
| `comprehensive` | 4 | Broad AI regulation covering multiple sectors |
| `frontier_ai` | 4 | Focused on advanced/frontier AI systems |
| `principles` | 4 | Non-binding guiding principles |
| `safety` | 3 | Safety testing and requirements |
| `disclosure` | 3 | Transparency and disclosure requirements |
| `genai` | 3 | Generative AI specific rules |
| `china` | 3 | Chinese regulatory items |
| `international` | 3 | Multi-national agreements |
| `voluntary` | 3 | Non-binding/voluntary frameworks |
| `discrimination` | 2 | Algorithmic bias and discrimination |

---

## Contributing

### Adding New Legislation

1. **Add entry** to appropriate JSON file in `data/`
2. **Follow existing schema** — check similar entries for field structure
3. **Include `source_url`** — link to official government source
4. **Add relevant tags** — use existing tags when applicable
5. **Verify** by running `python src/generate_dashboard.py`
6. **Submit PR** with brief description

### Schema Requirements

| Field | Required | Description |
|:------|:--------:|:------------|
| `id` | Yes | Unique identifier (e.g., `state-011`) |
| `title` / `name` | Yes | Official name |
| `status` | Yes | `enacted`, `active`, `pending`, `vetoed`, `rescinded` |
| `summary` | Yes | 1-3 sentence description |
| `key_provisions` | Yes | Array of key points |
| `source_url` | Yes | Official source link |
| `tags` | Yes | Relevant topic tags |
| `effective_date` | If enacted | When it takes effect |
| `last_verified` | Yes | Date entry was last verified (YYYY-MM-DD) |

---

## Disclaimer

This is a **research and tracking tool**, not legal advice. Legislation changes frequently. Always verify current status with official government sources before making compliance decisions.

---

## Automated Updates

This tracker **automatically updates every week** via GitHub Actions. New AI legislation from Congress.gov and Federal Register is fetched and merged into the dataset.

| Source | Frequency | What It Tracks |
|:-------|:---------:|:---------------|
| [Federal Register](https://www.federalregister.gov/developers) | Weekly | Federal rules, proposed rules, executive orders |
| [Congress.gov](https://api.congress.gov/) | Weekly | Congressional bills (HR, S, etc.) |

**Setup (one-time):** Add your Congress.gov API key as a GitHub secret named `CONGRESS_API_KEY`. Get a free key at [api.congress.gov/sign-up](https://api.congress.gov/sign-up/).

See [API_SOURCES.md](API_SOURCES.md) for full documentation.

---

## Roadmap

- [x] ~~Automate updates via official APIs~~ (Federal Register, Congress.gov)
- [x] ~~GitHub Actions workflow for automated weekly updates~~
- [ ] Add RSS/webhook integration for legislative tracking services
- [ ] Include bill text links where available
- [ ] Create jurisdiction comparison tool
- [ ] Add timeline visualization
- [ ] Add notification system for effective date approaches

---

## Live Demo

**Use this tool directly in your browser:**

### **[https://delschlangen.github.io/ai-legislation-tracker](https://delschlangen.github.io/ai-legislation-tracker)**

No installation or dependencies required. The web interface provides:
- Searchable table of all 28 legislation items
- Filter by jurisdiction, status, and tags
- Full-text search across titles, summaries, and provisions
- Expandable rows with complete details and source links
- Mobile-responsive design

---

## License

**MIT License** — See [LICENSE](LICENSE)

Data is curated from public government sources.

---

<p align="center">
  <strong>Built by Del Schlangen</strong><br/>
  <a href="https://linkedin.com/in/del-s-759557175/">LinkedIn</a>
</p>
