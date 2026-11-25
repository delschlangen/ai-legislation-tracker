"""
Tests for scripts/publish_report.py, which posts the weekly report as a GitHub
issue. Standard library only, and nothing here runs gh or touches the network:
a fake stands in for the gh command and records what it was asked to do.

    python3 -m unittest discover -s tests
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import publish_report as publish  # noqa: E402

REPO = "someone/tracker"
BOT = {"login": "github-actions[bot]", "type": "Bot"}
PERSON = {"login": "a-stranger", "type": "User"}


def issue(number, title="Maintenance report", author=BOT, pull_request=False):
    return dict(number=number, title=title, pull_request=pull_request, **author)


class FakeGh:
    """Answers the listing and the view from fixtures; records every call."""

    def __init__(self, issues, body=""):
        self.issues, self.body, self.calls = issues, body, []

    def __call__(self, args):
        self.calls.append(list(args))
        if args[0] == "api":
            return "".join(json.dumps(item) + "\n" for item in self.issues)
        if args[:2] == ["issue", "view"]:
            return self.body + "\n"
        return ""

    def did(self, *command):
        return [call for call in self.calls if call[:len(command)] == list(command)]


class FindIssueTests(unittest.TestCase):
    def test_no_issue(self):
        self.assertIsNone(publish.find_report_issue([]))
        self.assertIsNone(publish.find_report_issue([issue(3, title="Something else")]))

    def test_our_issue(self):
        self.assertEqual(publish.find_report_issue([issue(3, title="Other"), issue(7)]), 7)

    def test_a_strangers_issue_with_the_same_title_is_ignored(self):
        # GitHub lists newest first, so the stranger's newer issue comes first.
        self.assertEqual(publish.find_report_issue([issue(9, author=PERSON), issue(5)]), 5)
        self.assertIsNone(publish.find_report_issue([issue(9, author=PERSON)]))

    def test_the_author_must_be_the_actions_bot_exactly(self):
        for author in ({"login": "github-actions", "type": "User"},
                       {"login": "github-actions[bot]", "type": "User"},
                       {"login": "dependabot[bot]", "type": "Bot"},
                       {"login": "github-actions[bot]x", "type": "Bot"},
                       {"login": None, "type": None}):
            self.assertIsNone(publish.find_report_issue([issue(9, author=author)]), author)

    def test_a_pull_request_is_not_an_issue(self):
        self.assertIsNone(publish.find_report_issue([issue(4, pull_request=True)]))

    def test_similar_titles_do_not_match(self):
        for title in ("Maintenance report (old)", "maintenance report", " Maintenance report", "Re: Maintenance report"):
            self.assertIsNone(publish.find_report_issue([issue(4, title=title)]), title)

    def test_newest_of_ours_wins_and_junk_is_skipped(self):
        self.assertEqual(publish.find_report_issue([None, "text", {}, issue(8), issue(2)]), 8)


class CountTests(unittest.TestCase):
    def test_previous_count_reads_the_headline(self):
        body = "Automated maintenance report for 2026-11-18. **13 item(s) need a look.**\n\n**99 items** later"
        self.assertEqual(publish.previous_count(body), 13)

    def test_previous_count_is_zero_when_the_text_has_none(self):
        for body in ("edited by hand", "", None):
            self.assertEqual(publish.previous_count(body), 0)

    def test_read_count_keeps_digits_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "attention.txt")
            for content, expected in (("16\n", 16), ("", 0), ("  7 ", 7), ("$(rm -rf /) 3", 3), ("none", 0)):
                Path(path).write_text(content, encoding="utf-8")
                self.assertEqual(publish.read_count(path), expected, content)


class PublishTests(unittest.TestCase):
    def test_first_run_creates_the_issue(self):
        gh = FakeGh([])
        outcome = publish.publish("report.md", 16, REPO, gh)
        self.assertEqual(outcome, "created a new issue")
        self.assertEqual(gh.did("issue", "create"),
                         [["issue", "create", "--repo", REPO, "--title", "Maintenance report", "--body-file", "report.md"]])
        self.assertEqual(gh.did("issue", "edit") + gh.did("issue", "comment"), [])

    def test_more_to_do_updates_and_comments(self):
        gh = FakeGh([issue(7)], body="Report. **13 item(s) need a look.**")
        publish.publish("report.md", 16, REPO, gh)
        self.assertEqual(gh.did("issue", "edit"), [["issue", "edit", "7", "--repo", REPO, "--body-file", "report.md"]])
        comment = gh.did("issue", "comment")
        self.assertEqual(len(comment), 1)
        self.assertIn("now lists 16 item(s) to look at, up from 13", comment[0][-1])
        self.assertEqual(gh.did("issue", "create"), [])

    def test_same_or_less_to_do_updates_quietly(self):
        for count in (13, 4, 0):
            gh = FakeGh([issue(7)], body="Report. **13 item(s) need a look.**")
            publish.publish("report.md", count, REPO, gh)
            self.assertEqual(len(gh.did("issue", "edit")), 1, count)
            self.assertEqual(gh.did("issue", "comment"), [], count)

    def test_a_strangers_issue_is_never_edited(self):
        gh = FakeGh([issue(9, author=PERSON), issue(5)], body="**13 item(s)")
        publish.publish("report.md", 14, REPO, gh)
        self.assertEqual(gh.did("issue", "view")[0][2], "5")
        self.assertEqual(gh.did("issue", "edit")[0][2], "5")
        self.assertFalse(any("9" in call[2:3] for call in gh.calls if call[0] == "issue"))

    def test_only_a_strangers_issue_means_we_open_our_own(self):
        gh = FakeGh([issue(9, author=PERSON)])
        self.assertEqual(publish.publish("report.md", 3, REPO, gh), "created a new issue")
        self.assertEqual(gh.did("issue", "edit"), [])

    def test_the_listing_asks_for_every_open_issue_in_the_right_repository(self):
        gh = FakeGh([])
        publish.publish("report.md", 1, REPO, gh)
        listing = gh.did("api")[0]
        self.assertIn("--paginate", listing)
        self.assertIn(f"repos/{REPO}/issues?state=open&per_page=100", listing)

    def test_the_report_text_is_only_ever_passed_as_a_file(self):
        gh = FakeGh([issue(7)], body="**1 item(s)")
        publish.publish("report.md", 5, REPO, gh)
        for call in gh.calls:
            self.assertTrue(all(isinstance(part, str) for part in call))
        self.assertIn("--body-file", gh.did("issue", "edit")[0])
        source = (ROOT / "scripts" / "publish_report.py").read_text(encoding="utf-8")
        self.assertNotIn("shell=True", source)
        self.assertNotIn("os.system", source)


class CommandLineTests(unittest.TestCase):
    def test_needs_a_repository_name(self):
        saved = os.environ.pop("GH_REPO", None)
        try:
            self.assertEqual(publish.main(["report.md", "attention.txt"]), 2)
            os.environ["GH_REPO"] = "not a repo; rm -rf /"
            self.assertEqual(publish.main(["report.md", "attention.txt"]), 2)
        finally:
            os.environ.pop("GH_REPO", None)
            if saved is not None:
                os.environ["GH_REPO"] = saved

    def test_wrong_arguments_print_usage(self):
        self.assertEqual(publish.main([]), 2)

    def test_a_failing_gh_is_an_error_exit_not_a_traceback(self):
        import subprocess

        def failing(args):
            raise subprocess.CalledProcessError(1, ["gh"] + list(args))
        saved_run, saved_repo = publish.run_gh, os.environ.get("GH_REPO")
        os.environ["GH_REPO"] = REPO
        try:
            with tempfile.TemporaryDirectory() as tmp:
                report, count = os.path.join(tmp, "report.md"), os.path.join(tmp, "attention.txt")
                Path(report).write_text("x", encoding="utf-8")
                Path(count).write_text("1", encoding="utf-8")
                saved_default = publish.publish.__defaults__
                publish.publish.__defaults__ = (failing,)
                try:
                    self.assertEqual(publish.main([report, count]), 1)
                    self.assertEqual(publish.main([report, os.path.join(tmp, "missing.txt")]), 1)
                finally:
                    publish.publish.__defaults__ = saved_default
        finally:
            publish.run_gh = saved_run
            os.environ.pop("GH_REPO", None)
            if saved_repo is not None:
                os.environ["GH_REPO"] = saved_repo


class WorkflowTests(unittest.TestCase):
    """The workflow file itself, read as text: the project has no YAML parser."""

    text = (ROOT / ".github" / "workflows" / "maintenance.yml").read_text(encoding="utf-8")

    def test_only_the_publish_job_can_write_and_only_issues(self):
        self.assertEqual(self.text.count("issues: write"), 1)
        for forbidden in ("contents: write", "pull-requests: write", "permissions: write-all", "actions: write"):
            self.assertNotIn(forbidden, self.text)
        self.assertLess(self.text.index("  publish:"), self.text.index("issues: write"))

    def test_publish_never_runs_on_pull_requests(self):
        publish_job = self.text[self.text.index("  publish:"):]
        self.assertIn("if: github.event_name != 'pull_request'", publish_job)

    def test_nothing_is_interpolated_into_a_shell_command(self):
        lines = self.text.splitlines()
        for index, line in enumerate(lines):
            if line.strip().startswith("run:"):
                block = [line]
                indent = len(line) - len(line.lstrip())
                for later in lines[index + 1:]:
                    if later.strip() and len(later) - len(later.lstrip()) <= indent:
                        break
                    block.append(later)
                self.assertNotIn("${{", "\n".join(block), f"line {index + 1}")

    def test_no_secrets_are_used(self):
        self.assertNotIn("secrets.", self.text)

    def test_pull_requests_do_not_share_the_publishing_queue(self):
        self.assertIn("github.event_name == 'pull_request' && github.ref || 'publish'", self.text)


if __name__ == "__main__":
    unittest.main()
