# Citing the AI Legislation Tracker

## How to Cite This Dataset

When referencing this dataset in academic papers, policy reports, or other publications, please use one of the citation formats below.

---

## BibTeX

```bibtex
@misc{schlangen2026ailegislation,
  author       = {Schlangen, Del},
  title        = {{AI Legislation Tracker}: A Curated Dataset of Global AI Laws and Governance Frameworks},
  year         = {2026},
  publisher    = {GitHub},
  howpublished = {\url{https://github.com/delschlangen/ai-legislation-tracker}},
  note         = {Dataset tracking US federal, US state, and international AI legislation. Data current as of September 2026.}
}
```

---

## Citation Formats

### APA (7th Edition)

Schlangen, D. (2026). *AI Legislation Tracker: A curated dataset of global AI laws and governance frameworks* [Data set]. GitHub. https://github.com/delschlangen/ai-legislation-tracker

### Chicago (17th Edition)

Schlangen, Del. "AI Legislation Tracker: A Curated Dataset of Global AI Laws and Governance Frameworks." GitHub, 2026. https://github.com/delschlangen/ai-legislation-tracker.

### Bluebook (Legal Citation)

Del Schlangen, *AI Legislation Tracker: A Curated Dataset of Global AI Laws and Governance Frameworks*, GitHub (2026), https://github.com/delschlangen/ai-legislation-tracker.

### IEEE

D. Schlangen, "AI Legislation Tracker: A Curated Dataset of Global AI Laws and Governance Frameworks," GitHub, 2026. [Online]. Available: https://github.com/delschlangen/ai-legislation-tracker

---

## Data Currency Limitations

**Important:** This dataset is a point-in-time snapshot of AI legislation status. Please note:

1. **Legislation changes frequently.** Bills may be amended, enacted, vetoed, or rescinded between dataset updates.

2. **Verification dates vary by entry.** Each record carries `last_verified` (when it was checked) and may carry `verification` (how it was checked: `primary`, `secondary` or `unconfirmed`). Cite the entry's own dates rather than a single date for the dataset.

3. **Not comprehensive.** This dataset tracks selected significant legislation and does not claim to include every AI-related law globally.

4. **Not legal advice.** Always verify current status with official government sources before making compliance or legal decisions.

When citing, we recommend including the access date:

> Schlangen, D. (2026). *AI Legislation Tracker* [Data set]. GitHub. https://github.com/delschlangen/ai-legislation-tracker (accessed September 17, 2026).

---

## Citing Specific Legislation

When referencing specific legislation from this dataset, cite the primary source (the official government document) rather than this tracker. This dataset provides `source_url` fields for each entry to facilitate proper citation of primary sources.

Example:
> Colorado SB 24-205, Consumer Protections for Artificial Intelligence (2024). Available at: https://leg.colorado.gov/bills/sb24-205

---

## Citing a Specific Version

This dataset changes as the law does. For anything that needs to be reproducible, cite a commit rather than the branch:

```
https://github.com/delschlangen/ai-legislation-tracker/blob/<commit-sha>/data/us_state_bills.json
```

Record ids are permanent and are never reused, so a citation to an entry stays resolvable even after the law behind it is repealed. Colorado `state-001` still resolves today, and its record now shows that SB 24-205 was superseded by SB 26-189 before it ever took effect.

---

## Questions

For citation questions or to request additional formats, please open a GitHub issue.
