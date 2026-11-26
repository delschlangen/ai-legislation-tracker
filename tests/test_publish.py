"""
Tests for scripts/publish_report.py, which posts the weekly report as a GitHub
issue. Standard library only, and nothing here runs gh or touches the network:
a fake stands in for the gh command and records what it was asked to do.

    python3 -m unittest discover -s tests
"""

import inspect
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import link_check  # noqa: E402
import publish_report as publish  # noqa: E402
import upstream_check  # noqa: E402

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


def rest_issue(number, title, login, kind, pull_request=False):
    """An issue as GitHub's REST API returns it, trimmed to the fields that matter.
    A pull request carries a pull_request object; a plain issue has no such key."""
    item = {"number": number, "title": title, "state": "open", "body": "x",
            "user": {"login": login, "type": kind, "id": number * 7}}
    if pull_request:
        item["pull_request"] = {"url": f"https://api.github.com/repos/{REPO}/pulls/{number}"}
    return item


# Two pages of open issues, newest first. Ours is on the second page, behind a
# stranger's issue and a pull request that both carry the same title.
REST_PAGES = [
    [rest_issue(12, "Maintenance report", "a-stranger", "User"),
     rest_issue(11, "Maintenance report", "github-actions[bot]", "Bot", pull_request=True),
     rest_issue(10, "Something else", "github-actions[bot]", "Bot")],
    [rest_issue(5, "Maintenance report", "github-actions[bot]", "Bot"),
     rest_issue(2, "Maintenance report", "github-actions[bot]", "Bot")],
]


class ListingTests(unittest.TestCase):
    """What publish_report.py asks of gh, checked against how GitHub and jq
    really behave. The fake gh above answers in the projected shape, so these
    are what would notice a projection that no longer matches the REST API."""

    def test_the_projection_reads_the_rest_fields(self):
        for part in ("number: .number", "title: .title", "login: .user.login", "type: .user.type",
                     "pull_request: (.pull_request != null)"):
            self.assertIn(part, publish.ISSUE_FIELDS)

    @unittest.skipUnless(shutil.which("jq"), "jq is not installed")
    def test_the_projection_finds_our_issue_in_real_rest_output(self):
        def gh(args):
            # gh api --paginate applies --jq to each page and prints the results
            # in order, so do the same with the real jq.
            expression = args[args.index("--jq") + 1]
            out = []
            for page in REST_PAGES:
                done = subprocess.run(["jq", "-c", expression], input=json.dumps(page), check=True,
                                      stdout=subprocess.PIPE, universal_newlines=True)
                out.append(done.stdout)
            return "".join(out)
        issues = publish.list_open_issues(REPO, gh)
        self.assertEqual(len(issues), 5)
        self.assertEqual(issues[1], {"number": 11, "title": "Maintenance report", "login": "github-actions[bot]",
                                     "type": "Bot", "pull_request": True})
        self.assertEqual(issues[3]["pull_request"], False)
        self.assertEqual(publish.find_report_issue(issues), 5)


@unittest.skipIf(os.name == "nt", "uses a shell script as a stand-in for gh")
class RunGhTests(unittest.TestCase):
    """run_gh with a stand-in gh on the PATH: what it returns, and that a failing
    gh stops the run instead of being read as an empty list of issues."""

    def stand_in(self, script):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        path = os.path.join(folder, "gh")
        Path(path).write_text("#!/bin/sh\n" + script + "\n", encoding="utf-8")
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        saved = os.environ.get("PATH", "")
        os.environ["PATH"] = folder + os.pathsep + saved
        self.addCleanup(os.environ.__setitem__, "PATH", saved)

    def test_returns_what_gh_printed(self):
        self.stand_in('printf "%s|" "$@"')
        self.assertEqual(publish.run_gh(["issue", "view", "7", "--json", "body"]), "issue|view|7|--json|body|")

    def test_a_failing_gh_raises(self):
        # For example a 502 on the second page of the listing: gh prints the
        # first page, then fails. Reading that as "no report issue" would open
        # a duplicate, so it must stop the run.
        self.stand_in('echo \'{"number": 5, "title": "Maintenance report", "login": "github-actions[bot]", '
                      '"type": "Bot", "pull_request": false}\'\nexit 1')
        with self.assertRaises(subprocess.CalledProcessError):
            publish.run_gh(["api", "--paginate", "repos/x/y/issues"])
        with self.assertRaises(subprocess.CalledProcessError):
            publish.publish("report.md", 3, REPO, publish.run_gh)


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


def without_comments(text):
    """The workflow with its comments removed: whole-line comments, and from a
    space-hash to the end of a line. Nothing in these files has a # in a value."""
    lines = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            lines.append("")
        else:
            lines.append(re.sub(r"\s#.*$", "", line))
    return "\n".join(lines)


RUN_KEY = re.compile(r"^(\s*)(-\s+)?run:")


def run_blocks(text):
    """(line number, text) of every run: step, written either as `run:` or as
    `- run:`, with the lines of a block scalar that belong to it."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = RUN_KEY.match(line)
        if not match:
            continue
        key_column = match.end() - len("run:")
        block = [line]
        for later in lines[index + 1:]:
            if later.strip() and len(later) - len(later.lstrip()) <= key_column:
                break
            block.append(later)
        yield index + 1, "\n".join(block)


class WorkflowTests(unittest.TestCase):
    """The workflow file itself, read as text: the project has no YAML parser."""

    text = (ROOT / ".github" / "workflows" / "maintenance.yml").read_text(encoding="utf-8")
    code = without_comments(text)

    def job(self, name):
        start = self.code.index(f"\n  {name}:")
        following = re.search(r"\n  [a-z][a-z0-9_-]*:", self.code[start + 1:])
        return self.code[start:start + 1 + following.start()] if following else self.code[start:]

    def test_only_the_publish_job_can_write_and_only_issues(self):
        writes = re.findall(r"[a-z-]+\s*:\s*write\b", self.code)
        self.assertEqual(writes, ["issues: write"])
        self.assertIn("issues: write", self.job("publish"))
        self.assertNotIn("write-all", self.code)
        self.assertNotIn("read-all", self.code)
        # The default for every job is read-only.
        top = self.code[:self.code.index("\njobs:")]
        self.assertIn("permissions:\n  contents: read", top)

    def test_publish_never_runs_on_pull_requests(self):
        self.assertIn("if: github.event_name != 'pull_request'", self.job("publish"))

    def test_nothing_is_interpolated_into_a_shell_command(self):
        blocks = list(run_blocks(self.code))
        self.assertGreaterEqual(len(blocks), 3)
        for line, block in blocks:
            self.assertNotIn("${{", block, f"line {line}")

    def test_the_run_scanner_sees_every_way_of_writing_a_step(self):
        sample = ("steps:\n      - run: echo \"${{ github.event.head_commit.message }}\"\n"
                  "      - name: x\n        run: |\n          echo one\n          echo ${{ github.head_ref }}\n"
                  "        env:\n          A: ${{ github.token }}\n")
        found = [block for _, block in run_blocks(sample) if "${{" in block]
        self.assertEqual(len(found), 2)
        self.assertNotIn("github.token", "".join(found))

    def test_no_secrets_are_used(self):
        self.assertNotIn("secrets", self.code.lower())

    def test_pull_requests_do_not_share_the_publishing_queue(self):
        self.assertIn("github.event_name == 'pull_request' && github.ref || 'publish'", self.text)

    def test_the_network_checks_fit_inside_the_report_jobs_time_limit(self):
        """Each check has a deadline and each run a budget. Together they must
        end well before GitHub stops the job, or a slow week publishes nothing."""
        minutes = int(re.search(r"timeout-minutes:\s*(\d+)", self.job("report")).group(1))
        self.assertNotIn("--timeout", self.code)   # so the report's default applies
        source = (ROOT / "scripts" / "maintenance_report.py").read_text(encoding="utf-8")
        timeout = int(re.search(r'"--timeout", type=int, default=(\d+)', source).group(1))
        links = inspect.signature(link_check.check_all).parameters
        upstream = inspect.signature(upstream_check.check_all).parameters
        worst = (links["budget"].default + link_check.link_deadline(timeout, links["pause"].default)
                 + upstream["budget"].default + upstream["pause"].default
                 + upstream_check.record_deadline(timeout))
        setup = 180   # checkout, Python, the offline sections and the upload
        self.assertLessEqual(worst + setup, minutes * 60)


class ValidateWorkflowTests(unittest.TestCase):
    """The read-only test workflow must run on every pull request, including one
    that only changes a workflow, so it can be a required check."""

    text = (ROOT / ".github" / "workflows" / "validate.yml").read_text(encoding="utf-8")
    code = without_comments(text)

    def test_no_path_filters(self):
        self.assertNotIn("paths:", self.code)
        self.assertNotIn("paths-ignore:", self.code)
        self.assertIn("pull_request:", self.code)

    def test_read_only(self):
        self.assertNotRegex(self.code, r":\s*write\b")
        self.assertNotIn("secrets", self.code.lower())
        self.assertIn("permissions:\n  contents: read", self.code)


if __name__ == "__main__":
    unittest.main()
