"""
Tests for the maintenance scripts in scripts/. Standard library only, and no
network: every web request is answered by a fake.

    python3 -m unittest discover -s tests
"""

import http.client
import io
import json
import socket
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import link_check  # noqa: E402
import maintenance_report as report  # noqa: E402
import timebox  # noqa: E402
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

    def test_a_passed_date_clears_once_the_entry_is_verified_after_it(self):
        def listed(last_verified):
            records = [rec(effective_date="2026-10-10", last_verified=last_verified)]
            return bool(report.recently_passed(records, TODAY, 60))
        self.assertTrue(listed("2026-10-09"))            # checked before the date arrived
        self.assertFalse(listed("2026-10-10"))           # checked on the day
        self.assertFalse(listed("2026-11-01"))           # checked since
        self.assertTrue(listed("needs_verification"))    # never checked
        self.assertTrue(listed(None))


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

    def test_rows_are_parsed_with_their_jurisdiction(self):
        rows = report.readme_upcoming_rows(self.readme)
        self.assertEqual([(d.isoformat(), cells[0]) for d, cells in rows],
                         [("2026-10-01", "Connecticut"), ("2027-01-01", "Colorado")])

    def test_jurisdiction_names_match_the_site(self):
        self.assertEqual(report.jurisdiction_of({"id": "fed-001", "issuing_body": "OMB"}), "US Federal")
        self.assertEqual(report.jurisdiction_of({"id": "state-001", "state": "Colorado"}), "Colorado")
        self.assertEqual(report.jurisdiction_of({"id": "intl-001", "jurisdiction": "European Union"}), "European Union")

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

    def test_a_network_section_that_fails_does_not_cost_the_rest(self):
        saved = upstream.check_all, link_check.check_all

        def explode(*args, **kwargs):
            raise RuntimeError("resolver on fire")
        upstream.check_all = link_check.check_all = explode
        try:
            text, attention = report.build_report([rec(last_verified="2020-01-01")], TODAY, 183, "",
                                                  links=True, upstream=True)
        finally:
            upstream.check_all, link_check.check_all = saved
        self.assertEqual(text.count("could not run this week (RuntimeError: resolver on fire)"), 2)
        self.assertIn("## Stale entries (1)", text)
        self.assertEqual(attention, 1)

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

    def test_not_found_is_broken_once_a_full_request_agrees(self):
        calls = []

        def counted(code):
            def handler(request):
                calls.append(request.get_method())
                return http_error(code)(request)
            return handler
        result = self.check({"HEAD": counted(404), "GET": counted(404)})
        self.assertEqual((result["outcome"], result["status"]), ("broken", 404))
        self.assertEqual(calls, ["HEAD", "GET"])   # a definite answer is not retried

    def test_a_server_that_wrongly_answers_head_with_404_is_not_broken(self):
        result = self.check({"HEAD": http_error(404), "GET": lambda r: FakeResponse(self.url)})
        self.assertEqual(result["outcome"], "ok")

    def test_gone_is_broken(self):
        self.assertEqual(self.check({"HEAD": http_error(410), "GET": http_error(410)})["outcome"], "broken")

    def test_forbidden_is_blocked_not_broken(self):
        result = self.check({"HEAD": http_error(403), "GET": http_error(403)})
        self.assertEqual(result["outcome"], "blocked")

    def test_missing_host_is_broken_after_two_tries(self):
        calls = []

        def dns(request):
            calls.append(1)
            raise urllib.error.URLError(socket.gaierror(socket.EAI_NONAME, "Name or service not known"))
        result = self.check({"HEAD": dns})
        self.assertEqual((result["outcome"], result["detail"]), ("broken", "host not found"))
        self.assertEqual(len(calls), 2)

    def test_one_host_not_found_among_other_failures_is_not_broken(self):
        """Both tries must say the host does not exist. A timeout, a temporary
        DNS fault or a server error on the other try leaves it unreachable."""
        not_found = urllib.error.URLError(socket.gaierror(socket.EAI_NONAME, "Name or service not known"))
        others = (socket.timeout("timed out"),
                  urllib.error.URLError(socket.gaierror(socket.EAI_AGAIN, "Temporary failure in name resolution")),
                  ConnectionRefusedError("refused"), "HTTP 500")
        for other in others:
            for order in ((other, not_found), (not_found, other)):
                calls = []

                def flaky(request, order=order):
                    calls.append(1)
                    step = order[len(calls) - 1]
                    if step == "HTTP 500":
                        return http_error(500)(request)
                    raise step
                result = self.check({"HEAD": flaky})
                label = f"{order[0]!r} then {order[1]!r}"
                self.assertEqual(result["outcome"], "unreachable", label)
                self.assertIsNone(result["status"], label)
                self.assertIn("host not found on 1 of 2 tries", result["detail"], label)
                result["ids"] = ["fed-001"]
                self.assertEqual(link_check.render_markdown([result])[1], 0, label)

    def test_host_that_resolves_on_the_second_try_is_ok(self):
        calls = []

        def flaky(request):
            calls.append(1)
            if len(calls) == 1:
                raise urllib.error.URLError(socket.gaierror(socket.EAI_NONAME, "Name or service not known"))
            return FakeResponse(self.url)
        self.assertEqual(self.check({"HEAD": flaky})["outcome"], "ok")

    def test_temporary_dns_failure_is_not_a_broken_link(self):
        calls = []

        def dns(request):
            calls.append(1)
            raise urllib.error.URLError(socket.gaierror(socket.EAI_AGAIN, "Temporary failure in name resolution"))
        result = self.check({"HEAD": dns})
        self.assertEqual(result["outcome"], "unreachable")
        self.assertIn("DNS lookup failed", result["detail"])
        self.assertEqual(len(calls), 2)
        result["ids"] = ["fed-001"]
        text, broken = link_check.render_markdown([result])
        self.assertEqual(broken, 0)
        self.assertIn("Could not check automatically (1)", text)

    def test_garbled_responses_are_an_outcome_not_a_crash(self):
        # None of these is an OSError or a ValueError, which is what used to be caught.
        for error in (http.client.BadStatusLine("not http"), http.client.IncompleteRead(b"x"),
                      http.client.HTTPException("got more than 100 headers"),
                      http.client.LineTooLong("header line"), RuntimeError("anything else"), KeyError("x")):
            def broken_server(request, error=error):
                raise error
            result = self.check({"HEAD": broken_server})
            self.assertEqual(result["outcome"], "unreachable", repr(error))
            self.assertIn(type(error).__name__, result["detail"])

    def test_one_bad_link_does_not_stop_the_others(self):
        def head(request):
            if "bad" in request.full_url:
                raise http.client.BadStatusLine("not http")
            return FakeResponse(request.full_url)
        records = [rec(id="state-001", source_url="https://ok.example/a"),
                   rec(id="state-002", source_url="https://bad.example/b"),
                   rec(id="state-003", source_url="https://ok.example/c")]
        results = link_check.check_all(records, opener=opener_for({"HEAD": head}), pause=0)
        self.assertEqual(sorted((r["ids"][0], r["outcome"]) for r in results),
                         [("state-001", "ok"), ("state-002", "unreachable"), ("state-003", "ok")])

    def test_status_from_a_failed_try_does_not_leak_into_the_next(self):
        calls = []

        def first_500_then_timeout(request):
            calls.append(1)
            if len(calls) == 1:
                return http_error(500)(request)
            raise socket.timeout("timed out")
        result = self.check({"HEAD": first_500_then_timeout})
        self.assertEqual((result["outcome"], result["status"], result["detail"]), ("unreachable", None, "timed out"))

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


class Gate:
    """Something a fake server can be held at. Released when the test ends, so
    no thread is left waiting."""

    def __init__(self, test):
        self.event = threading.Event()
        test.addCleanup(self.event.set)

    def hold(self, limit=10):
        self.event.wait(limit)


class LinkDeadlineTests(unittest.TestCase):
    """The network timeout limits one wait on a socket. A server that keeps
    sending a byte at a time never trips it, so each link also has a limit on
    the whole of its check, and the run has a limit on all of them."""

    def test_a_link_that_never_finishes_is_given_up_on_and_the_rest_are_checked(self):
        gate = Gate(self)

        def head(request):
            if "slow" in request.full_url:
                gate.hold()
            return FakeResponse(request.full_url)
        records = [rec(id="state-001", source_url="https://ok.example/a"),
                   rec(id="state-002", source_url="https://slow.example/b"),
                   rec(id="state-003", source_url="https://ok.example/c")]
        began = time.monotonic()
        results = link_check.check_all(records, opener=opener_for({"HEAD": head}), pause=0, deadline=0.3)
        self.assertLess(time.monotonic() - began, 5)
        by_id = {r["ids"][0]: r for r in results}
        self.assertEqual(by_id["state-002"]["outcome"], "unreachable")
        self.assertEqual(by_id["state-002"]["detail"], "no complete answer within 0.3 seconds")
        self.assertEqual((by_id["state-001"]["outcome"], by_id["state-003"]["outcome"]), ("ok", "ok"))
        text, broken = link_check.render_markdown(results)
        self.assertEqual(broken, 0)
        self.assertIn("Could not check automatically (1)", text)

    def test_once_the_run_budget_is_spent_no_further_link_is_started(self):
        gate = Gate(self)
        started = []

        def head(request):
            started.append(request.full_url)
            gate.hold()
        records = [rec(id=f"state-00{n}", source_url=f"https://slow.example/{n}") for n in range(1, 6)]
        began = time.monotonic()
        results = link_check.check_all(records, opener=opener_for({"HEAD": head}), pause=0, workers=1,
                                       deadline=0.2, budget=0.3)
        self.assertLess(time.monotonic() - began, 5)
        details = [r["detail"] for r in results]
        self.assertEqual(len(results), 5)
        self.assertIn("no complete answer within 0.2 seconds", details)
        self.assertIn("not checked: this run had used up its time on other links", details)
        self.assertLess(len(started), 5)
        self.assertTrue(all(r["outcome"] == "unreachable" for r in results))

    def test_the_default_limit_leaves_room_for_two_tries_that_time_out(self):
        for timeout, pause in ((20, 2.0), (3, 0), (60, 2.0)):
            self.assertGreaterEqual(link_check.link_deadline(timeout, pause), 2 * timeout + pause)


class TimeboxTests(unittest.TestCase):
    def test_answers_and_failures_come_back_for_every_item(self):
        def work(n):
            if n == 3:
                raise ValueError("three")
            return n * 10
        out = timebox.run_all(work, [1, 2, 3, 4], seconds=5, workers=2)
        self.assertEqual({k: v[0] for k, v in out.items()},
                         {1: timebox.DONE, 2: timebox.DONE, 3: timebox.FAILED, 4: timebox.DONE})
        self.assertEqual(out[4][1], 40)
        self.assertIsInstance(out[3][1], ValueError)
        self.assertEqual(timebox.run_all(work, [], seconds=5), {})

    def test_a_late_answer_does_not_change_the_outcome(self):
        gate, finished = Gate(self), threading.Event()

        def slow(n):
            gate.hold()
            finished.set()
            return "late"
        out = timebox.run_all(slow, ["x"], seconds=0.2)
        self.assertEqual(out, {"x": (timebox.GAVE_UP, None)})
        gate.event.set()
        self.assertTrue(finished.wait(5))
        self.assertEqual(out, {"x": (timebox.GAVE_UP, None)})

    def test_a_late_answer_while_other_calls_run_is_ignored(self):
        """The first call is given up on at 1 s and answers at 1.5 s, while the
        second is still running. That answer must change nothing."""
        first_answered = threading.Event()

        def work(name):
            if name == "first":
                time.sleep(1.5)
                first_answered.set()
                return "late"
            first_answered.wait(5)
            time.sleep(0.1)
            return "on time"
        out = timebox.run_all(work, ["first", "second"], seconds=1.0, workers=1)
        self.assertEqual(out, {"first": (timebox.GAVE_UP, None), "second": (timebox.DONE, "on time")})

    def test_an_answer_that_came_in_time_is_never_given_up_on(self):
        """The loop used to read one answer, then give up on every call past its
        deadline, throwing away answers already waiting. With a pause while
        calls run, that hit the second call every time."""
        out = timebox.run_all(lambda n: n * 10, range(4), seconds=1.0, workers=4, pause=0.6)
        self.assertEqual(out, {n: (timebox.DONE, n * 10) for n in range(4)})

    def test_an_abandoned_call_does_not_keep_the_process_alive(self):
        """Its thread must be a daemon, or a server that never finishes keeps the
        report job running until GitHub stops it, and nothing is published."""
        code = ("import sys, threading; sys.path.insert(0, 'scripts'); import timebox; "
                "print(timebox.run_all(lambda n: threading.Event().wait(), [1], seconds=0.1))")
        done = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), timeout=30,
                              stdout=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(done.returncode, 0)
        self.assertIn("gave up", done.stdout)

    def test_calls_run_side_by_side_up_to_the_number_of_workers(self):
        began = time.monotonic()
        out = timebox.run_all(lambda n: time.sleep(0.5), range(4), seconds=5, workers=4)
        self.assertLess(time.monotonic() - began, 1.5)   # one after another would take 2 seconds
        self.assertEqual({v[0] for v in out.values()}, {timebox.DONE})

    def test_the_pause_comes_between_calls(self):
        began = time.monotonic()
        timebox.run_all(lambda n: n, range(3), seconds=5, pause=0.1)
        self.assertGreaterEqual(time.monotonic() - began, 0.2)

    def test_the_budget_stops_new_calls_but_reports_every_item(self):
        gate = Gate(self)
        out = timebox.run_all(lambda n: gate.hold(), range(6), seconds=0.15, workers=2, budget=0.2)
        states = [out[n][0] for n in range(6)]
        self.assertIn(timebox.GAVE_UP, states)
        self.assertIn(timebox.OUT_OF_TIME, states)
        self.assertEqual(set(states), {timebox.GAVE_UP, timebox.OUT_OF_TIME})


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


class FederalRegisterRuleTests(unittest.TestCase):
    """A rule has no signing date and no disposition notes, so it is compared by
    publication date instead. Before this, nothing was compared at all and the
    report still said "matched"."""

    record = rec(id="fed-008", title="Rule", status="active", date_issued="2023-10-17",
                 source_url="https://www.federalregister.gov/documents/2023/10/25/2023-23055/export-controls")

    def rule(self, **fields):
        doc = {"type": "Rule", "document_number": "2023-23055", "publication_date": "2023-10-25",
               "signing_date": None, "html_url": "https://fr.example/rule"}
        doc.update(fields)
        return fake_fetch([("documents/2023-23055.json", doc)])

    def test_published_soon_after_it_was_issued_is_a_match(self):
        out = upstream.check_federal_register(self.record, self.rule(), 20)
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["summary"], "Rule 2023-23055, published 2023-10-25")

    def test_a_date_far_from_publication_is_reported(self):
        out = upstream.check_federal_register(dict(self.record, date_issued="2024-10-01"), self.rule(), 20)
        self.assertEqual(len(out["findings"]), 1)
        self.assertIn("Published 2023-10-25", out["findings"][0])
        self.assertIn("342 days apart", out["findings"][0])

    def test_the_tolerance_is_thirty_days(self):
        at_limit = upstream.check_federal_register(dict(self.record, date_issued="2023-09-25"), self.rule(), 20)
        over = upstream.check_federal_register(dict(self.record, date_issued="2023-09-24"), self.rule(), 20)
        self.assertEqual(at_limit["findings"], [])
        self.assertEqual(len(over["findings"]), 1)

    def test_effective_dates_are_compared_when_both_sides_have_one(self):
        fetch = self.rule(effective_on="2023-11-17")
        same = upstream.check_federal_register(dict(self.record, effective_date="2023-11-17"), fetch, 20)
        different = upstream.check_federal_register(dict(self.record, effective_date="2024-01-01"), fetch, 20)
        absent = upstream.check_federal_register(self.record, fetch, 20)
        self.assertEqual(same["findings"], [])
        self.assertIn("Effective 2023-11-17", different["findings"][0])
        self.assertEqual(absent["findings"], [])
        self.assertTrue(same["summary"].endswith("effective 2023-11-17"))

    def test_the_tracked_export_control_record_is_flagged(self):
        """fed-008 cites the October 2023 rule but gives date_issued 2024-10-01.
        The report should say so until a person resolves it."""
        record = real_records()["fed-008"]
        out = upstream.check_federal_register(record, self.rule(), 20)
        if record["date_issued"] == "2024-10-01":
            self.assertEqual(len(out["findings"]), 1)
        else:
            self.assertEqual(out["findings"], [])


class FetchTests(unittest.TestCase):
    """fetch_json turns every kind of failure into a FetchError."""

    class Body:
        def __init__(self, payload=b"{}", error=None):
            self.payload, self.error = payload, error

        def read(self):
            if self.error:
                raise self.error
            return self.payload

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fetch(self, body=None, raises=None, seen=None):
        def opener(request, timeout):
            if seen is not None:
                seen.append(request)
            if raises:
                raise raises
            return body
        return upstream.fetch_json("https://api.example/x", headers={"X-Api-Key": "DEMO_KEY"}, opener=opener)

    def test_good_json_is_returned_and_headers_are_sent(self):
        seen = []
        self.assertEqual(self.fetch(self.Body(b'{"a": 1}'), seen=seen), {"a": 1})
        self.assertEqual(seen[0].get_header("X-api-key"), "DEMO_KEY")
        self.assertNotIn("DEMO_KEY", seen[0].full_url)

    def test_http_errors_keep_their_status(self):
        error = urllib.error.HTTPError("https://api.example/x", 429, "Too Many", {}, io.BytesIO(b""))
        with self.assertRaises(upstream.FetchError) as caught:
            self.fetch(raises=error)
        self.assertEqual((str(caught.exception), caught.exception.status), ("HTTP 429", 429))

    def test_truncated_and_garbled_responses_become_fetch_errors(self):
        for error in (http.client.IncompleteRead(b"par"), http.client.BadStatusLine("x"),
                      http.client.HTTPException(), socket.timeout("timed out"),
                      urllib.error.URLError("no route")):
            with self.assertRaises(upstream.FetchError, msg=repr(error)) as caught:
                self.fetch(self.Body(error=error))
            self.assertTrue(str(caught.exception))

    def test_a_body_that_is_not_json_is_a_fetch_error(self):
        for payload in (b"<html>rate limited</html>", b"", b"\xff\xfe"):
            with self.assertRaises(upstream.FetchError) as caught:
                self.fetch(self.Body(payload))
            self.assertIn("not valid JSON", str(caught.exception))


class OddResponseTests(unittest.TestCase):
    """Valid JSON in an unexpected shape is reported for that record and never raised."""

    def test_federal_register_shapes(self):
        order = rec(id="fed-010", status="active", date_issued="2025-12-11",
                    source_url="https://www.federalregister.gov/executive-order/14365")
        document = rec(id="fed-001", status="active", date_issued="2023-10-30",
                       source_url="https://www.federalregister.gov/documents/2023/11/01/2023-24283/x")
        for payload in ({"results": [None]}, {"results": None}, {"results": "x"}, [], None, "text", 5):
            out = upstream.check_all([order], fetch=fake_fetch([("documents.json?", payload)]), pause=0)
            self.assertIn("no Federal Register document found", out[0]["error"], repr(payload))
        for payload in ([], None, "text", {}, {"title": "no document number"}):
            out = upstream.check_all([document], fetch=fake_fetch([("documents/2023-24283.json", payload)]), pause=0)
            self.assertEqual(out[0]["error"], "the Federal Register returned no document", repr(payload))
            self.assertEqual(out[0]["findings"], [])

    def test_congress_shapes(self):
        record = real_records()["fed-012"]
        for payload in ([], None, {}, {"bill": None}, {"bill": []}):
            out = upstream.check_all([record], fetch=fake_fetch([("/bill/119/s/146", payload)]), pause=0)
            self.assertEqual(out[0]["error"], "Congress.gov returned no bill", repr(payload))
        # A malformed list of laws must not be read as "this never became law".
        for laws in ([None], "119-12", [["119-12"]]):
            payload = {"bill": {"latestAction": {"actionDate": "2025-05-19", "text": "x"}, "laws": laws}}
            out = upstream.check_all([record], fetch=fake_fetch([("/bill/119/s/146", payload)]), pause=0)
            self.assertIn("could not be read", out[0]["error"], repr(laws))
            self.assertEqual(out[0]["findings"], [])
        # Odd values inside an otherwise good answer are tolerated.
        payload = {"bill": {"latestAction": None, "laws": [{"number": "119-12"}, {"type": "Public Law"}]}}
        out = upstream.check_all([record], fetch=fake_fetch([("/bill/119/s/146", payload)]), pause=0)
        self.assertIsNone(out[0]["error"])
        self.assertEqual(out[0]["findings"], [])

    def test_anything_else_becomes_an_error_for_that_record_only(self):
        def fetch(url, headers=None, timeout=20):
            if "2023-24283" in url:
                raise KeyError("surprise")
            return {"document_number": "2025-02172", "executive_order_number": 14179, "signing_date": "2025-01-23"}
        records = [rec(id="fed-001", status="rescinded", date_issued="2023-10-30",
                       source_url="https://www.federalregister.gov/documents/2023/11/01/2023-24283/x"),
                   rec(id="fed-009", status="active", date_issued="2025-01-23",
                       source_url="https://www.federalregister.gov/documents/2025/01/31/2025-02172/y")]
        out = upstream.check_all(records, fetch=fetch, pause=0)
        self.assertIn("unexpected response: KeyError", out[0]["error"])
        self.assertIsNone(out[1]["error"])
        text, count = upstream.render_markdown(out)
        self.assertIn("Could not check (1)", text)
        self.assertIn("Matched with no change (1)", text)


class NothingToCompareTests(unittest.TestCase):
    """A record is "matched with no change" only if something was set against
    it. An answer with no date to compare, and no notes, is an error."""

    order = rec(id="fed-010", status="active", date_issued="2025-12-11",
                source_url="https://www.federalregister.gov/documents/2025/12/16/2025-23092/x")
    rule = rec(id="fed-008", status="active", date_issued="2024-10-01",
               source_url="https://www.federalregister.gov/documents/2023/10/25/2023-23055/x")

    def check(self, record, doc):
        number = doc.get("document_number", "none")
        out = upstream.check_all([record], fetch=fake_fetch([(f"documents/{number}.json", doc)]), pause=0)
        return out[0]

    def test_a_rule_with_no_dates_is_not_a_match(self):
        for doc in ({"document_number": "2023-23055", "type": "Rule"},
                    {"document_number": "2023-23055", "type": "Rule", "publication_date": None},
                    {"document_number": "2023-23055", "type": "Rule", "publication_date": "soon"},
                    {"document_number": "2023-23055", "type": "Rule", "effective_on": "2023-11-17"}):
            out = self.check(self.rule, doc)
            self.assertIn("nothing to compare", out["error"] or "", doc)
            self.assertEqual(out["findings"], [], doc)
            text, count = upstream.render_markdown([out])
            self.assertIn("Could not check (1)", text)
            self.assertIn("Matched with no change (0)", text)
            self.assertNotIn("None", out["summary"])

    def test_a_rule_compared_by_effective_date_alone_is_a_match(self):
        doc = {"document_number": "2023-23055", "type": "Rule", "effective_on": "2023-11-17"}
        out = self.check(dict(self.rule, effective_date="2023-11-17"), doc)
        self.assertIsNone(out["error"])
        self.assertEqual(out["summary"], "Rule 2023-23055, effective 2023-11-17")

    def test_an_order_with_no_signing_date_and_no_notes_is_not_a_match(self):
        doc = {"document_number": "2025-23092", "executive_order_number": 14365, "type": "Presidential Document",
               "publication_date": "2025-12-16"}
        out = self.check(self.order, doc)
        self.assertIn("no signing date and no notes", out["error"] or "")
        self.assertEqual(out["summary"], "EO 14365, Presidential Document 2025-23092, published 2025-12-16")

    def test_an_order_whose_notes_were_read_is_a_match(self):
        doc = {"document_number": "2025-23092", "executive_order_number": 14365,
               "executive_order_notes": "See: EO 14179"}
        out = self.check(self.order, doc)
        self.assertIsNone(out["error"])
        self.assertEqual(out["findings"], [])

    def test_a_record_without_date_issued_says_so(self):
        doc = {"document_number": "2023-23055", "type": "Rule", "publication_date": "2023-10-25"}
        record = dict(self.rule)
        del record["date_issued"]
        self.assertEqual(self.check(record, doc)["error"], "nothing to compare: the record has no date_issued to compare")


class UpstreamDeadlineTests(unittest.TestCase):
    def test_a_record_whose_check_never_finishes_is_given_up_on(self):
        gate = Gate(self)

        def fetch(url, headers=None, timeout=20):
            if "2023-24283" in url:
                gate.hold()
            return {"document_number": "2025-02172", "executive_order_number": 14179, "signing_date": "2025-01-23"}
        records = [rec(id="fed-001", status="rescinded", date_issued="2023-10-30",
                       source_url="https://www.federalregister.gov/documents/2023/11/01/2023-24283/x"),
                   rec(id="fed-009", status="active", date_issued="2025-01-23",
                       source_url="https://www.federalregister.gov/documents/2025/01/31/2025-02172/y"),
                   rec(id="state-001")]
        began = time.monotonic()
        out = upstream.check_all(records, fetch=fetch, pause=0, deadline=0.3)
        self.assertLess(time.monotonic() - began, 5)
        self.assertEqual([r["id"] for r in out], ["fed-001", "fed-009", "state-001"])
        self.assertEqual(out[0]["error"], "no complete answer within 0.3 seconds")
        self.assertIsNone(out[1]["error"])
        self.assertTrue(out[2]["skipped"])

    def test_once_the_budget_is_spent_the_rest_are_listed_as_not_checked(self):
        gate = Gate(self)

        def fetch(url, headers=None, timeout=20):
            gate.hold()
        records = [rec(id=f"fed-00{n}", status="active", date_issued="2023-10-30",
                       source_url=f"https://www.federalregister.gov/documents/2023/11/01/2023-2428{n}/x")
                   for n in range(1, 5)]
        out = upstream.check_all(records, fetch=fetch, pause=0, deadline=0.2, budget=0.1)
        errors = [r["error"] for r in out]
        self.assertEqual(errors[0], "no complete answer within 0.2 seconds")
        self.assertEqual(set(errors[1:]), {"not checked: this run had used up its time on other records"})

    def test_the_default_limit_covers_an_executive_order_lookup(self):
        # Two searches and the document itself, each allowed the network timeout.
        for timeout in (3, 20, 60):
            self.assertGreaterEqual(upstream.record_deadline(timeout), 3 * timeout)


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
