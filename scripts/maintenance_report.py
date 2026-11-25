#!/usr/bin/env python3
"""
maintenance_report.py

Builds the weekly maintenance report: a Markdown checklist of what in the
dataset needs a human to look at it. It never edits the data. The scheduled
workflow in .github/workflows/maintenance.yml posts the result as a GitHub issue.

Sections:
- Stale entries: not verified within --max-age-days (default 183, twice a year,
  matching the review cadence in MAINTENANCE.md)
- Dates that just passed: confirm the law really took effect as recorded
- Dates coming up soon
- README dates now in the past
- Entries not yet confirmed against a primary source
- Broken source links (with --links, needs network)
- Upstream changes from official APIs (with --upstream, needs network)

Usage:
    python3 scripts/maintenance_report.py                     # offline sections only
    python3 scripts/maintenance_report.py --links --upstream  # everything
    python3 scripts/maintenance_report.py --output report.md --attention-file attention.txt

The exit code is 0 whenever a report was produced, even one full of findings:
findings are for a person to act on, not a build failure.
"""

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
README = ROOT / "README.md"

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_dashboard import key_dates  # noqa: E402

FILES = ("us_federal_actions", "us_state_bills", "international_frameworks")
IN_FORCE_STATUSES = {"enacted", "active", "adopted"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REPO_URL = "https://github.com/delschlangen/ai-legislation-tracker"
SITE_URL = "https://delschlangen.github.io/ai-legislation-tracker/"


def load_records(data_dir=DATA_DIR):
    records = []
    for name in FILES:
        path = Path(data_dir) / f"{name}.json"
        if path.exists():
            records.extend(json.loads(path.read_text(encoding="utf-8")))
    return records


def parse_date(value):
    if isinstance(value, str) and DATE_RE.match(value):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def label(record):
    """'state-018 Artificial Intelligence Safety Measures Act (Illinois)', linked to the site."""
    where = record.get("state") or record.get("jurisdiction") or record.get("issuing_body") or ""
    title = record.get("title") or record.get("name") or record.get("id")
    link = f"[`{record.get('id')}`]({SITE_URL}#{record.get('id')})"
    return f"{link} {md(title)}" + (f" ({md(where)})" if where else "")


def md(text):
    """Keep record text from being read as Markdown structure inside a list item or table."""
    return str(text).replace("|", "\\|").replace("\n", " ").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------------------
# Offline checks
# ---------------------------------------------------------------------------

def stale_entries(records, today, max_age_days):
    """Records whose last check is older than max_age_days, oldest first.
    The needs_verification sentinel counts as never checked."""
    stale = []
    for record in records:
        checked = record.get("last_verified")
        if checked == "needs_verification":
            stale.append((None, record))
            continue
        when = parse_date(checked)
        if when is None or (today - when).days > max_age_days:
            stale.append(((today - when).days if when else None, record))
    # Never verified first, then oldest first.
    return sorted(stale, key=lambda pair: (pair[0] is not None, -(pair[0] or 0)))


def verification_backlog(records):
    """Records not confirmed against a primary source, grouped by how they were checked."""
    groups = {"unconfirmed": [], "secondary": [], "not recorded": []}
    for record in records:
        level = record.get("verification")
        if level == "primary":
            continue
        groups[level if level in groups else "not recorded"].append(record)
    return groups


def dated_stages(records, statuses=IN_FORCE_STATUSES):
    """(date, record, what happens) for every dated stage of in-force records."""
    stages = []
    for record in records:
        if str(record.get("status", "")).lower() not in statuses:
            continue
        for when, what in key_dates(record):
            parsed = parse_date(when)
            if parsed:
                stages.append((parsed, record, what))
    return sorted(stages, key=lambda item: (item[0], str(item[1].get("id"))))


def upcoming(records, today, within_days):
    end = today + timedelta(days=within_days)
    return [s for s in dated_stages(records) if today < s[0] <= end]


def recently_passed(records, today, within_days):
    """Stages whose date arrived recently. A law can be delayed, enjoined or
    amended right before its start date, so each one is worth confirming."""
    start = today - timedelta(days=within_days)
    return [s for s in dated_stages(records) if start <= s[0] <= today]


README_ROW = re.compile(r"^\|\s*\*{0,2}(\d{4}-\d{2}-\d{2})\*{0,2}\s*\|(.+)$")


def readme_rows_in_past(readme_text, today):
    """Rows of the README's hand-written 'Upcoming effective dates' table whose date has passed."""
    rows = []
    in_section = False
    for line in readme_text.splitlines():
        if line.startswith("#"):
            in_section = "upcoming effective dates" in line.lower()
            continue
        if not in_section:
            continue
        match = README_ROW.match(line.strip())
        if match:
            when = parse_date(match.group(1))
            if when and when < today:
                cells = [c.strip() for c in match.group(2).split("|") if c.strip()]
                rows.append((when, " · ".join(cells[:2])))
    return rows


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_offline_sections(records, today, max_age_days, readme_text):
    """Returns (markdown, number of items needing attention)."""
    out = []
    attention = 0

    stale = stale_entries(records, today, max_age_days)
    out.append(f"## Stale entries ({len(stale)})\n")
    out.append(f"Not verified in the last {max_age_days} days. Re-check each against its source, "
               "then update `last_verified` and `verification`.\n")
    if stale:
        attention += len(stale)
        for age, record in stale:
            when = "never verified" if age is None else f"last verified {record.get('last_verified')}, {age} days ago"
            out.append(f"- [ ] {label(record)}: {when}")
    else:
        out.append("None. Every entry was checked recently.")
    out.append("")

    passed = recently_passed(records, today, 60)
    out.append(f"## Dates that just passed ({len(passed)})\n")
    out.append("These dates arrived in the last 60 days. Confirm each law really took effect as recorded, "
               "and was not delayed, enjoined or amended at the last minute.\n")
    if passed:
        attention += len(passed)
        for when, record, what in passed:
            out.append(f"- [ ] {when.isoformat()}: {label(record)}: {md(what)}")
    else:
        out.append("None.")
    out.append("")

    soon = upcoming(records, today, 60)
    out.append(f"## Coming up in the next 60 days ({len(soon)})\n")
    out.append("No action needed yet. Worth watching for a last-minute delay.\n")
    if soon:
        for when, record, what in soon:
            out.append(f"- {when.isoformat()}: {label(record)}: {md(what)}")
    else:
        out.append("None.")
    out.append("")

    past_rows = readme_rows_in_past(readme_text, today) if readme_text else []
    out.append(f"## README dates now in the past ({len(past_rows)})\n")
    if past_rows:
        attention += len(past_rows)
        out.append("The \"Upcoming effective dates\" table in README.md is written by hand. Remove or update these rows.\n")
        for when, text in past_rows:
            out.append(f"- [ ] {when.isoformat()}: {md(text)}")
    else:
        out.append("None.")
    out.append("")

    backlog = verification_backlog(records)
    total = sum(len(v) for v in backlog.values())
    out.append(f"## Not yet confirmed against a primary source ({total})\n")
    out.append("Moving these to `primary` is the top open task in MAINTENANCE.md. "
               "Listed for reference; they are not counted as new action items each week.\n")
    for level, items in backlog.items():
        if items:
            ids = ", ".join(f"`{r.get('id')}`" for r in items)
            out.append(f"- **{level}** ({len(items)}): {ids}")
    out.append("")

    return "\n".join(out), attention


def build_report(records, today, max_age_days=183, readme_text="", links=False, upstream=False,
                 fetch=None, timeout=20):
    """Returns (markdown, attention count)."""
    sections = []
    attention = 0

    offline, count = render_offline_sections(records, today, max_age_days, readme_text)
    attention += count

    if upstream:
        import upstream_check
        results = upstream_check.check_all(records, fetch=fetch, timeout=timeout)
        text, count = upstream_check.render_markdown(results)
        sections.append(text)
        attention += count

    if links:
        import link_check
        results = link_check.check_all(records, timeout=timeout)
        text, count = link_check.render_markdown(results)
        sections.append(text)
        attention += count

    sections.append(offline)

    header = [
        f"Automated maintenance report for {today.isoformat()}. "
        f"**{attention} item(s) need a look.**",
        "",
        "This report only reads the data and official sources. It never edits a record. "
        "Changing a record, and its `last_verified` date, stays a human decision.",
        "",
        f"Generated by `scripts/maintenance_report.py`. See [MAINTENANCE.md]({REPO_URL}/blob/main/MAINTENANCE.md) "
        "for how to act on it.",
        "",
    ]
    return "\n".join(header + sections), attention


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the maintenance report (read-only).")
    parser.add_argument("--today", help="Report as of this date (YYYY-MM-DD). Default: today, UTC")
    parser.add_argument("--max-age-days", type=int, default=183,
                        help="Flag entries not verified within this many days (default 183)")
    parser.add_argument("--links", action="store_true", help="Check every source_url (needs network)")
    parser.add_argument("--upstream", action="store_true",
                        help="Compare records with official APIs (needs network; see scripts/upstream_check.py)")
    parser.add_argument("--timeout", type=int, default=20, help="Network timeout in seconds")
    parser.add_argument("--output", help="Write the report here instead of printing it")
    parser.add_argument("--attention-file", help="Also write the number of items needing a look to this file")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    today = parse_date(args.today) if args.today else datetime.now(timezone.utc).date()
    if today is None:
        parser.error("--today must be a YYYY-MM-DD date")

    readme_text = README.read_text(encoding="utf-8") if README.exists() else ""
    report, attention = build_report(
        load_records(), today, args.max_age_days, readme_text,
        links=args.links, upstream=args.upstream, timeout=args.timeout)

    if args.output:
        Path(args.output).write_text(report + "\n", encoding="utf-8")
        print(f"Report written to {args.output}: {attention} item(s) need a look")
    else:
        print(report)
    if args.attention_file:
        Path(args.attention_file).write_text(f"{attention}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
