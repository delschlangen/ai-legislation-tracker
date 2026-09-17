# Dataset Maintenance

How this dataset is kept current, how entries are verified, and how to report a problem.

---

## Review Schedule

This is a single-maintainer project. The schedule below is what can realistically be sustained, not an aspiration.

| Cadence | Scope |
|:--------|:------|
| **Twice yearly** | Re-check every entry's status, effective date and source link |
| **On report** | Any entry flagged through an issue is checked as soon as practical |

Earlier versions of this file promised quarterly reviews and one-week turnarounds on major events. That commitment was not met — seven consecutive quarterly reviews were missed between December 2024 and September 2026, during which the Colorado entry went stale while the statute it described was delayed, enforcement-stayed and finally repealed. A promise the project cannot keep is worse than an honest one, so the cadence above replaces it.

**The dataset tells you its own age.** Every entry carries `last_verified`. The site shows the range, and `python3 src/generate_dashboard.py` prints it. Trust that field over anything written in prose.

---

## Review History

| Review | Date | Scope |
|:-------|:-----|:------|
| Full dataset review | 2026-09-17 | 30 of 44 entries corrected or added; schema extended for supersession |
| Full dataset review | 2024-12-24 | Original 28 entries verified |

---

## Verification Status

Every entry may carry a `verification` field recording **how** it was last checked. This is separate from `last_verified`, which records **when**.

| Value | Meaning |
|:------|:--------|
| `primary` | Confirmed against the official legislature, agency or gazette text |
| `secondary` | Confirmed against multiple independent published legal analyses, not the primary text |
| `unconfirmed` | Provisional. Corroboration was thin or a detail could not be pinned down |
| *(absent)* | As originally recorded and not re-checked since |

`last_verified` may also be the literal string `needs_verification`, meaning nobody has checked the entry at all. The site displays the verification status on each record, so a reader can see how much weight it carries.

**Current state:** the September 2026 review was conducted against published legal analyses rather than primary texts, because the primary sources were not reachable from the environment the review ran in. Those entries are marked `secondary`. Moving them to `primary` is the top open task.

### Checking status

```bash
# Entries nobody has ever verified
python3 src/query_legislation.py --search "needs_verification"

# Verification date range and full status breakdown
python3 src/generate_dashboard.py

# Structural problems: duplicate ids, missing fields, bad dates, bare-domain URLs
python3 validate.py
```

---

## Verification Method

For each entry, confirm:

1. The **status** is current — not superseded, repealed, expired, amended or enjoined
2. The **dates** match the official record, especially the effective date
3. The **source URL** resolves and points at the specific document, not an agency homepage
4. The **summary and key provisions** still describe the instrument accurately
5. Any **supersession** is recorded through `superseded_by`, `supersedes`, `amends` or `amended_by`

Then set `last_verified` to the date of the check and `verification` to the method used.

### Source priority

| Tier | Source | Use |
|:----:|:-------|:----|
| 1 | Official legislature, agency or gazette text | The citation. Always prefer this |
| 2 | Government summaries and press releases | Acceptable supporting context |
| 3 | Published legal analyses from established firms | Corroboration only; mark the entry `secondary` |
| 4 | News reporting | Signal that something changed. Never the citation |

---

## Handling Superseded Law

**Records are never deleted and ids are never reused.** When a law is replaced:

1. Set the old record's `status` to `superseded`, `expired` or `rescinded`
2. Add `date_superseded` and `superseded_by` pointing at the successor's id
3. Create the successor as a new record with `supersedes` pointing back
4. Update the old record's summary to explain what happened

This is deliberate. A citation to `state-001` written in 2024 still resolves today and now tells the reader that Colorado SB 24-205 was repealed before it ever took effect. Deleting the record would break that.

---

## Reporting a Problem

Open an issue. No Git knowledge required:

- [Report an incorrect or out-of-date entry](https://github.com/delschlangen/ai-legislation-tracker/issues/new?template=stale-entry.yml)
- [Suggest a law to add](https://github.com/delschlangen/ai-legislation-tracker/issues/new?template=new-law.yml)

Include the entry id or title, what is wrong, what it should say, and an official source link. Corrections are the most useful contribution to this project.

---

## Updating an Entry

1. Edit the relevant file in `data/`
2. Update `last_verified` and `verification`
3. Run `python3 validate.py`
4. Open a pull request

The website reads `data/*.json` directly, so there is no second copy to keep in sync. The same validator runs automatically on pull requests; it only reads files and reports problems, and never changes anything.

---

## Contact

Open an issue on the repository. For anything else, see the maintainer link in the README.
