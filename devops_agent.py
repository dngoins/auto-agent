"""
DevOps Agent - Handles all git, CI, and state management operations.

This agent consolidates all infrastructure operations into a single interface,
separating state management from code decision-making.
"""

import subprocess
import json
import time
import os
from typing import Optional


class DevOpsAgent:
    """
    DevOps Agent responsible for:
    - Git operations (branch, commit, push)
    - PR management (create, status, auto-merge)
    - CI operations (logs, status checks)
    - Environment detection (CI vs local)
    """

    def __init__(self):
        """Initialize DevOps agent with environment detection"""
        self.is_ci = self._detect_ci_mode()
        self.current_branch = self._get_current_branch()

    # Environment Detection
    # =====================

    def _detect_ci_mode(self) -> bool:
        """Detect if running in CI environment or local mode"""
        in_ci = os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"
        current_branch = self._get_current_branch()
        on_feature_branch = current_branch not in ["main", "master"]
        return in_ci or on_feature_branch

    def _get_current_branch(self) -> str:
        """Get the current git branch name"""
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()

    def is_ci_mode(self) -> bool:
        """Check if running in CI mode"""
        return self.is_ci

    # Git Operations
    # ==============

    def create_branch(self) -> str:
        """
        Create a new feature branch with timestamp-based name.
        Returns the branch name.
        """
        branch_name = f"agent-{int(time.time())}"
        subprocess.run(["git", "checkout", "-b", branch_name])
        subprocess.run(["git", "push", "-u", "origin", branch_name])
        self.current_branch = branch_name
        print(f"Created branch: {branch_name}")
        return branch_name

    def configure_git(self, name: str, email: str) -> None:
        """Configure git user name and email (for CI environment)"""
        subprocess.run(["git", "config", "--global", "user.name", name])
        subprocess.run(["git", "config", "--global", "user.email", email])
        print(f"Configured git user: {name} <{email}>")

    def commit_changes(self, message: str) -> None:
        """Stage all changes and create a commit"""
        subprocess.run(["git", "add", "."])
        subprocess.run(["git", "commit", "-m", message])
        print(f"Committed: {message}")

    def push_changes(self, force: bool = False) -> None:
        """Push changes to remote (with optional force push)"""
        if force:
            subprocess.run(["git", "push", "--force"])
            print("Force pushed changes")
        else:
            subprocess.run(["git", "push"])
            print("Pushed changes")

    # PR Operations
    # =============

    def create_pr(self, title: str, body: str) -> int:
        """
        Create a new pull request.
        Returns the PR number.
        """
        subprocess.run([
            "gh", "pr", "create",
            "--title", title,
            "--body", body,
            "--fill"
        ])

        result = subprocess.run(
            ["gh", "pr", "view", "--json", "number"],
            capture_output=True,
            text=True
        )

        pr_number = json.loads(result.stdout)["number"]
        print(f"Created PR #{pr_number}")
        return pr_number

    def get_pr_number(self) -> Optional[int]:
        """Get the PR number for the current branch. Returns None if no PR exists."""
        result = subprocess.run(
            ["gh", "pr", "view", "--json", "number"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0 or not result.stdout.strip():
            # No PR exists for current branch
            return None
        pr_number = json.loads(result.stdout)["number"]
        return pr_number

    def enable_auto_merge(self, pr_number: int) -> bool:
        """
        Enable auto-merge with squash strategy for a PR.
        Returns True if successful, False otherwise.
        """
        result = subprocess.run(
            ["gh", "pr", "merge", str(pr_number),
             "--auto",
             "--squash",
             "--delete-branch"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"✓ Auto-merge enabled for PR #{pr_number}")
            print("PR will merge automatically when all checks pass")
            return True
        else:
            print(f"Warning: Could not enable auto-merge: {result.stderr}")
            print("PR may require manual review or approval")
            return False

    # CI Operations
    # =============

    def get_pr_status(self, pr_number: int) -> dict:
        """
        Get PR status and check results.
        Returns a dict with 'all_passed' and 'checks' fields.
        """
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_number),
             "--json", "statusCheckRollup"],
            capture_output=True,
            text=True
        )

        ci_data = json.loads(result.stdout)
        checks = ci_data.get("statusCheckRollup", [])
        all_passed = all(
            check.get("conclusion") == "SUCCESS"
            for check in checks
            if check.get("conclusion")
        )

        return {
            "all_passed": all_passed,
            "checks": checks
        }

    def get_failed_test_logs(self) -> Optional[str]:
        """
        Get logs from the test workflow run that triggered this repair agent.
        Returns logs as string, or None if not available.
        """
        if not os.environ.get("GITHUB_ACTIONS") == "true":
            return None

        runs = subprocess.run(
            ["gh", "run", "list", "--workflow", "Python Tests", "--limit", "5",
             "--json", "databaseId,conclusion,status"],
            capture_output=True,
            text=True
        )

        runs_data = json.loads(runs.stdout)

        # Find the most recent failed run
        for run in runs_data:
            if run.get("conclusion") == "failure":
                run_id = run["databaseId"]
                print(f"Fetching logs from failed test run #{run_id}")
                return self._get_run_logs_by_id(run_id)

        return None

    def get_latest_run_logs(self) -> str:
        """Get logs from the most recent workflow run"""
        runs = subprocess.run(
            ["gh", "run", "list", "--limit", "1", "--json", "databaseId"],
            capture_output=True,
            text=True
        )
        run_id = json.loads(runs.stdout)[0]["databaseId"]

        logs = subprocess.run(
            ["gh", "run", "view", str(run_id), "--log"],
            capture_output=True,
            text=True
        )

        return logs.stdout

    def _get_run_logs_by_id(self, run_id: int) -> str:
        """Get logs from a specific workflow run ID"""
        logs = subprocess.run(
            ["gh", "run", "view", str(run_id), "--log"],
            capture_output=True,
            text=True
        )
        return logs.stdout

    def extract_ci_logs(self, checks: list) -> str:
        """Extract failure information from CI checks"""
        ci_logs = "CI Checks Failed:\n"
        for check in checks:
            if check.get("conclusion") not in ["SUCCESS", None]:
                ci_logs += f"\n{check.get('name')}: {check.get('conclusion')}\n"
                if check.get("detailsUrl"):
                    ci_logs += f"Details: {check.get('detailsUrl')}\n"
        return ci_logs

    def wait_for_ci(self, seconds: int = 30) -> None:
        """Wait for CI to start running"""
        print(f"Waiting {seconds} seconds for CI to run...")
        time.sleep(seconds)

    # Safety Operations
    # =================

    def count_agent_commits(self) -> int:
        """Count how many recent commits were made by agent-bot"""
        result = subprocess.run(
            ["git", "log", "--format=%an", "-10"],
            capture_output=True,
            text=True
        )
        commits = result.stdout.strip().split("\n")
        agent_count = sum(1 for author in commits if author == "agent-bot")
        return agent_count

    def check_runaway_protection(self, max_commits: int = 7) -> None:
        """
        Check for runaway loop protection.
        Exits if too many agent commits detected.
        """
        agent_commit_count = self.count_agent_commits()
        print(f"Found {agent_commit_count} recent agent-bot commits")

        if agent_commit_count >= max_commits:
            print(f"ERROR: Too many agent-bot commits ({agent_commit_count}). Stopping to prevent runaway loop.")
            print(f"The agent has already attempted to fix this issue {max_commits} times.")
            print("Manual intervention is required.")
            exit(1)

    # GitHub Context Extraction
    # =========================

    def get_issue_body(self, issue_number: int) -> str:
        """Get issue description from GitHub"""
        result = subprocess.run(
            ["gh", "issue", "view", str(issue_number), "--json", "body"],
            capture_output=True,
            text=True
        )
        data = json.loads(result.stdout)
        return data['body']

    def get_issue_labels(self, issue_number: int) -> list:
        """Get labels from a GitHub issue"""
        result = subprocess.run(
            ["gh", "issue", "view", str(issue_number), "--json", "labels"],
            capture_output=True,
            text=True
        )
        data = json.loads(result.stdout)
        return [label['name'] for label in data['labels']]

    def get_pr_description(self, pr_number: int) -> str:
        """Get PR description from GitHub"""
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "body"],
            capture_output=True,
            text=True
        )
        data = json.loads(result.stdout)
        return data['body']

    def get_pr_labels(self, pr_number: int) -> list:
        """Get labels from a pull request"""
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "labels"],
            capture_output=True,
            text=True
        )
        data = json.loads(result.stdout)
        return [label['name'] for label in data['labels']]

    def comment_on_issue(self, issue_number: int, comment: str) -> None:
        """Post a comment on a GitHub issue"""
        subprocess.run(
            ["gh", "issue", "comment", str(issue_number), "--body", comment]
        )
        print(f"Posted comment to issue #{issue_number}")

    def comment_on_pr(self, pr_number: int, comment: str) -> None:
        """Post a comment on a pull request"""
        subprocess.run(
            ["gh", "pr", "comment", str(pr_number), "--body", comment]
        )
        print(f"Posted comment to PR #{pr_number}")

    def update_pr_body(self, pr_number: int, body: str) -> None:
        """Update PR description"""
        subprocess.run(
            ["gh", "pr", "edit", str(pr_number), "--body", body]
        )
        print(f"Updated PR #{pr_number} description")
