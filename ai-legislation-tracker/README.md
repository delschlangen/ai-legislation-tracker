# ai-legislation-tracker

**Curated dataset and tools for tracking global AI legislation and governance frameworks.**

A structured, queryable database of AI laws, regulations, and policy frameworks across US federal, US state, and international jurisdictions.

## Why This Exists

AI governance is fragmenting fast—EU AI Act, Colorado SB 205, EO 14110 rescission, China's GenAI rules, the Bletchley Declaration. Keeping track of what's enacted, pending, or dead requires structured data, not just news alerts. This repo provides a maintained dataset with simple tools for querying and generating reports.

## Quick Start

```bash
# Clone
git clone https://github.com/delschlangen/ai-legislation-tracker.git
cd ai-legislation-tracker

# Generate dashboard
python src/generate_dashboard.py

# Query by tag
python src/query_legislation.py --tag employment

# Search
python src/query_legislation.py --search "frontier"

# List all tags
python src/query_legislation.py --list-tags
```

## What's Tracked

### US Federal (8 items)
- Executive orders (including rescinded EO 14110)
- Agency frameworks (NIST AI RMF)
- Regulatory guidance (OMB, SEC, FTC)
- Export controls

### US State (10 items)
- Comprehensive bills (Colorado SB 205)
- Employment AI laws (Illinois, NYC)
- Transparency requirements (California AB 2013)
- Vetoed bills (California SB 1047)

### International (10 items)
- EU AI Act
- UK pro-innovation framework
- China's GenAI and algorithm regulations
- OECD principles
- UN, G7, and summit declarations

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

## Data Structure

Each item includes:

```json
{
  "id": "state-001",
  "state": "Colorado",
  "bill_number": "SB 24-205",
  "title": "Consumer Protections for Artificial Intelligence",
  "status": "enacted",
  "date_enacted": "2024-05-17",
  "effective_date": "2026-02-01",
  "summary": "...",
  "key_provisions": ["...", "..."],
  "source_url": "https://...",
  "tags": ["comprehensive", "high_risk", "discrimination"]
}
```

## Project Structure

```
ai-legislation-tracker/
├── data/
│   ├── us_federal_actions.json    # 8 federal items
│   ├── us_state_bills.json        # 10 state items
│   └── international_frameworks.json  # 10 international items
├── src/
│   ├── generate_dashboard.py      # Creates markdown summary
│   └── query_legislation.py       # CLI query tool
├── examples/
│   └── current_landscape.md       # Generated dashboard
├── README.md
└── LICENSE
```

## Query Examples

```bash
# Find all employment-related AI laws
python src/query_legislation.py --tag employment

# Find enacted legislation only
python src/query_legislation.py --status enacted

# Search for frontier AI mentions
python src/query_legislation.py --search "frontier"

# Filter by jurisdiction
python src/query_legislation.py --jurisdiction California

# Just get counts
python src/query_legislation.py --tag comprehensive --count
```

## Upcoming Effective Dates

| Date | Jurisdiction | Item |
|------|--------------|------|
| 2025-01-01 | California | AI Definition Standardization |
| 2026-01-01 | California | AI Training Data Transparency |
| 2026-02-01 | Colorado | Consumer Protections for AI |
| 2026-08-01 | EU | AI Act Full Application |

## Contributing

To add legislation:

1. Add entry to appropriate JSON file in `data/`
2. Follow existing schema
3. Include `source_url` for verification
4. Run `python src/generate_dashboard.py` to verify
5. Submit PR

## Disclaimer

This is a research/tracking tool, not legal advice. Always verify current status with official sources. Legislation changes frequently.

## Next Steps

- [ ] Add RSS/webhook for legislative tracking services
- [ ] Add bill text links where available
- [ ] Create jurisdiction comparison tool
- [ ] Add timeline visualization
- [ ] Automate updates via official APIs

## License

MIT License — See [LICENSE](LICENSE)

Data is curated from public government sources.

---

*Built by Del Schlangen | [LinkedIn](https://linkedin.com/in/del-s-759557175/)*
