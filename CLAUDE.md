# CLAUDE.md

Guidance for AI assistants working in this repository.

## What this is

A curated, machine-readable dataset of AI laws, regulations and governance frameworks (US federal, US state, international), plus small tools to query it and a static website that reads it. The author is a single maintainer. The project's stated principle: **a tracker that is confidently wrong is worse than one that is visibly incomplete.** Accuracy and honesty about verification come before coverage.

This is a research tool, not legal advice. Never write copy that implies otherwise.

## Layout

| Path | Purpose |
|:-----|:--------|
| `data/*.json` | The dataset. **The single source of truth.** Three files, each a JSON list of records |
| `data/meta/changelog.json` | Hand-written log of what changed and when, newest first. The site shows it as "Recently changed" |
| `schema/legislation.schema.json` | JSON Schema for the data. Lists every allowed field |
| `validate.py` | Read-only data validator. Run by CI. Checks every record against the schema, then adds rules a schema cannot express |
| `src/query_legislation.py` | CLI filtering and search |
| `src/generate_dashboard.py` | Markdown summary report |
| `src/export_csv.py` | Flattens the data to CSV on demand (never committed) |
| `scripts/` | The weekly maintenance report: `maintenance_report.py`, `link_check.py`, `upstream_check.py`, `timebox.py`, which puts a time limit on each network check, and `publish_report.py`, which posts it as an issue |
| `tests/` | Standard-library `unittest` suite |
| `docs/` | GitHub Pages site: `index.html`, `app.js`, `styles.css`. No build step |
| `examples/current_landscape.md` | A committed copy of generated dashboard output |
| `CITATION.cff`, `CITATION.md` | Citation metadata. The `.cff` powers GitHub's "Cite this repository" |
| `.github/` | Issue forms, the read-only validation workflow, and the weekly maintenance workflow |

The three data files are `us_federal_actions.json` (ids `fed-NNN`), `us_state_bills.json` (`state-NNN`) and `international_frameworks.json` (`intl-NNN`).

## Commands

```bash
python3 validate.py                      # check the data; run after ANY edit to data/
python3 -m unittest discover -s tests    # tests; run after any edit to src/, validate.py or data/
python3 src/query_legislation.py --search "colorado"
python3 src/generate_dashboard.py [out.md]   # --today YYYY-MM-DD reproduces an earlier day's report
python3 src/export_csv.py [out.csv | -]
python3 scripts/maintenance_report.py    # what the weekly report would flag, offline
```

To try the site locally, serve the **repository root** (not `docs/`), because the site fetches `../data/*.json`:

```bash
python3 -m http.server 8000     # then open http://localhost:8000/docs/
```

## Rules for the data

- **Never delete a record. Never reuse or renumber an id.** Ids are permanent so citations keep resolving. A replaced law gets status `superseded`, `expired` or `rescinded` and points at its successor.
- **Supersession and amendment links are mutual.** If `fed-001` has `superseded_by: fed-009`, then `fed-009` needs `supersedes: fed-001`. The same holds for `amends` and `amended_by`. The validator fails a one-way link.
- **New records get the next unused id in their file** (highest number plus one). The file decides the prefix.
- **Use `title`, not `name`.** The `name` and `date_effective` fields were retired.
- **Every field must be in the schema.** The validator rejects any field not in `KNOWN_FIELDS`, which catches misspellings. A genuinely new field goes in `KNOWN_FIELDS` in `validate.py`, in `schema/legislation.schema.json`, and in `COLUMNS` in `src/export_csv.py`.
- **The validator runs the schema.** A record that passes `validate.py`'s own checks is then checked against the schema by a small built-in checker, so nothing the schema rejects can pass. A schema keyword that checker does not implement is an error: add support in `schema_errors`, never a silent skip. `tests/test_schema.py` runs a table of broken records through both layers; add a row there for any new rule.
- **Phased laws use `milestones`**, a list of `{"date", "description"}`, oldest first. The validator requires `effective_date` to equal the first milestone's date. Only record a stage you have read a source for, and word it as the source does: a milestone is a factual claim like any other field.
- **A law blocked by a court is `enjoined`** and needs `injunction` (court, case, date). Add `date_enjoined` too; the validator does not require it.
- **Log every data change** with an entry at the top of `data/meta/changelog.json`: `date`, `summary`, and the ids in `added` or `updated`. The validator checks that ids exist and dates run newest first. Do not log purely structural edits that change no fact.
- **Dates are `YYYY-MM-DD`, zero-padded, in ASCII digits.** Only `last_verified` may instead be the literal `needs_verification`. In Python, write `[0-9]`, not `\d`, which also matches digits from other scripts.
- **`source_url` must be a specific document**, never a bare agency homepage. The validator wants a path segment or a query; a fragment such as `#main-content` does not count, and whitespace is refused. A search-results page passes the validator but is still not a document. Prefer the official legislature, agency or gazette. News is never the citation.
- **Tags are lowercase with underscores.** Reuse existing tags (`python3 src/query_legislation.py --list-tags`) instead of inventing synonyms.
- Per-file required fields, and the status rules (`superseded` needs `superseded_by`, `vetoed` needs `veto_reason`, `enjoined` needs `injunction`), are enforced by `validate.py`. Read it rather than guessing.

### Verification is a claim. Do not make it falsely.

`last_verified` is *when* an entry was checked and `verification` is *how*:

| `verification` | Meaning |
|:--------------|:--------|
| `primary` | Confirmed against the official legislative, agency or gazette text |
| `secondary` | Confirmed against published legal analyses, not the primary text |
| `unconfirmed` | Provisional |
| *(absent)* | Not re-checked since first recorded |

Only change these when you actually performed the check, and set `verification` honestly. Editing a link or fixing structure does **not** justify bumping `last_verified`. If you could not reach a primary source, use `secondary` or `unconfirmed` and say so. Do not state that a law is in force, delayed or repealed without a source you have read.

### Things that must stay in step with the data

Adding a record, or changing a status or a date, changes things that are written by hand. Update all of these in the same change. The tests check the first four and say which is wrong; the rest you must remember:

1. README badges (`Legislation Tracked`, `Jurisdictions`), the "N entries across M jurisdictions" line, and the "At a glance" table
2. README "Upcoming effective dates" table. It must have one row for every future dated stage of an enacted, active or adopted record, and no row for a date the data does not have. Each row's Legislation cell links to its record (`...github.io/ai-legislation-tracker/#state-011`); the tests match rows to records by that link
3. `examples/current_landscape.md`, by regenerating it: `python3 src/generate_dashboard.py examples/current_landscape.md`
4. `data/meta/changelog.json`, for any change of fact. The validator checks its shape
5. `MAINTENANCE.md` review history, if you did a review pass
6. `CITATION.md` and `CITATION.cff` (`date-released`, "data current as of") after a review pass

The weekly maintenance report flags README upcoming rows once their date has passed. That is the one check time itself can trip; the tests never start failing just because a date went by.

If a record gains a field the CSV does not know, add it to `COLUMNS` in `src/export_csv.py`. A test fails otherwise, so a field is never silently dropped.

## Rules for the code

- **Python standard library only. No third-party dependencies.** This is deliberate.
- **Python 3.7+ syntax.** No walrus operator, `match`, dict union (`|`) or `str.removeprefix`. CI runs 3.7 (pinned to ubuntu-22.04, the last image with a 3.7 build) and 3.12, so the floor is tested for real.
- **Read files and write output as UTF-8** (`encoding="utf-8"`, and `sys.stdout.reconfigure` for emoji output). Without it the tools crash on Windows consoles.
- **Tools must not crash on odd data.** Use `.get()` for optional fields. The validator is the gatekeeper, but the tools should still degrade gracefully.
- **CI is read-only.** `validate.yml` must not need secrets, fetch external data, or edit and commit files. Keep it that way. It runs on every pull request and push to main, with no path filters, so it can be a required check.
- **The maintenance workflow is the one exception, and a narrow one.** `maintenance.yml` fetches official APIs and source links. It uses no secrets: the Federal Register needs no key and Congress.gov is queried with api.data.gov's public `DEMO_KEY`. **The maintainer has decided not to manage API keys**, so do not add a check that needs one. State bills stay unchecked upstream for that reason. Only its `publish` job has a write permission, `issues: write`, and it never runs on pull requests. It must never edit data or commit. The publishing logic lives in `scripts/publish_report.py` so the tests cover it: it only updates an open issue that `github-actions[bot]` itself opened, because anyone can open an issue with the same title. Pass untrusted text (API responses, record content) to `gh` as files, never through a shell and never through `${{ }}` in a `run:` line. `tests/test_publish.py` checks these guarantees against the workflow file.
- **Automation reports; people edit.** No script may change a record or bump `last_verified`. An API can say a bill had an action; only a person reading the source can say what the law now is.
- **The maintenance scripts take an injectable `fetch` or `opener`.** Tests must not touch the network. Add a fake response to `tests/test_maintenance.py` for any new upstream check.
- **One bad answer must never cost the whole report.** A garbled response, an odd JSON shape or a failed lookup becomes that record's outcome ("could not check"), and everything else is still published. `http.client` errors are not `OSError`; catch broadly at those boundaries, and never report a guess: a malformed answer is "unreadable", not "no change".
- **Only report what was compared.** A record goes under "Matched with no change" only if something was actually checked against it. An answer with nothing to compare is an error for that record.
- **Every network check runs through `timebox.run_all`**, with a deadline for the whole of each check and a budget for the run. A socket timeout alone does not stop a server that sends one byte at a time. `tests/test_publish.py` checks that the budgets and deadlines fit inside the report job's `timeout-minutes`; change them together.
- Keep the three CLIs consistent. A filter or search that works on the site should work in `query_legislation.py`, across all three files, which use different field names (`state` vs `jurisdiction` vs `issuing_body`).

## Rules for the website (`docs/`)

- It reads `data/*.json` at runtime. **Never copy data into `docs/`.**
- **Everything that comes from the data and goes into HTML is escaped** with `escapeHtml`. Values used as CSS classes go through `cssToken`, and links through `safeUrl` (http and https only). Do not interpolate a data field into a template string unescaped.
- **Keep it keyboard accessible.** Each row's title is a real `<button>` with `aria-expanded`. Filter buttons carry `aria-pressed`. Keep the two states changing together (`setPressed`, `setExpanded`). Rebuilding the table destroys the focused button, so `applyFilters` puts focus back on the same record, and Back returns focus to the link the reader left by (`focusAfterHistoryStep`).
- **Record ids are deep links:** `/docs/#state-001` opens that record. Do not break this.
- **The view is in the address bar.** Filters and sort live in the query string (`jurisdiction`, `status`, `tag`, `q`, `in_force`, `sort`), the open record in the fragment. `readUrlState` must ignore anything it does not recognise. The `popstate` handler reads the view back from the address, so Back and Forward work; anything new that belongs in the view must be read there too, and added to `viewKey`, which decides whether a history step needs the table rebuilt.
- **Only a link to a record adds a history step.** `followRecordLink` adds it with `pushState`, which fires no event, and notes on the entry being left which link was used. Everything else goes through `writeUrlState`, which replaces the current entry and keeps its state.
- **A search still being typed is never left half applied.** The box is applied 300 ms after the last key. Anything that changes or leaves the view in that gap first applies the pending text (`settleSearch`, and `applyFilters` does it itself) or drops it (`cancelSearch`, for Back and Clear).
- **Search is the same on the site and in the CLI.** `matchesFilters` in `docs/app.js` and `searchable_text` in `src/query_legislation.py` join the same fields in the same order, because a query like "Colorado SB 24-205" spans two of them; the CLI adds only `last_verified`, at the end. Change both together. A test compares the two lists.
- **Nothing date-dependent is hand-written on the site.** "Coming up", "Not yet in force", "Next stage" and "In force today" are computed from the data and the reader's date. "In force" means status `enacted`, `active` or `adopted` with no effective date still to come; the CLI and dashboard use the same rule.
- **Key Dates states a stage as fact only where the status supports it** (`stageStanding`). A pending or vetoed bill never "took effect", and a law that was enjoined, rescinded, superseded or expired reached only the stages dated before that. Other stage dates are worded as dates in the text and carry no countdown.
- Below 640px the table becomes stacked cards. Explicit `role` attributes keep table semantics, so keep them when editing the row template.
- Text on coloured backgrounds must stay at 4.5:1 contrast or better.

## Git

- Develop on the branch you were given. Do not push elsewhere or open a pull request unless asked.
- Commit messages are short and say what changed and why.
- Do not commit generated files other than `examples/current_landscape.md`. `ai_legislation.csv` is deliberately never committed.
