#!/usr/bin/env python3
"""
upstream_check.py

Compares records with official sources and reports where they may have moved.
It NEVER edits a record. An API knows when a bill had an action; it does not
know that a court enjoined a law or that a different bill delayed it, and it
cannot tell which bills count as AI law. So this tool says "look at this",
and a person decides what, if anything, changes in the data.

Sources, matched from each record's source_url (and bill_number for states):

- Federal Register (federalregister.gov): executive orders and rules. No key.
  For an executive order: the signing date must equal the record's date_issued,
  and the disposition notes are read for "Revoked by", "Superseded by" and
  "Amended by". For a rule: the publication date is compared with date_issued
  and flagged when they are more than 30 days apart (a rule is normally issued
  a little before it is published), and the effective date is compared when
  both sides record one. Rules carry no disposition notes.
- Congress.gov (congress.gov/bill/...): federal bills. Uses api.data.gov's
  public DEMO_KEY, which needs no sign-up. It is rate-limited, but that is
  plenty for the one or two federal bills tracked here; if the limit is hit,
  the report says so and checks again next week. Reports public-law status
  and any action newer than the record's last check.

Every record's check has a time limit on the whole of it, and the run has a
limit on all of them (see timebox.py), so a server that never finishes
answering costs that record its check, not the week's report.

Nothing here needs an API key or any setup. State bills are not checked:
every free source of state bill data needs a personal key, and the state
legislature sites refuse automated requests. State records are still covered
by the report's staleness and passed-date checks. Records no source covers
(agency guidance, state law, international law, city law) are listed as not
checked automatically.

Usage:
    python3 scripts/upstream_check.py
"""

import http.client
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import timebox

ROOT = Path(__file__).resolve().parent.parent
FILES = ("us_federal_actions", "us_state_bills", "international_frameworks")
USER_AGENT = "Mozilla/5.0 (compatible; upstream-check/1.0)"
DATE_RE = re.compile(r"^([0-9]{4}-[0-9]{2}-[0-9]{2})")   # ASCII digits only


class FetchError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def fetch_json(url, headers=None, timeout=20, opener=urllib.request.urlopen):
    """GET a URL and parse JSON. Every failure becomes a FetchError, carrying
    the HTTP status when there was one."""
    try:
        request = urllib.request.Request(url, headers=dict(
            {"User-Agent": USER_AGENT, "Accept": "application/json"}, **(headers or {})))
        with opener(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise FetchError(f"HTTP {exc.code}", exc.code)
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as exc:
        # http.client errors (a truncated body, a garbled status line) are not
        # OSError, and some carry no message at all.
        detail = str(getattr(exc, "reason", "") or exc).strip()
        raise FetchError(f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__)
    try:
        return json.loads(body.decode("utf-8"))
    except ValueError as exc:
        raise FetchError(f"the response was not valid JSON ({exc})")


def as_dict(value):
    """An API can return null, or a list, where an object was expected."""
    return value if isinstance(value, dict) else {}


def as_list(value):
    return value if isinstance(value, list) else []


def day(value):
    """The YYYY-MM-DD part of a date or timestamp, or None."""
    match = DATE_RE.match(str(value or ""))
    return match.group(1) if match else None


def days_between(first, second):
    """Whole days between two YYYY-MM-DD dates, or None if either is not a date."""
    try:
        return abs((datetime.strptime(first, "%Y-%m-%d") - datetime.strptime(second, "%Y-%m-%d")).days)
    except (TypeError, ValueError):
        return None


def newer_than_check(action_date, record):
    """True if an upstream action happened after the record was last verified."""
    checked = day(record.get("last_verified"))
    action = day(action_date)
    return bool(action and (not checked or action > checked))


# The longest all the checks together may take before no further check is
# started. See RUN_BUDGET_SECONDS in link_check.py.
RUN_BUDGET_SECONDS = 180


def record_deadline(timeout):
    """How long one record's check may take in all. Looking up an executive
    order can take three requests, each allowed the network timeout."""
    return max(30.0, 4 * timeout)


def result(record, source, **fields):
    base = {"id": record.get("id"), "title": record.get("title"), "source": source,
            "upstream_url": None, "summary": "", "findings": [], "error": None, "skipped": None}
    base.update(fields)
    return base


# ---------------------------------------------------------------------------
# Federal Register
# ---------------------------------------------------------------------------

FR_DOCUMENT = re.compile(r"federalregister\.gov/documents/\d{4}/\d{2}/\d{2}/(\d{4}-\d{3,6})(?:/|$)")
FR_EXECUTIVE_ORDER = re.compile(r"federalregister\.gov/executive-order/(\d+)")
FR_API = "https://www.federalregister.gov/api/v1"
# A rule is normally issued shortly before the Federal Register publishes it.
# A gap larger than this suggests the record's date, or its link, is wrong.
RULE_DATE_TOLERANCE_DAYS = 30
DISPOSITION = re.compile(r"(Revoked by|Superseded by|Amended by|Revokes|Supersedes|Amends)\s*:?\s*([^\r\n;]+)", re.I)


def federal_register_target(record):
    url = str(record.get("source_url") or "")
    match = FR_DOCUMENT.search(url)
    if match:
        return ("document", match.group(1))
    match = FR_EXECUTIVE_ORDER.search(url)
    if match:
        return ("executive_order", match.group(1))
    return None


def disposition_notes(doc):
    """The Federal Register has used two names for the notes field, and often
    returns both with the same text. Read one, so nothing is counted twice."""
    for key in ("executive_order_notes", "disposition_notes"):
        if doc.get(key):
            return str(doc[key]).strip()
    return ""


def find_executive_order(number, fetch, timeout):
    """The document number for an executive order, looked up by its EO number.

    The API has no filter on the EO number itself, so search the full text for
    the number among presidential documents and keep only an exact match on
    executive_order_number. Returns None when nothing matches."""
    searches = [
        [("conditions[term]", number), ("conditions[type][]", "PRESDOCU"),
         ("conditions[presidential_document_type]", "executive_order")],
        [("conditions[term]", number), ("conditions[type][]", "PRESDOCU")],
    ]
    for conditions in searches:
        query = urlencode(conditions + [("fields[]", "executive_order_number"),
                                        ("fields[]", "document_number"), ("per_page", "50")])
        found = as_dict(fetch(f"{FR_API}/documents.json?{query}", timeout=timeout))
        for doc in as_list(found.get("results")):
            doc = as_dict(doc)
            if str(doc.get("executive_order_number")) == str(number) and doc.get("document_number"):
                return doc["document_number"]
    return None


def check_federal_register(record, fetch, timeout):
    kind, value = federal_register_target(record)
    try:
        if kind == "document":
            doc = fetch(f"{FR_API}/documents/{value}.json", timeout=timeout)
        else:
            document_number = find_executive_order(value, fetch, timeout)
            if not document_number:
                return result(record, "Federal Register",
                              error=f"no Federal Register document found for Executive Order {value}")
            doc = fetch(f"{FR_API}/documents/{document_number}.json", timeout=timeout)
    except FetchError as exc:
        return result(record, "Federal Register", error=str(exc))
    if not isinstance(doc, dict) or not doc.get("document_number"):
        return result(record, "Federal Register", error="the Federal Register returned no document")

    findings = []
    status = str(record.get("status", "")).lower()
    issued = day(record.get("date_issued"))
    signing = day(doc.get("signing_date"))
    published = day(doc.get("publication_date"))
    kind_of_document = doc.get("type") or "document"
    is_order = bool(doc.get("executive_order_number"))
    # Only what was actually set against the record counts as a check. An
    # answer that leaves nothing to compare is an error, not a match.
    compared = False

    if is_order:
        if signing and issued:
            compared = True
            if signing != issued:
                findings.append(f"Signed {signing} according to the Federal Register; "
                                f"the record says date_issued {issued}")
        summary = f"EO {doc['executive_order_number']}, {kind_of_document} {doc['document_number']}"
        if signing:
            summary += f", signed {signing}"
        elif published:
            summary += f", published {published}"
    else:
        gap = days_between(published, issued)
        if gap is not None:
            compared = True
            if gap > RULE_DATE_TOLERANCE_DAYS:
                findings.append(f"Published {published} in the Federal Register, but the record says "
                                f"date_issued {issued}, {gap} days apart. Check the date and the link")
        effective = day(doc.get("effective_on"))
        recorded = day(record.get("effective_date"))
        if effective and recorded:
            compared = True
            if effective != recorded:
                findings.append(f"Effective {effective} according to the Federal Register; "
                                f"the record says effective_date {recorded}")
        summary = f"{kind_of_document} {doc['document_number']}"
        if published:
            summary += f", published {published}"
        if effective:
            summary += f", effective {effective}"

    notes = disposition_notes(doc)
    # Notes that are there were read for a revocation, which is a check of the
    # record's status even when they name none.
    if notes:
        compared = True
    dispositions = DISPOSITION.findall(notes)
    for verb, target in dispositions:
        verb_l = verb.lower()
        if verb_l in ("revoked by", "superseded by") and status not in ("rescinded", "superseded"):
            findings.append(f"Federal Register notes say \"{verb} {target.strip()}\", but the record's status is {status}")
        elif verb_l == "amended by" and not record.get("amended_by"):
            findings.append(f"Federal Register notes say \"{verb} {target.strip()}\"; the record has no amended_by link")
    if dispositions:
        summary += ". " + "; ".join(f"{verb} {target.strip()}" for verb, target in dispositions)
    if not compared:
        if not issued:
            missing = "the record has no date_issued to compare"
        elif is_order:
            missing = "the Federal Register answer has no signing date and no notes to compare with the record"
        else:
            missing = "the Federal Register answer has no publication or effective date to compare with the record"
        return result(record, "Federal Register", upstream_url=doc.get("html_url"), summary=summary,
                      error=f"nothing to compare: {missing}")
    return result(record, "Federal Register", upstream_url=doc.get("html_url"), summary=summary, findings=findings)


# ---------------------------------------------------------------------------
# Congress.gov
# ---------------------------------------------------------------------------

CONGRESS_BILL = re.compile(r"congress\.gov/bill/(\d+)(?:st|nd|rd|th)-congress/([a-z-]+)/(\d+)")
CONGRESS_TYPES = {
    "house-bill": "hr", "senate-bill": "s",
    "house-joint-resolution": "hjres", "senate-joint-resolution": "sjres",
    "house-concurrent-resolution": "hconres", "senate-concurrent-resolution": "sconres",
    "house-resolution": "hres", "senate-resolution": "sres",
}
CONGRESS_SLUGS = {v: k for k, v in CONGRESS_TYPES.items()}
CONGRESS_API = "https://api.congress.gov/v3"


def ordinal(n):
    n = int(n)
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def congress_target(record):
    match = CONGRESS_BILL.search(str(record.get("source_url") or ""))
    if match and match.group(2) in CONGRESS_TYPES:
        return match.group(1), CONGRESS_TYPES[match.group(2)], match.group(3)
    return None


# api.data.gov's shared public key. Documented for exactly this kind of light
# use, and needs no account.
CONGRESS_DEMO_KEY = "DEMO_KEY"


def check_congress(record, fetch, timeout, api_key=CONGRESS_DEMO_KEY):
    congress, bill_type, number = congress_target(record)
    try:
        payload = fetch(f"{CONGRESS_API}/bill/{congress}/{bill_type}/{number}?format=json",
                        headers={"X-Api-Key": api_key}, timeout=timeout)
    except FetchError as exc:
        hint = " (the shared public key is rate-limited; it will be tried again next week)" \
            if exc.status in (403, 429) else ""
        return result(record, "Congress.gov", error=f"{exc}{hint}")

    bill = as_dict(as_dict(payload).get("bill"))
    if not bill:
        return result(record, "Congress.gov", error="Congress.gov returned no bill")
    latest = as_dict(bill.get("latestAction"))
    # The API leaves "laws" out for a bill that is not law. A value that is
    # there but malformed tells us nothing, so say that rather than guess.
    raw_laws = bill.get("laws")
    if raw_laws is not None and not (isinstance(raw_laws, list) and all(isinstance(law, dict) for law in raw_laws)):
        return result(record, "Congress.gov", error="unexpected response: the list of laws could not be read")
    laws = [str(law["number"]) for law in as_list(raw_laws) if law.get("number")]
    status = str(record.get("status", "")).lower()
    findings = []
    if laws and status == "pending":
        findings.append(f"Became Public Law {', '.join(laws)}, but the record's status is pending")
    if not laws and status == "enacted":
        findings.append("Congress.gov records no public law, but the record's status is enacted")
    if newer_than_check(latest.get("actionDate"), record):
        findings.append(f"Action on {latest.get('actionDate')} is newer than the last check "
                        f"({record.get('last_verified')}): {latest.get('text')}")

    summary = f"Latest action {latest.get('actionDate')}: {str(latest.get('text') or '').rstrip('.')}"
    if laws:
        summary += f". Public Law {', '.join(laws)}"
    human_url = f"https://www.congress.gov/bill/{ordinal(congress)}-congress/{CONGRESS_SLUGS[bill_type]}/{number}"
    return result(record, "Congress.gov", upstream_url=human_url, summary=summary, findings=findings)


# ---------------------------------------------------------------------------
# Orchestration and report
# ---------------------------------------------------------------------------

def check_all(records, fetch=None, timeout=20, pause=0.5, deadline=None, budget=RUN_BUDGET_SECONDS):
    """Check every record a source covers. Returns one result per record, in
    the order given.

    The checks run one at a time, with `pause` seconds between them.
    deadline: seconds one record's check may take in all (default: record_deadline()).
    budget:   seconds all of them may take; records not started by then are
              reported as not checked."""
    fetch = fetch or fetch_json
    if deadline is None:
        deadline = record_deadline(timeout)

    results = [None] * len(records)
    planned = {}   # index -> (source, check)
    for index, record in enumerate(records):
        if federal_register_target(record):
            planned[index] = ("Federal Register", check_federal_register)
        elif congress_target(record):
            planned[index] = ("Congress.gov", check_congress)
        else:
            reason = ("state bills have no free official API; covered by the staleness and date checks"
                      if record.get("state") else "no official API covers this source")
            results[index] = result(record, None, skipped=reason)

    outcomes = timebox.run_all(lambda index: planned[index][1](records[index], fetch, timeout),
                               sorted(planned), seconds=deadline, workers=1, pause=pause, budget=budget)

    for index, (source, _) in planned.items():
        state, value = outcomes[index]
        record = records[index]
        if state == timebox.DONE:
            results[index] = value
        elif state == timebox.GAVE_UP:
            results[index] = result(record, source, error=f"no complete answer within {deadline:g} seconds")
        elif state == timebox.OUT_OF_TIME:
            results[index] = result(record, source,
                                    error="not checked: this run had used up its time on other records")
        else:
            # One odd response must not stop the report.
            detail = str(value).strip()
            results[index] = result(record, source, error="unexpected response: "
                                    + (f"{type(value).__name__}: {detail}" if detail else type(value).__name__))
    return results


def render_markdown(results):
    """Returns (markdown, number of records needing a look)."""
    review = [r for r in results if r["findings"]]
    errors = [r for r in results if r["error"]]
    matched = [r for r in results if not r["findings"] and not r["error"] and not r["skipped"]]
    skipped = [r for r in results if r["skipped"]]

    def ref(r):
        link = f" ([official record]({r['upstream_url']}))" if r.get("upstream_url") else ""
        return f"`{r['id']}` {str(r.get('title') or '').replace('|', '/')}{link}"

    out = [f"## Changes reported by official sources ({len(review)})\n"]
    out.append("An official API shows something newer than, or different from, the record. "
               "Read the official source, then update the record by hand if needed.\n")
    if review:
        for r in review:
            out.append(f"- [ ] {ref(r)}, via {r['source']}")
            for finding in r["findings"]:
                out.append(f"  - {finding}")
    else:
        out.append("None.")
    out.append("")

    if errors:
        out.append(f"### Could not check ({len(errors)})\n")
        for r in errors:
            out.append(f"- `{r['id']}` via {r['source']}: {r['error']}")
        out.append("")

    out.append(f"### Matched with no change ({len(matched)})\n")
    if matched:
        for r in matched:
            out.append(f"- {ref(r)}: {r['summary']}")
    else:
        out.append("None.")
    out.append("")

    by_reason = {}
    for r in skipped:
        by_reason.setdefault(r["skipped"], []).append(f"`{r['id']}`")
    if by_reason:
        out.append(f"### Not checked automatically ({len(skipped)})\n")
        for reason, ids in by_reason.items():
            out.append(f"- {reason[0].upper() + reason[1:]}: {', '.join(ids)}")
        out.append("")

    return "\n".join(out), len(review)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    records = []
    for name in FILES:
        records.extend(json.loads((ROOT / "data" / f"{name}.json").read_text(encoding="utf-8")))
    text, _ = render_markdown(check_all(records))
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
