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
  Checks the signing date against the record and reads the disposition notes
  for "Revoked by", "Superseded by" and "Amended by".
- Congress.gov (congress.gov/bill/...): federal bills. Uses the key in
  CONGRESS_GOV_API_KEY, or api.data.gov's shared DEMO_KEY, which is heavily
  rate-limited but enough for the one or two federal bills tracked here.
  Reports public-law status and any action newer than the record's last check.
- Open States (state bills): needs OPENSTATES_API_KEY; skipped without one.
  The session for each bill is worked out from its official URL. Reports any
  action newer than the record's last check.

Records no source covers (agency guidance, international law, city law) are
listed as not checked automatically.

Usage:
    python3 scripts/upstream_check.py
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

ROOT = Path(__file__).resolve().parent.parent
FILES = ("us_federal_actions", "us_state_bills", "international_frameworks")
USER_AGENT = "Mozilla/5.0 (compatible; upstream-check/1.0)"
DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


class FetchError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def fetch_json(url, headers=None, timeout=20):
    """GET a URL and parse JSON. Raises FetchError with the HTTP status if any."""
    request = urllib.request.Request(url, headers=dict({"User-Agent": USER_AGENT, "Accept": "application/json"},
                                                       **(headers or {})))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise FetchError(f"HTTP {exc.code}", exc.code)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise FetchError(str(getattr(exc, "reason", exc)))


def day(value):
    """The YYYY-MM-DD part of a date or timestamp, or None."""
    match = DATE_RE.match(str(value or ""))
    return match.group(1) if match else None


def newer_than_check(action_date, record):
    """True if an upstream action happened after the record was last verified."""
    checked = day(record.get("last_verified"))
    action = day(action_date)
    return bool(action and (not checked or action > checked))


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
        found = fetch(f"{FR_API}/documents.json?{query}", timeout=timeout)
        for doc in found.get("results") or []:
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

    findings = []
    status = str(record.get("status", "")).lower()
    signing = day(doc.get("signing_date"))
    published = day(doc.get("publication_date"))
    if doc.get("executive_order_number") and signing and record.get("date_issued") and signing != record.get("date_issued"):
        findings.append(f"Signed {signing} according to the Federal Register; the record says date_issued {record.get('date_issued')}")

    notes = disposition_notes(doc)
    dispositions = DISPOSITION.findall(notes)
    for verb, target in dispositions:
        verb_l = verb.lower()
        if verb_l in ("revoked by", "superseded by") and status not in ("rescinded", "superseded"):
            findings.append(f"Federal Register notes say \"{verb} {target.strip()}\", but the record's status is {status}")
        elif verb_l == "amended by" and not record.get("amended_by"):
            findings.append(f"Federal Register notes say \"{verb} {target.strip()}\"; the record has no amended_by link")

    eo = f"EO {doc['executive_order_number']}, " if doc.get("executive_order_number") else ""
    summary = f"{eo}{doc.get('type') or 'document'} {doc.get('document_number')}, " \
              f"{'signed ' + signing if signing else 'published ' + str(published)}"
    if dispositions:
        summary += ". " + "; ".join(f"{verb} {target.strip()}" for verb, target in dispositions)
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


def congress_target(record):
    match = CONGRESS_BILL.search(str(record.get("source_url") or ""))
    if match and match.group(2) in CONGRESS_TYPES:
        return match.group(1), CONGRESS_TYPES[match.group(2)], match.group(3)
    return None


def check_congress(record, fetch, timeout, api_key):
    congress, bill_type, number = congress_target(record)
    try:
        payload = fetch(f"{CONGRESS_API}/bill/{congress}/{bill_type}/{number}?format=json",
                        headers={"X-Api-Key": api_key}, timeout=timeout)
    except FetchError as exc:
        hint = " (the shared DEMO_KEY may be rate-limited; set CONGRESS_GOV_API_KEY)" \
            if api_key == "DEMO_KEY" and exc.status in (403, 429) else ""
        return result(record, "Congress.gov", error=f"{exc}{hint}")

    bill = payload.get("bill") or {}
    latest = bill.get("latestAction") or {}
    laws = [law.get("number") for law in bill.get("laws") or [] if law.get("number")]
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
# Open States
# ---------------------------------------------------------------------------

OPENSTATES_API = "https://v3.openstates.org"


def ordinal(n):
    n = int(n)
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def normalise_identifier(bill_number):
    """'S6953B' -> 'S 6953', 'SB 942, as amended by AB 853' -> 'SB 942', 'SB 24-205' unchanged."""
    first = str(bill_number or "").split(",")[0].strip()
    match = re.match(r"^([A-Za-z]+)\s*(\d+(?:-\d+)?)", first)
    if not match:
        return None
    return f"{match.group(1).upper()} {match.group(2)}"


def year_of(record):
    for field in ("date_introduced", "date_enacted", "effective_date"):
        value = day(record.get(field))
        if value:
            return int(value[:4])
    return None


def openstates_target(record):
    """(jurisdiction, session, identifier, how the session was found), or None.

    Session names are each state's own, as Open States uses them. Where the
    official URL names the session it is used; otherwise it is worked out from
    the record's dates and marked as such, because that guess can be wrong."""
    state = record.get("state")
    url = str(record.get("source_url") or "")
    identifier = normalise_identifier(record.get("bill_number"))
    if not state or not identifier:
        return None
    parts = urlsplit(url)
    query = parse_qs(parts.query)
    year = year_of(record)

    if state == "California":
        match = re.search(r"bill_id=(\d{8})", url)
        if match:
            return state, match.group(1), identifier, "from the official URL"
    elif state == "Illinois":
        if "GA" in query:
            return state, ordinal(query["GA"][0]), identifier, "from the official URL"
        match = re.search(r"PublicActs/View/(\d+)-", url)
        if match:
            return state, ordinal(match.group(1)), identifier, "from the Public Act number"
        if year:
            start = year if year % 2 else year - 1
            return state, ordinal((start - 1817) // 2), identifier, "worked out from the record's dates"
    elif state == "Colorado":
        match = re.search(r"/bills/[a-z]+(\d{2})-\d+", url)
        if match:
            return state, f"20{match.group(1)}A", identifier, "from the official URL"
    elif state == "Texas":
        if "LegSess" in query:
            match = re.match(r"(\d+)R$", query["LegSess"][0])
            if match:
                return state, match.group(1), identifier, "from the official URL"
    elif state == "Utah":
        match = re.search(r"le\.utah\.gov/~(\d{4})/", url)
        if match:
            return state, match.group(1), identifier, "from the official URL"
    elif state == "New York":
        match = re.search(r"/legislation/bills/(\d{4})/", url)
        if match:
            start = int(match.group(1))
            start = start if start % 2 else start - 1
            return state, f"{start}-{start + 1}", identifier, "from the official URL"
    elif state == "Connecticut":
        match = re.search(r"cga\.ct\.gov/(\d{4})/", url)
        if match:
            return state, match.group(1), identifier, "from the official URL"
        if year:
            return state, str(year), identifier, "worked out from the record's dates"
    elif state == "Tennessee" and year:
        start = year if year % 2 else year - 1
        return state, str((start - 1797) // 2), identifier, "worked out from the record's dates"
    return None


def check_openstates(record, fetch, timeout, api_key):
    jurisdiction, session, identifier, how = openstates_target(record)
    query = urlencode({"jurisdiction": jurisdiction, "session": session, "identifier": identifier})
    try:
        payload = fetch(f"{OPENSTATES_API}/bills?{query}", headers={"X-API-KEY": api_key}, timeout=timeout)
    except FetchError as exc:
        return result(record, "Open States", error=f"{exc} looking up {identifier}, session {session} ({how})")

    bills = payload.get("results") or []
    if not bills:
        return result(record, "Open States",
                      error=f"{identifier} not found in session {session} ({how}). Check the session mapping.")
    bill = bills[0]
    findings = []
    latest_date = bill.get("latest_action_date")
    latest_text = bill.get("latest_action_description")
    if newer_than_check(latest_date, record):
        findings.append(f"Action on {day(latest_date)} is newer than the last check "
                        f"({record.get('last_verified')}): {latest_text}")
    status = str(record.get("status", "")).lower()
    if status == "pending" and day(bill.get("latest_passage_date")):
        findings.append(f"Passed a chamber on {day(bill.get('latest_passage_date'))}; the record's status is pending")

    summary = f"{identifier} ({session}): latest action {day(latest_date)}: {latest_text}"
    return result(record, "Open States", upstream_url=bill.get("openstates_url"), summary=summary, findings=findings)


# ---------------------------------------------------------------------------
# Orchestration and report
# ---------------------------------------------------------------------------

def check_all(records, fetch=None, timeout=20, environ=None, pause=0.5):
    """Check every record a source covers. Returns one result per record."""
    fetch = fetch or fetch_json
    environ = os.environ if environ is None else environ
    congress_key = environ.get("CONGRESS_GOV_API_KEY") or "DEMO_KEY"
    openstates_key = environ.get("OPENSTATES_API_KEY") or ""

    results = []
    for record in records:
        if federal_register_target(record):
            results.append(check_federal_register(record, fetch, timeout))
        elif congress_target(record):
            results.append(check_congress(record, fetch, timeout, congress_key))
        elif record.get("state") and openstates_target(record):
            if openstates_key:
                results.append(check_openstates(record, fetch, timeout, openstates_key))
            else:
                results.append(result(record, "Open States",
                                      skipped="needs an Open States API key (OPENSTATES_API_KEY)"))
                continue
        else:
            results.append(result(record, None, skipped="no official API covers this source"))
            continue
        if pause:
            time.sleep(pause)
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
