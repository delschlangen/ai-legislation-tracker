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

**A weekly report keeps the cadence honest.** Between reviews, the [automated maintenance report](#automated-maintenance-report) lists what has gone stale or changed upstream, so nothing waits six months unnoticed.

---

## Automated Maintenance Report

Every Monday a GitHub Actions workflow builds a checklist and posts it as one issue titled **Maintenance report**. It updates that same issue each week rather than opening new ones, and adds a comment only when there is more to do than the week before.

| Section | What it means | What to do |
|:--------|:--------------|:-----------|
| Changes reported by official sources | The Federal Register, Congress.gov or Open States shows something newer than, or different from, the record | Read the official source. Update the record if the law really changed |
| Stale entries | Not verified in the last 183 days | Re-check the entry, then update `last_verified` and `verification` |
| Dates that just passed | An effective date or phase arrived in the last 60 days | Confirm the law took effect as recorded and was not delayed or enjoined |
| README dates now in the past | A row in the README's hand-written upcoming table has passed | Remove or update the row |
| Broken source links | The official page returns 404 or 410, or the host is gone | Find the current URL for the same document |
| Could not check automatically | The site refused an automated request or timed out | Usually bot protection. Open the link in a browser if in doubt |

**It never edits the data.** An API knows a bill had an action. It does not know that a court enjoined the law or a different bill delayed it, and it cannot judge what counts as AI law. So the report says "look at this", and a person decides. A record's `last_verified` date moves only when someone actually checked it.

### What is checked upstream

| Source | Records | Key |
|:-------|:--------|:----|
| Federal Register | Executive orders and rules whose `source_url` is on federalregister.gov. Checks the signing date and the "Revoked by", "Superseded by" and "Amended by" notes | None needed |
| Congress.gov | Federal bills whose `source_url` is on congress.gov. Checks public-law status and any action newer than the last check | Optional. Without one it uses api.data.gov's shared `DEMO_KEY`, which is rate-limited |
| Open States | State bills. The session is worked out from the official URL, or from the record's dates where the URL does not say | Required. State bills are skipped without one |

Agency guidance, city law and international law have no comparable single API. The report lists them as not checked automatically, and they stay on the twice-yearly review.

### Adding API keys

Both keys are free. Add each one as a repository secret: **Settings → Secrets and variables → Actions → New repository secret**.

| Secret name | Where to get it |
|:------------|:----------------|
| `CONGRESS_GOV_API_KEY` | Sign up at [api.congress.gov](https://api.congress.gov/) |
| `OPENSTATES_API_KEY` | Request one through the [Open States API documentation](https://docs.openstates.org/api-v3/) |

The workflow reads them only in its read-only report job, and sends each only to its own service.

### Running it now

Open the **Actions** tab, choose **Maintenance report**, then **Run workflow**. The report also appears on the run's summary page. GitHub pauses scheduled workflows in a repository with no activity for 60 days; if the issue stops updating, re-enable the workflow from the same page.

To build the offline parts locally:

```bash
python3 scripts/maintenance_report.py                     # stale entries, dates, README
python3 scripts/maintenance_report.py --links --upstream  # also links and official APIs
```

---

## Review History

| Review | Date | Scope |
|:-------|:-----|:------|
| Targeted update | 2026-11-24 | 3 entries added (Illinois SB 315, California AI Transparency Act, EO 14409) and 1 corrected (New York RAISE Act), all checked against published legal analyses and official bill pages. **Not a full review:** every other entry keeps its earlier `last_verified` date |
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
# Entries nobody has ever verified (none today, so this returns nothing)
python3 src/query_legislation.py --search "needs_verification"

# Entries confirmed only against secondary sources, still waiting for a primary check
# (search also matches the word anywhere in a record, so skim the results)
python3 src/query_legislation.py --search "secondary"

# Verification date range and full status breakdown
python3 src/generate_dashboard.py

# Structural problems: duplicate ids, missing or misspelled fields, bad dates,
# bare-domain URLs, one-way supersession links, a malformed change log
python3 validate.py

# Everything the weekly report would flag, offline
python3 scripts/maintenance_report.py
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
3. Create the successor as a new record with `supersedes` pointing back. The validator fails a link recorded on only one side
4. Update the old record's summary to explain what happened

This is deliberate. A citation to `state-001` written in 2024 still resolves today and now tells the reader that Colorado SB 24-205 was repealed before it ever took effect. Deleting the record would break that.

## Handling Enjoined Law

When a court blocks enforcement of a law, set its `status` to `enjoined`, add `injunction` naming the court, the case and the date, and add `date_enjoined`. If the injunction is lifted, set the status back and keep the history in the summary. The site shows an enjoined law with its own status and filter button.

## Phased Laws

A law that applies in stages keeps its first stage in `effective_date`, and lists every stage in `milestones`, oldest first:

```json
"milestones": [
  {"date": "2026-08-02", "description": "Provider disclosure duties begin"},
  {"date": "2027-01-01", "description": "Platform duties begin"}
]
```

The site's "Coming up" list, each record's key dates, the dashboard and the weekly report all read these, so no upcoming-date table has to be kept by hand.

---

## Reporting a Problem

Open an issue. No Git knowledge required:

- [Report an incorrect or out-of-date entry](https://github.com/delschlangen/ai-legislation-tracker/issues/new?template=stale-entry.yml)
- [Suggest a law to add](https://github.com/delschlangen/ai-legislation-tracker/issues/new?template=new-law.yml)

Include the entry id or title, what is wrong, what it should say, and an official source link. Corrections are the most useful contribution to this project.

---

## Updating an Entry

1. Edit the relevant file in `data/`
2. Update `last_verified` and `verification`, if you actually re-checked the entry
3. Add an entry at the top of `data/meta/changelog.json` saying what changed. The site shows the latest ones under "Recently changed"
4. Run `python3 validate.py`
5. Open a pull request

The website reads `data/*.json` directly, so there is no second copy to keep in sync. The same validator runs automatically on pull requests; it only reads files and reports problems, and never changes anything.

---

## Contact

Open an issue on the repository. For anything else, see the maintainer link in the README.
