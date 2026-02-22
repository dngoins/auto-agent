"""
Multi-Agent Controller - Orchestrates the agent pipeline.

Architecture:
    Controller → Planner → Coder → Tester → Reviewer → DevOps

Each agent has a strict, limited role with clean information boundaries.
The controller manages the iteration loop and feedback between agents.
"""

import subprocess
import json
import os
from pathlib import Path
from typing import Optional

from devops_agent import DevOpsAgent
from agent_caller import AgentCaller
from contracts import PlannerOutput, CoderOutput, ReviewerOutput

# Configuration
MAX_ITERS = 10
MAX_REVIEWER_RETRIES = 3


def run_tests() -> tuple[int, str]:
    """Run pytest and return (exit_code, output)"""
    result = subprocess.run(
        ["pytest"],
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout


def collect_files() -> dict:
    """
    Collect all Python files in the repository.
    Returns dict of {path: content}
    """
    files_data = {}
    for file in Path(".").glob("*.py"):
        # Skip controller to avoid self-modification
        if "controller" in str(file):
            continue
        files_data[str(file)] = file.read_text()
    return files_data


def apply_changes(files: list) -> None:
    """Apply file changes to disk"""
    for file in files:
        Path(file["path"]).write_text(file["content"])
    print(f"Applied changes to {len(files)} file(s)")


def is_repeating_strategy(iteration_history: list, window: int = 3) -> bool:
    """
    Detect if the same strategy is being repeated.
    Returns True if the last 'window' iterations have the same strategy.
    """
    if len(iteration_history) < window:
        return False

    recent_strategies = [
        entry["strategy"]
        for entry in iteration_history[-window:]
    ]

    # Check if all recent strategies are identical
    return len(set(recent_strategies)) == 1


def main():
    """Main controller loop implementing multi-agent pipeline"""

    print("=== Multi-Agent Autonomous Repair System ===\n")

    # Initialize agents
    devops = DevOpsAgent()
    agent_caller = AgentCaller()

    # Setup: Environment detection and initialization
    if devops.is_ci_mode():
        print(f"Running in CI mode on branch: {devops.current_branch}")

        # Safety: Check for runaway loop
        devops.check_runaway_protection()

        # Configure git for CI
        devops.configure_git("agent-bot", "agent@bot.com")

        # Get existing PR number
        pr_number = devops.get_pr_number()
        print(f"Fixing existing PR #{pr_number}")
        first_commit_made = True
    else:
        print("Running in local mode - creating new branch...")
        devops.create_branch()
        pr_number = None
        first_commit_made = False

    # Initial CI logs (if in CI mode)
    ci_logs = ""
    if devops.is_ci_mode():
        print("Fetching failed test logs from CI...")
        initial_ci_logs = devops.get_failed_test_logs()
        if initial_ci_logs:
            ci_logs = initial_ci_logs
            print("Successfully fetched CI test logs")
        else:
            print("Warning: Could not fetch CI logs, will run tests locally")

    # Track iteration history for reflection
    iteration_history = []
    previous_attempt_failed = False
    previous_failure_reason = None

    # Main iteration loop - Agent Governance Pattern
    for iteration in range(MAX_ITERS):
        print(f"\n{'='*60}")
        print(f"=== Iteration {iteration + 1}/{MAX_ITERS} ===")
        print(f"{'='*60}\n")

        # Step 1: Run tests
        # -----------------
        if ci_logs and iteration == 0 and devops.is_ci_mode():
            print("Using fetched CI logs, skipping local test run")
            test_code = 1  # Mark as failed
            test_output = ""
        else:
            print("Running tests...")
            test_code, test_output = run_tests()

        # Exit if tests pass
        if test_code == 0 and not ci_logs:
            print("\n✓ All tests passed!")
            if pr_number:
                devops.enable_auto_merge(pr_number)
            break

        # Step 2: Collect repository state
        # ---------------------------------
        print("Collecting repository files...")
        repo_state = collect_files()

        # Step 3: Call Planner Agent
        # ---------------------------
        print("\n[PLANNER] Analyzing test failures...")
        print(f"  Previous attempt failed: {previous_attempt_failed}")

        plan = agent_caller.call_planner(
            test_result=test_output,
            ci_logs=ci_logs,
            repo_state=repo_state,
            previous_attempt_failed=previous_attempt_failed,
            failure_reason=previous_failure_reason
        )

        print(f"[PLANNER] Strategy: {plan['strategy']}")
        print(f"[PLANNER] Files to modify: {', '.join(plan['files_to_modify'])}")
        print(f"[PLANNER] Needs new tests: {plan['needs_new_tests']}")
        print(f"[PLANNER] Strategy changed: {plan['should_strategy_change']}")

        # Track iteration history
        iteration_history.append({
            "iteration": iteration + 1,
            "strategy": plan["strategy"],
            "strategy_changed": plan.get("should_strategy_change", False)
        })

        # Detect infinite loops (same strategy 3+ times)
        if is_repeating_strategy(iteration_history, window=3):
            print("\n❌ ERROR: Strategy is repeating. Same approach tried 3 times.")
            print("The agent appears stuck in a loop. Manual intervention required.")
            break

        # Step 4: Call Coder Agent
        # -------------------------
        print("\n[CODER] Implementing repair plan...")

        changes = agent_caller.call_coder(
            plan=plan,
            repo_state=repo_state
        )

        print(f"[CODER] Modified {len(changes['files'])} file(s)")
        print(f"[CODER] Commit message: {changes['commit_message']}")

        # Step 5: Call Tester Agent (if needed)
        # --------------------------------------
        if plan.get("needs_new_tests", False):
            print("\n[TESTER] Writing test cases...")

            test_changes = agent_caller.call_tester(
                changes=changes,
                repo_state=repo_state,
                plan=plan
            )

            print(f"[TESTER] Created/updated {len(test_changes['files'])} test file(s)")
            print(f"[TESTER] Strategy: {test_changes['test_strategy']}")

            # Merge test files into changes
            changes["files"].extend(test_changes["files"])

        # Step 6: Call Reviewer Agent
        # ----------------------------
        print("\n[REVIEWER] Reviewing changes...")

        review = agent_caller.call_reviewer(
            repo_state=repo_state,
            changes=changes,
            test_result=test_output or ci_logs
        )

        # Handle review decision
        if not review["approved"]:
            print(f"[REVIEWER] ❌ REJECTED - {len(review['issues'])} issue(s) found")
            print(f"[REVIEWER] Feedback: {review['feedback']}")

            # Log issues
            for issue in review['issues']:
                print(f"  - {issue['file']}:{issue['line']} - {issue['issue']}")

            # Feed rejection back to Planner for next iteration
            previous_attempt_failed = True
            previous_failure_reason = f"Reviewer rejected: {review['feedback']}"

            # Continue loop - Planner will see rejection and adjust
            continue

        print("[REVIEWER] ✓ APPROVED")
        print(f"[REVIEWER] Feedback: {review['feedback']}")

        # Step 7: DevOps Agent - Apply and commit
        # ----------------------------------------
        print("\n[DEVOPS] Applying changes and committing...")

        apply_changes(changes["files"])
        devops.commit_changes(changes["commit_message"])

        # Push changes
        if devops.is_ci_mode():
            devops.push_changes(force=True)
        else:
            if first_commit_made:
                devops.push_changes(force=True)
            else:
                devops.push_changes(force=False)
                first_commit_made = True

        # Create PR if needed (local mode only)
        if pr_number is None:
            print("[DEVOPS] Creating pull request...")
            pr_number = devops.create_pr(
                title="Autonomous Fix - Multi-Agent System",
                body="Generated by multi-agent autonomous repair system\n\n" +
                     f"Strategy: {plan['strategy']}\n\n" +
                     f"Files modified: {', '.join([f['path'] for f in changes['files']])}"
            )

        # Step 8: Wait for CI and check results
        # --------------------------------------
        devops.wait_for_ci(30)

        print("[DEVOPS] Checking CI status...")
        ci_status = devops.get_pr_status(pr_number)

        if ci_status['all_passed'] and ci_status['checks']:
            print("\n✓ All CI checks passed!")

            # Enable auto-merge
            if devops.is_ci_mode() and pr_number:
                devops.enable_auto_merge(pr_number)

            break
        else:
            print("CI checks failed, extracting logs...")

            # Extract failure logs for next iteration
            ci_logs = devops.extract_ci_logs(ci_status['checks'])

            # Get detailed workflow logs
            print("Fetching detailed workflow logs...")
            run_logs = devops.get_latest_run_logs()
            ci_logs += f"\n\nWorkflow Run Logs:\n{run_logs}"

            # Mark as failed for next iteration
            previous_attempt_failed = True
            previous_failure_reason = "CI checks failed"

            # Loop continues with updated CI logs

    # End of iteration loop
    print("\n" + "="*60)
    print("=== Autonomous Repair Session Complete ===")
    print("="*60)

    # Print summary
    print(f"\nTotal iterations: {len(iteration_history)}")
    print(f"Final status: {'SUCCESS' if test_code == 0 or ci_status.get('all_passed') else 'INCOMPLETE'}")


if __name__ == "__main__":
    main()
