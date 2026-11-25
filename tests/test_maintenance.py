"""
Tests for the maintenance scripts in scripts/. Standard library only, and no
network: every web request is answered by a fake.

    python3 -m unittest discover -s tests
"""

import io
import json
import socket
import sys
import unittest
import urllib.error
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import link_check  # noqa: E402
import maintenance_report as report  # noqa: E402
import upstream_check as upstream  # noqa: E402

TODAY = date(2026, 11, 25)


def rec(**fields):
    base = {"id": "state-001", "title": "Test Act", "state": "Testland", "bill_number": "HB 1",
            "status": "enacted", "summary": "S", "key_provisions": ["P"],
            "source_url": "https://legislature.example/bills/hb1", "tags": ["t"],
            "last_verified": "2026-09-17", "verification": "secondary"}
    base.update(fields)
    return base


def real_records():
    records = {}
    for name in ("us_federal_actions", "us_state_bills", "international_frameworks"):
        for r in json.loads((ROOT / "data" / f"{name}.json").read_text(encoding="utf-8")):
            records[r["id"]] = r
    return records


# ---------------------------------------------------------------------------
# maintenance_report.py
# ---------------------------------------------------------------------------

class StalenessTests(unittest.TestCase):
    def test_old_and_unverified_entries_are_stale(self):
        records = [rec(id="state-001", last_verified="2026-09-17"),
                   rec(id="state-002", last_verified="2024-12-24"),
                   rec(id="state-003", last_verified="needs_verification")]
        stale = report.stale_entries(records, TODAY, 183)
        self.assertEqual([r["id"] for _, r in stale], ["state-003", "state-002"])
        self.assertIsNone(stale[0][0])
        self.assertEqual(stale[1][0], (TODAY - date(2024, 12, 24)).days)

    def test_boundary_is_not_stale(self):
        exactly = (TODAY.toordinal() - 183)
        when = date.fromordinal(exactly).isoformat()
        self.assertEqual(report.stale_entries([rec(last_verified=when)], TODAY, 183), [])


class DateTests(unittest.TestCase):
    records = [
        rec(id="state-001", effective_date="2026-12-01"),
        rec(id="state-002", effective_date="2026-10-10"),
        rec(id="state-003", status="superseded", superseded_by="state-001", effective_date="2026-12-05"),
        rec(id="state-004", effective_date="2025-01-01", milestones=[
            {"date": "2025-01-01", "description": "First"},
            {"date": "2027-06-01", "description": "Second"}]),
    ]

    def test_upcoming_includes_milestones_and_skips_dead_laws(self):
        soon = report.upcoming(self.records, TODAY, 60)
        self.assertEqual([(d.isoformat(), r["id"]) for d, r, _ in soon], [("2026-12-01", "state-001")])
        later = report.upcoming(self.records, TODAY, 365)
        self.assertIn(("2027-06-01", "state-004", "Second"), [(d.isoformat(), r["id"], w) for d, r, w in later])
        self.assertNotIn("state-003", [r["id"] for _, r, _ in later])

    def test_recently_passed(self):
        passed = report.recently_passed(self.records, TODAY, 60)
        self.assertEqual([r["id"] for _, r, _ in passed], ["state-002"])


class ReadmeTests(unittest.TestCase):
    readme = """
## Quick Reference

### Upcoming effective dates

| Date | Jurisdiction | Legislation | What happens |
|:-----|:-------------|:------------|:-------------|
| **2026-10-01** | Connecticut | CART Act | First obligations |
| **2027-01-01** | Colorado | SB 26-189 | Takes effect |

### Another table

| **2020-01-01** | Not | in the section |
"""

    def test_only_past_rows_in_the_upcoming_table(self):
        rows = report.readme_rows_in_past(self.readme, TODAY)
        self.assertEqual([(d.isoformat(), text) for d, text in rows], [("2026-10-01", "Connecticut · CART Act")])

    def test_real_readme_parses(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("upcoming effective dates", text.lower())
        # Every row in the real table is found when it is in the past.
        self.assertTrue(report.readme_rows_in_past(text, date(2100, 1, 1)))


class ReportTests(unittest.TestCase):
    def test_offline_report_counts_attention(self):
        records = [rec(id="state-001", last_verified="2020-01-01"),
                   rec(id="state-002", effective_date="2026-10-10")]
        text, attention = report.build_report(records, TODAY, 183, "")
        self.assertEqual(attention, 2)
        self.assertIn("**2 item(s) need a look.**", text)
        self.assertIn("[ ] [`state-001`]", text)

    def test_markdown_in_titles_is_neutralised(self):
        records = [rec(title="A | B <script>", last_verified="2020-01-01")]
        text, _ = report.build_report(records, TODAY, 183, "")
        self.assertIn("A \\| B &lt;script&gt;", text)
        self.assertNotIn("<script>", text)

    def test_real_data_offline_report_runs(self):
        text, _ = report.build_report(report.load_records(), TODAY, 183, "")
        self.assertIn("## Stale entries", text)


# ---------------------------------------------------------------------------
# link_check.py
# ---------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, url, status=200):
        self.url, self.status = url, status

    def geturl(self):
        return self.url

    def read(self, n=-1):
        return b""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def opener_for(behaviour):
    """behaviour: {method: callable(request) -> FakeResponse or raise}."""
    def opener(request, timeout):
        return behaviour[request.get_method()](request)
    return opener


def http_error(code):
    def raise_it(request):
        raise urllib.error.HTTPError(request.full_url, code, "x", {}, io.BytesIO(b""))
    return raise_it


class LinkCheckTests(unittest.TestCase):
    url = "https://agency.example/doc"

    def check(self, behaviour):
        return link_check.check_url(self.url, opener=opener_for(behaviour), pause=0)

    def test_ok(self):
        self.assertEqual(self.check({"HEAD": lambda r: FakeResponse(self.url)})["outcome"], "ok")

    def test_head_refused_falls_back_to_get(self):
        result = self.check({"HEAD": http_error(405), "GET": lambda r: FakeResponse(self.url)})
        self.assertEqual(result["outcome"], "ok")

    def test_not_found_is_broken(self):
        self.assertEqual(self.check({"HEAD": http_error(404)})["outcome"], "broken")

    def test_forbidden_is_blocked_not_broken(self):
        result = self.check({"HEAD": http_error(403), "GET": http_error(403)})
        self.assertEqual(result["outcome"], "blocked")

    def test_missing_host_is_broken(self):
        def dns(request):
            raise urllib.error.URLError(socket.gaierror(-2, "Name or service not known"))
        self.assertEqual(self.check({"HEAD": dns})["outcome"], "broken")

    def test_timeout_is_unreachable_after_retry(self):
        calls = []

        def slow(request):
            calls.append(1)
            raise socket.timeout("timed out")
        result = self.check({"HEAD": slow})
        self.assertEqual(result["outcome"], "unreachable")
        self.assertEqual(len(calls), 2)

    def test_incomplete_certificate_chain_is_explained(self):
        def bad_cert(request):
            raise urllib.error.URLError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")
        result = self.check({"HEAD": bad_cert})
        self.assertEqual(result["outcome"], "unreachable")
        self.assertIn("certificate chain is incomplete", result["detail"])

    def test_redirect_to_another_site_is_moved(self):
        result = self.check({"HEAD": lambda r: FakeResponse("https://archive.example/doc")})
        self.assertEqual(result["outcome"], "moved")

    def test_report_counts_only_broken(self):
        results = [dict(url="https://a.example/x", outcome="broken", status=404, final_url=None, detail="HTTP 404", ids=["fed-001"]),
                   dict(url="https://b.example/x", outcome="blocked", status=403, final_url=None, detail="HTTP 403", ids=["fed-002"]),
                   dict(url="https://c.example/x", outcome="ok", status=200, final_url=None, detail="", ids=["fed-003"])]
        text, broken = link_check.render_markdown(results)
        self.assertEqual(broken, 1)
        self.assertIn("- [ ] `fed-001`", text)
        self.assertIn("Could not check automatically (1)", text)

    def test_shared_urls_are_checked_once(self):
        seen = []

        def head(request):
            seen.append(request.full_url)
            return FakeResponse(request.full_url)
        records = [rec(id="state-001", source_url=self.url), rec(id="state-002", source_url=self.url)]
        results = link_check.check_all(records, opener=opener_for({"HEAD": head}))
        self.assertEqual(len(seen), 1)
        self.assertEqual(results[0]["ids"], ["state-001", "state-002"])


# ---------------------------------------------------------------------------
# upstream_check.py
# ---------------------------------------------------------------------------

def fake_fetch(routes):
    """routes: [(substring, payload or Exception)]. Records each call."""
    calls = []

    def fetch(url, headers=None, timeout=20):
        calls.append((url, headers or {}))
        for needle, answer in routes:
            if needle in url:
                if isinstance(answer, Exception):
                    raise answer
                return answer
        raise upstream.FetchError("HTTP 404", 404)
    fetch.calls = calls
    return fetch


class FederalRegisterTests(unittest.TestCase):
    record = rec(id="fed-001", title="EO", status="active", date_issued="2023-10-30",
                 source_url="https://www.federalregister.gov/documents/2023/11/01/2023-24283/safe-secure")

    def test_target_parsing(self):
        self.assertEqual(upstream.federal_register_target(self.record), ("document", "2023-24283"))
        eo = rec(source_url="https://www.federalregister.gov/executive-order/14365")
        self.assertEqual(upstream.federal_register_target(eo), ("executive_order", "14365"))
        self.assertIsNone(upstream.federal_register_target(rec()))

    def test_revoked_order_still_marked_active_is_reported(self):
        fetch = fake_fetch([("documents/2023-24283.json", {
            "document_number": "2023-24283", "executive_order_number": 14110, "signing_date": "2023-10-30",
            "type": "Presidential Document", "html_url": "https://fr.example/doc",
            "executive_order_notes": "Revoked by: EO 14148, January 20, 2025"})])
        out = upstream.check_federal_register(self.record, fetch, 20)
        self.assertEqual(len(out["findings"]), 1)
        self.assertIn("Revoked by EO 14148", out["findings"][0])

    def test_disposition_notes_field_name_also_works(self):
        fetch = fake_fetch([("documents/2023-24283.json", {
            "document_number": "2023-24283", "executive_order_number": 14110, "signing_date": "2023-10-30",
            "disposition_notes": "Revoked by: EO 14148, January 20, 2025"})])
        self.assertTrue(upstream.check_federal_register(self.record, fetch, 20)["findings"])

    def test_revoked_order_marked_rescinded_is_fine(self):
        fetch = fake_fetch([("documents/2023-24283.json", {
            "document_number": "2023-24283", "executive_order_number": 14110, "signing_date": "2023-10-30",
            "executive_order_notes": "Revoked by: EO 14148, January 20, 2025"})])
        out = upstream.check_federal_register(dict(self.record, status="rescinded"), fetch, 20)
        self.assertEqual(out["findings"], [])

    def test_signing_date_mismatch_is_reported(self):
        fetch = fake_fetch([("documents/2023-24283.json", {
            "document_number": "2023-24283", "executive_order_number": 14110, "signing_date": "2023-10-31"})])
        out = upstream.check_federal_register(self.record, fetch, 20)
        self.assertIn("Signed 2023-10-31", out["findings"][0])

    def test_executive_order_number_is_looked_up(self):
        record = rec(id="fed-010", status="active", date_issued="2025-12-11",
                     source_url="https://www.federalregister.gov/executive-order/14365")
        fetch = fake_fetch([
            ("documents.json?", {"results": [
                {"executive_order_number": 14179, "document_number": "2025-02172"},
                {"executive_order_number": 14365, "document_number": "2025-23092"}]}),
            ("documents/2025-23092.json", {"document_number": "2025-23092", "executive_order_number": 14365,
                                           "signing_date": "2025-12-11"}),
        ])
        out = upstream.check_federal_register(record, fetch, 20)
        self.assertIsNone(out["error"])
        self.assertEqual(out["findings"], [])

    def test_unmatched_executive_order_is_an_error_not_a_guess(self):
        record = rec(id="fed-010", status="active", source_url="https://www.federalregister.gov/executive-order/14365")
        fetch = fake_fetch([("documents.json?", {"results": [{"executive_order_number": 14179, "document_number": "x"}]})])
        out = upstream.check_federal_register(record, fetch, 20)
        self.assertIn("no Federal Register document found", out["error"])

    def test_notes_in_both_fields_are_counted_once(self):
        notes = "Amended by: EO 15000, March 1, 2026"
        fetch = fake_fetch([("documents/2023-24283.json", {
            "document_number": "2023-24283", "executive_order_number": 14110, "signing_date": "2023-10-30",
            "executive_order_notes": notes, "disposition_notes": notes})])
        out = upstream.check_federal_register(self.record, fetch, 20)
        self.assertEqual(len(out["findings"]), 1)

    def test_see_also_lists_stay_out_of_the_summary(self):
        fetch = fake_fetch([("documents/2023-24283.json", {
            "document_number": "2023-24283", "executive_order_number": 14110, "signing_date": "2023-10-30",
            "executive_order_notes": "See: EO 12250, November 2, 1980; EO 12333\r\nRevoked by: EO 14148, January 20, 2025"})])
        out = upstream.check_federal_register(dict(self.record, status="rescinded"), fetch, 20)
        self.assertIn("Revoked by EO 14148", out["summary"])
        self.assertNotIn("12250", out["summary"])

    def test_errors_are_reported_not_raised(self):
        fetch = fake_fetch([("documents/2023-24283.json", upstream.FetchError("HTTP 500", 500))])
        self.assertEqual(upstream.check_federal_register(self.record, fetch, 20)["error"], "HTTP 500")


class CongressTests(unittest.TestCase):
    record = rec(id="fed-012", status="enacted", last_verified="2026-09-17",
                 source_url="https://www.congress.gov/bill/119th-congress/senate-bill/146")

    def payload(self, action_date="2025-05-19", laws=True):
        bill = {"latestAction": {"actionDate": action_date, "text": "Became Public Law No: 119-12."}}
        if laws:
            bill["laws"] = [{"number": "119-12", "type": "Public Law"}]
        return {"bill": bill}

    def test_target_parsing(self):
        self.assertEqual(upstream.congress_target(self.record), ("119", "s", "146"))

    def test_enacted_bill_with_old_action_is_fine(self):
        fetch = fake_fetch([("/bill/119/s/146", self.payload())])
        out = upstream.check_congress(self.record, fetch, 20, "DEMO_KEY")
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["upstream_url"], "https://www.congress.gov/bill/119th-congress/senate-bill/146")
        # The key travels in a header, never in the URL where logs would show it.
        url, headers = fetch.calls[0]
        self.assertNotIn("DEMO_KEY", url)
        self.assertEqual(headers.get("X-Api-Key"), "DEMO_KEY")

    def test_new_action_is_reported(self):
        fetch = fake_fetch([("/bill/119/s/146", self.payload(action_date="2026-10-01"))])
        out = upstream.check_congress(self.record, fetch, 20, "key")
        self.assertIn("newer than the last check", out["findings"][0])

    def test_pending_bill_that_became_law_is_reported(self):
        fetch = fake_fetch([("/bill/119/s/146", self.payload())])
        out = upstream.check_congress(dict(self.record, status="pending"), fetch, 20, "key")
        self.assertIn("Became Public Law 119-12", out["findings"][0])

    def test_rate_limit_is_reported_without_asking_for_a_key(self):
        fetch = fake_fetch([("/bill/", upstream.FetchError("HTTP 429", 429))])
        out = upstream.check_congress(self.record, fetch, 20)
        self.assertIn("tried again next week", out["error"])
        self.assertNotIn("API_KEY", out["error"])


class OrchestrationTests(unittest.TestCase):
    def test_state_bills_are_skipped_and_never_contacted(self):
        records = [real_records()["state-013"], real_records()["intl-002"]]
        fetch = fake_fetch([])
        results = upstream.check_all(records, fetch=fetch, pause=0)
        self.assertIn("no free official API", results[0]["skipped"])
        self.assertEqual(results[1]["skipped"], "no official API covers this source")
        self.assertEqual(fetch.calls, [])

    def test_congress_uses_the_public_demo_key(self):
        fetch = fake_fetch([("/bill/119/s/146", {"bill": {"latestAction": {"actionDate": "2025-05-19", "text": "x"},
                                                          "laws": [{"number": "119-12"}]}})])
        upstream.check_all([real_records()["fed-012"]], fetch=fetch, pause=0)
        self.assertEqual(fetch.calls[0][1]["X-Api-Key"], "DEMO_KEY")

    def test_nothing_reads_an_api_key_from_the_environment(self):
        source = (ROOT / "scripts" / "upstream_check.py").read_text(encoding="utf-8")
        self.assertNotIn("environ", source)
        self.assertNotIn("OPENSTATES", source)

    def test_every_record_gets_exactly_one_result(self):
        records = list(real_records().values())
        results = upstream.check_all(records, fetch=fake_fetch([]), pause=0)
        self.assertEqual(sorted(r["id"] for r in results), sorted(r["id"] for r in records))

    def test_report_lists_findings_first_and_counts_them(self):
        results = [
            upstream.result(rec(id="fed-001"), "Federal Register", findings=["Revoked"], summary="s"),
            upstream.result(rec(id="fed-002"), "Federal Register", summary="fine"),
            upstream.result(rec(id="fed-003"), "Congress.gov", error="HTTP 500"),
            upstream.result(rec(id="intl-001"), None, skipped="no official API covers this source"),
        ]
        text, count = upstream.render_markdown(results)
        self.assertEqual(count, 1)
        self.assertLess(text.index("fed-001"), text.index("fed-002"))
        self.assertIn("Could not check (1)", text)
        self.assertIn("Not checked automatically (1)", text)


if __name__ == "__main__":
    unittest.main()
