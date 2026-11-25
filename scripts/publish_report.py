#!/usr/bin/env python3
"""
publish_report.py

Posts the weekly maintenance report as a GitHub issue. It is run by the publish
job of .github/workflows/maintenance.yml, the only place in this repository
with permission to write anything, and that permission covers issues only.

It keeps one open issue titled "Maintenance report". Each week it replaces that
issue's text, and it adds a comment only when the number of items to look at
went up, so the issue does not turn into weekly noise. If the issue was closed,
the next run opens a fresh one.

Only an issue this workflow created counts. Anyone can open an issue with the
same title, and matching on the title alone would send the report into a
stranger's issue, which that stranger could then edit. So the author has to be
the GitHub Actions bot.

Usage, in the workflow:
    python3 scripts/publish_report.py report.md attention.txt

Needs the gh command, with GH_TOKEN and GH_REPO (owner/name) in the environment.
The report reaches gh as a file and nothing is passed through a shell.
"""

import json
import os
import re
import subprocess
import sys

TITLE = "Maintenance report"
# How GitHub's REST API names the account behind a workflow's own token.
BOT_LOGIN = "github-actions[bot]"
COUNT_IN_BODY = re.compile(r"\*\*([0-9]+) item")

# One compact JSON object per issue, across every page of results.
ISSUE_FIELDS = (".[] | {number: .number, title: .title, login: .user.login, "
                "type: .user.type, pull_request: (.pull_request != null)}")


def run_gh(args):
    """Run gh with these arguments and return what it printed. Raises if gh fails."""
    done = subprocess.run(["gh"] + list(args), check=True, stdout=subprocess.PIPE, universal_newlines=True)
    return done.stdout


def is_ours(issue):
    """An open issue with our title that this workflow's bot account created."""
    return (isinstance(issue, dict)
            and issue.get("title") == TITLE
            and issue.get("login") == BOT_LOGIN
            and issue.get("type") == "Bot"
            and not issue.get("pull_request"))


def find_report_issue(issues):
    """The number of our report issue, or None. GitHub lists newest first, so
    if there were ever two, the newest wins."""
    for issue in issues:
        if is_ours(issue):
            return issue.get("number")
    return None


def previous_count(body):
    """The item count the last report announced, or 0 if the text has none."""
    match = COUNT_IN_BODY.search(body or "")
    return int(match.group(1)) if match else 0


def read_count(path):
    with open(path, encoding="utf-8") as handle:
        digits = "".join(ch for ch in handle.read() if ch in "0123456789")
    return int(digits) if digits else 0


def list_open_issues(repo, gh):
    listing = gh(["api", "--paginate", f"repos/{repo}/issues?state=open&per_page=100", "--jq", ISSUE_FIELDS])
    return [json.loads(line) for line in listing.splitlines() if line.strip()]


def publish(report_path, count, repo, gh=run_gh):
    """Create or update the report issue. Returns what it did, for the log."""
    number = find_report_issue(list_open_issues(repo, gh))
    if number is None:
        gh(["issue", "create", "--repo", repo, "--title", TITLE, "--body-file", report_path])
        return "created a new issue"

    number = str(int(number))
    before = previous_count(gh(["issue", "view", number, "--repo", repo, "--json", "body", "--jq", ".body"]))
    gh(["issue", "edit", number, "--repo", repo, "--body-file", report_path])

    # Editing an issue notifies nobody. Comment only when there is more to do.
    if count > before:
        gh(["issue", "comment", number, "--repo", repo, "--body",
            f"The weekly report now lists {count} item(s) to look at, up from {before}. "
            "The issue description has the details."])
        return f"updated issue #{number} and commented ({before} -> {count})"
    return f"updated issue #{number} ({before} -> {count}, no comment)"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__)
        return 2
    report_path, count_path = argv
    repo = os.environ.get("GH_REPO", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        print("GH_REPO must be set to owner/name", file=sys.stderr)
        return 2
    try:
        print(publish(report_path, read_count(count_path), repo))
    except subprocess.CalledProcessError as exc:
        # gh has already printed its own error. Name the step that failed.
        print(f"gh {' '.join(exc.cmd[1:3])} failed with exit code {exc.returncode}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(f"could not publish the report: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
