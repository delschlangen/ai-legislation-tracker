# Dataset Maintenance

This document describes how the AI Legislation Tracker dataset is maintained, updated, and verified.

---

## Update Schedule

### Regular Updates

- **Quarterly reviews**: Comprehensive review of all entries every 3 months (January, April, July, October)
- **Major legislative events**: Immediate updates when significant AI legislation is enacted, vetoed, or rescinded

### Triggers for Immediate Updates

| Event Type | Response Time |
|:-----------|:--------------|
| Major law enacted (e.g., comprehensive state AI bill) | Within 1 week |
| Executive order issued or rescinded | Within 1 week |
| International framework adopted (e.g., EU AI Act milestones) | Within 1 week |
| Bill vetoed | Within 2 weeks |
| Effective date reached | Within 1 month |

---

## Last Comprehensive Review

| Review Type | Date | Scope |
|:------------|:-----|:------|
| **Full dataset review** | 2024-12-24 | All 28 entries verified |
| US Federal Actions | 2024-12-24 | 8 entries |
| US State Bills | 2024-12-24 | 10 entries |
| International Frameworks | 2024-12-24 | 10 entries |

---

## Submitting Corrections

### Found an Error?

If you find inaccurate, outdated, or missing information:

1. **Open a GitHub Issue** at [github.com/delschlangen/ai-legislation-tracker/issues](https://github.com/delschlangen/ai-legislation-tracker/issues)

2. **Include the following:**
   - Which entry is affected (include `id` if known)
   - What is incorrect
   - What the correct information is
   - Link to official source confirming the correction

3. **Use issue labels:**
   - `correction` — Factual error in existing entry
   - `outdated` — Status or date needs updating
   - `missing` — Legislation that should be added
   - `source-needed` — Source URL is broken or missing

### Example Issue Template

```
**Entry ID:** state-001
**Field:** status
**Current Value:** pending
**Correct Value:** enacted
**Source:** https://leg.colorado.gov/bills/sb24-205
**Notes:** Bill was signed into law on May 17, 2024
```

---

## Data Verification Methodology

### For Each Entry, We Verify:

| Field | Verification Source |
|:------|:-------------------|
| Status | Official legislature/agency website |
| Dates (enacted, effective, etc.) | Official government records |
| Key provisions | Bill text or official summary |
| Source URL | Confirm link is active and correct |

### Verification Process

1. **Check official source** — Visit the `source_url` for each entry
2. **Confirm status** — Verify current legislative status
3. **Update dates** — Add any new dates (enacted, effective, rescinded)
4. **Review provisions** — Ensure key provisions are accurate
5. **Update `last_verified`** — Set to current date after verification

### Source Priority

We prioritize official government sources:

| Priority | Source Type | Examples |
|:---------|:------------|:---------|
| 1 | Official legislature | congress.gov, state legislature sites |
| 2 | Official agency | NIST, FTC, EU Commission |
| 3 | Official gazette | Federal Register, Official Journal of EU |
| 4 | Government press release | White House, agency announcements |

News articles and secondary sources are used for awareness but not as primary verification sources.

---

## Verification Status

Each entry in the JSON files includes a `last_verified` field:

- **Date value** (e.g., `"2024-12-24"`) — Entry was verified on this date
- **`"needs_verification"`** — Entry has not been recently verified and may be stale

### Checking Verification Status

```bash
# Find entries needing verification
python src/query_legislation.py --search "needs_verification"

# Generate dashboard (shows verification date range)
python src/generate_dashboard.py
```

---

## Contributing Updates

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed instructions on submitting updates and new entries.

### Quick Update Process

1. Fork the repository
2. Update the relevant JSON file in `data/`
3. Set `last_verified` to today's date
4. Run `python src/generate_dashboard.py` to verify
5. Submit a pull request with source link

---

## Contact

For maintenance questions or to report urgent corrections, open a GitHub issue with the `urgent` label.
