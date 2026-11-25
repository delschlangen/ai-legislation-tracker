#!/usr/bin/env python3
"""
link_check.py

Checks that every record's source_url still answers. Read-only; standard
library only. Run by the weekly maintenance workflow, or by hand:

    python3 scripts/link_check.py

Outcomes:
- ok:          the page answered
- moved:       it answered, but only after redirecting to a different site
- broken:      404 or 410 to a full request, or the host does not exist, on two
               tries. Needs a new link
- blocked:     the site refused an automated request (401, 403, 429, 451, 503).
               Common for government sites; open the link in a browser to check
- unreachable: a timeout, a connection or DNS fault, or a garbled response,
               after one retry

Only "broken" counts as an action item. "blocked" and "unreachable" are often
the site's bot protection or a passing outage, so they are listed separately
rather than reported as failures.

Nothing a server sends can stop the run: every failure for one link becomes
that link's outcome, and the other links are still checked.
"""

import json
import socket
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
FILES = ("us_federal_actions", "us_state_bills", "international_frameworks")

# A generic client name. Nothing here identifies the project or its owner.
USER_AGENT = "Mozilla/5.0 (compatible; link-check/1.0)"
BLOCKED = {401, 403, 429, 451, 503}
GONE = {404, 410}
# Some servers answer HEAD wrongly, including with 404, and serve GET normally.
# So a HEAD failure with one of these codes is confirmed with a GET.
RETRY_WITH_GET = {400, 403, 404, 405, 410, 501}

# Resolver answers that mean the host really does not exist. Any other
# resolver error ("try again", "server failure") is treated as temporary.
PERMANENT_DNS_ERRORS = {socket.EAI_NONAME, getattr(socket, "EAI_NODATA", socket.EAI_NONAME)}


def _request(url, method, timeout, opener):
    request = urllib.request.Request(url, method=method, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
    })
    with opener(request, timeout=timeout) as response:
        if method == "GET":
            response.read(2048)
        return response.status, response.geturl()


def check_url(url, timeout=20, opener=urllib.request.urlopen, retries=1, pause=2.0):
    """Returns a dict: url, outcome, status, final_url, detail.

    A definite answer (the page, a 404 to a GET, a refusal) is returned at once.
    Anything that could be a passing fault is tried again first, and the last
    attempt's outcome is what is reported. No exception leaves this function."""
    result = {"url": url, "outcome": "unreachable", "status": None, "final_url": None, "detail": ""}
    for attempt in range(retries + 1):
        result.update(status=None, final_url=None)
        try:
            try:
                status, final = _request(url, "HEAD", timeout, opener)
            except urllib.error.HTTPError as exc:
                if exc.code in RETRY_WITH_GET:
                    status, final = _request(url, "GET", timeout, opener)
                else:
                    raise
            result.update(status=status, final_url=final, outcome="ok", detail="")
            if urlsplit(final).netloc.lower() != urlsplit(url).netloc.lower():
                result.update(outcome="moved", detail=f"redirects to {final}")
            return result
        except urllib.error.HTTPError as exc:
            result["status"] = exc.code
            if exc.code in GONE:
                result.update(outcome="broken", detail=f"HTTP {exc.code}")
                return result
            if exc.code in BLOCKED:
                result.update(outcome="blocked", detail=f"HTTP {exc.code}")
                return result
            result.update(outcome="unreachable", detail=f"HTTP {exc.code}")
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, socket.gaierror):
                if reason.errno in PERMANENT_DNS_ERRORS:
                    # Reported as broken only if the retry gets the same answer.
                    result.update(outcome="broken", detail="host not found")
                else:
                    result.update(outcome="unreachable",
                                  detail=f"DNS lookup failed ({reason.strerror or reason})")
            elif "CERTIFICATE_VERIFY_FAILED" in str(reason):
                # Usually a server that omits an intermediate certificate.
                # Browsers fill the gap; Python does not. Verification stays on.
                result.update(outcome="unreachable",
                              detail="the site's certificate chain is incomplete; browsers usually still open it")
                return result
            else:
                result.update(outcome="unreachable", detail=str(reason))
        except (socket.timeout, TimeoutError):
            result.update(outcome="unreachable", detail="timed out")
        except Exception as exc:  # noqa: BLE001 - deliberate; see the docstring
            # http.client errors (a garbled status line, a truncated body, too
            # many headers) are not OSError or ValueError, so catch everything.
            detail = str(exc).strip()
            result.update(outcome="unreachable",
                          detail=f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__)
        if attempt < retries:
            time.sleep(pause)
    return result


def check_all(records, timeout=20, workers=8, opener=urllib.request.urlopen, pause=2.0):
    """Check each distinct source_url once. Returns a list of results, each with
    the ids of the records that cite it."""
    by_url = {}
    for record in records:
        url = record.get("source_url")
        if isinstance(url, str) and url:
            by_url.setdefault(url, []).append(record.get("id"))

    def run(url):
        result = check_url(url, timeout=timeout, opener=opener, pause=pause)
        result["ids"] = by_url[url]
        return result

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(run, sorted(by_url)))


def render_markdown(results):
    """Returns (markdown, number of broken links)."""
    groups = {}
    for result in results:
        groups.setdefault(result["outcome"], []).append(result)

    def lines(items, checkbox):
        out = []
        for r in sorted(items, key=lambda x: x["ids"]):
            ids = ", ".join(f"`{i}`" for i in r["ids"])
            box = "- [ ] " if checkbox else "- "
            detail = f": {r['detail']}" if r["detail"] else ""
            out.append(f"{box}{ids} <{r['url']}>{detail}")
        return out

    broken = groups.get("broken", [])
    out = [f"## Source links ({len(results)} checked)\n"]
    out.append(f"### Broken ({len(broken)})\n")
    if broken:
        out.append("The page is gone (404 or 410), or the host no longer exists. "
                   "Find the current URL for the same document.\n")
        out += lines(broken, True)
    else:
        out.append("None.")
    out.append("")

    moved = groups.get("moved", [])
    if moved:
        out.append(f"### Redirects to another site ({len(moved)})\n")
        out.append("Still answering, but the address has moved. Consider citing the new location.\n")
        out += lines(moved, False)
        out.append("")

    uncertain = groups.get("blocked", []) + groups.get("unreachable", [])
    if uncertain:
        out.append(f"### Could not check automatically ({len(uncertain)})\n")
        out.append("The site refused an automated request or did not answer. "
                   "This is usually bot protection, not a dead link. Open them in a browser if in doubt.\n")
        out += lines(uncertain, False)
        out.append("")

    ok = len(groups.get("ok", []))
    out.append(f"{ok} link(s) answered normally.\n")
    return "\n".join(out), len(broken)


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
