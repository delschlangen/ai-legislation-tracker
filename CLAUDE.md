# CLAUDE.md

Guidance for AI assistants working in this repository.

## What this is

A curated, machine-readable dataset of AI laws, regulations and governance frameworks (US federal, US state, international), plus small tools to query it and a static website that reads it. The author is a single maintainer. The project's stated principle: **a tracker that is confidently wrong is worse than one that is visibly incomplete.** Accuracy and honesty about verification come before coverage.

This is a research tool, not legal advice. Never write copy that implies otherwise.

## Layout

| Path | Purpose |
|:-----|:--------|
| `data/*.json` | The dataset. **The single source of truth.** Three files, each a JSON list of records |
| `validate.py` | Read-only data validator. Run by CI |
| `src/query_legislation.py` | CLI filtering and search |
| `src/generate_dashboard.py` | Markdown summary report |
| `src/export_csv.py` | Flattens the data to CSV on demand (never committed) |
| `tests/` | Standard-library `unittest` suite |
| `docs/` | GitHub Pages site: `index.html`, `app.js`, `styles.css`. No build step |
| `examples/current_landscape.md` | A committed copy of generated dashboard output |
| `CITATION.cff`, `CITATION.md` | Citation metadata. The `.cff` powers GitHub's "Cite this repository" |
| `.github/` | Issue forms and the read-only validation workflow |

The three data files are `us_federal_actions.json` (ids `fed-NNN`), `us_state_bills.json` (`state-NNN`) and `international_frameworks.json` (`intl-NNN`).

## Commands

```bash
python3 validate.py                      # check the data; run after ANY edit to data/
python3 -m unittest discover -s tests    # tests; run after any edit to src/, validate.py or data/
python3 src/query_legislation.py --search "colorado"
python3 src/generate_dashboard.py [out.md]
python3 src/export_csv.py [out.csv | -]
```

To try the site locally, serve the **repository root** (not `docs/`), because the site fetches `../data/*.json`:

```bash
python3 -m http.server 8000     # then open http://localhost:8000/docs/
```

## Rules for the data

- **Never delete a record. Never reuse or renumber an id.** Ids are permanent so citations keep resolving. A replaced law gets status `superseded`, `expired` or `rescinded` and points at its successor.
- **Supersession and amendment links are mutual.** If `fed-001` has `superseded_by: fed-009`, then `fed-009` needs `supersedes: fed-001`. The same holds for `amends` and `amended_by`. The validator fails a one-way link.
- **New records get the next unused id in their file** (highest number plus one). The file decides the prefix.
- **Use `title`, not `name`.** The `name` field was retired.
- **Dates are `YYYY-MM-DD`, zero-padded.** Only `last_verified` may instead be the literal `needs_verification`.
- **`source_url` must be a specific document**, never a bare agency homepage. Prefer the official legislature, agency or gazette. News is never the citation.
- **Tags are lowercase with underscores.** Reuse existing tags (`python3 src/query_legislation.py --list-tags`) instead of inventing synonyms.
- Per-file required fields, and the status rules (`superseded` needs `superseded_by`, `vetoed` needs `veto_reason`), are enforced by `validate.py`. Read it rather than guessing.

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

Adding or removing a record changes counts that are written by hand. Update all of these in the same change. The tests check the README badge total and the example report; the rest you must remember:

1. README badges (`Legislation Tracked`, `Jurisdictions`) and the "At a glance" table
2. `examples/current_landscape.md`, by regenerating it: `python3 src/generate_dashboard.py examples/current_landscape.md`
3. `MAINTENANCE.md` review history, if you did a review pass
4. `CITATION.md` and `CITATION.cff` (`date-released`, "data current as of") after a review pass

If a record gains a field the CSV does not know, add it to `COLUMNS` in `src/export_csv.py`. A test fails otherwise, so a field is never silently dropped.

## Rules for the code

- **Python standard library only. No third-party dependencies.** This is deliberate.
- **Python 3.7+ syntax.** No walrus operator, `match`, dict union (`|`) or `str.removeprefix`. CI runs 3.7 (pinned to ubuntu-22.04, the last image with a 3.7 build) and 3.12, so the floor is tested for real.
- **Read files and write output as UTF-8** (`encoding="utf-8"`, and `sys.stdout.reconfigure` for emoji output). Without it the tools crash on Windows consoles.
- **Tools must not crash on odd data.** Use `.get()` for optional fields. The validator is the gatekeeper, but the tools should still degrade gracefully.
- **CI is read-only.** The workflow must not need secrets, fetch external data, or edit and commit files. Keep it that way.
- Keep the three CLIs consistent. A filter or search that works on the site should work in `query_legislation.py`, across all three files, which use different field names (`state` vs `jurisdiction` vs `issuing_body`).

## Rules for the website (`docs/`)

- It reads `data/*.json` at runtime. **Never copy data into `docs/`.**
- **Everything that comes from the data and goes into HTML is escaped** with `escapeHtml`. Values used as CSS classes go through `cssToken`, and links through `safeUrl` (http and https only). Do not interpolate a data field into a template string unescaped.
- **Keep it keyboard accessible.** Each row's title is a real `<button>` with `aria-expanded`. Filter buttons carry `aria-pressed`. Keep the two states changing together (`setPressed`, `setExpanded`).
- **Record ids are deep links:** `/docs/#state-001` opens that record. Do not break this.
- Below 640px the table becomes stacked cards. Explicit `role` attributes keep table semantics, so keep them when editing the row template.
- Text on coloured backgrounds must stay at 4.5:1 contrast or better.

## Git

- Develop on the branch you were given. Do not push elsewhere or open a pull request unless asked.
- Commit messages are short and say what changed and why.
- Do not commit generated files other than `examples/current_landscape.md`. `ai_legislation.csv` is deliberately never committed.
