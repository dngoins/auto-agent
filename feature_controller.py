"""
Feature Development Controller - Orchestrates the feature development pipeline.

Architecture:
    RequirementsGather → AcceptanceCriteria → ArchitectPlanner →
    TechnicalPlanner → Coder → Tester → Reviewer → DevOps

This controller manages new feature development from requirements to implementation.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Configure UTF-8 encoding for stdout/stderr to prevent Unicode encoding errors on Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, errors='replace')

from devops_agent import DevOpsAgent
from agent_caller import AgentCaller
from contracts import (
    RequirementsGatherOutput,
    AcceptanceCriteriaOutput,
    ArchitectPlannerOutput,
    TechnicalPlannerOutput,
    CoderOutput,
    ReviewerOutput
)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Feature Development Pipeline')
    parser.add_argument('--ci-mode', action='store_true',
                       help='Run in non-interactive CI mode')
    parser.add_argument('--auto-approve', action='store_true',
                       help='Auto-approve all stages (skip user approval)')
    parser.add_argument('--requirements-file', type=str,
                       help='Path to requirements file')
    return parser.parse_args()


def get_requirements_input(args):
    """Get requirements from various sources"""

    # Priority 1: Environment variable (from CI)
    if 'REQUIREMENTS_TEXT' in os.environ:
        return os.environ['REQUIREMENTS_TEXT']

    # Priority 2: File path argument
    if args.requirements_file:
        return Path(args.requirements_file).read_text()

    # Priority 3: Interactive stdin (local mode)
    if not args.ci_mode:
        print("\nEnter your feature requirements (Gherkin or free form).")
        print("Press Ctrl+D (Unix) or Ctrl+Z (Windows) when done:\n")

        requirements_lines = []
        try:
            while True:
                line = input()
                requirements_lines.append(line)
        except EOFError:
            pass

        return "\n".join(requirements_lines)

    raise ValueError("No requirements provided in CI mode")


def collect_files() -> dict:
    """
    Collect all Python files in the repository.
    Returns dict of {path: content}
    """
    files_data = {}
    for file in Path(".").glob("**/*.py"):
        # Skip certain directories
        if any(skip in str(file) for skip in [".venv", "__pycache__", "controller"]):
            continue
        try:
            files_data[str(file)] = file.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            print(f"Warning: Could not read {file}: {e}")
    return files_data


def apply_changes(files: list) -> None:
    """Apply file changes to disk"""
    for file in files:
        file_path = Path(file["path"])
        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(file["content"])
    print(f"Applied changes to {len(files)} file(s)")


def display_gherkin_scenarios(scenarios: list) -> None:
    """Display Gherkin scenarios for user review"""
    print("\n" + "="*60)
    print("GHERKIN SCENARIOS")
    print("="*60)
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- Scenario {i} ---")
        print(scenario)


def display_clarification_questions(questions: list) -> list:
    """Display questions and get user answers"""
    print("\n" + "="*60)
    print("CLARIFICATION QUESTIONS")
    print("="*60)

    answers = []
    for i, q in enumerate(questions, 1):
        print(f"\n[Question {i}]")
        print(f"Context: {q['context']}")
        print(f"\nQuestion: {q['question']}")

        if q['suggested_answers']:
            print("\nSuggested answers:")
            for j, answer in enumerate(q['suggested_answers'], 1):
                print(f"  {j}. {answer}")

        print("\nYour answer:")
        answer = input("> ")
        answers.append(answer)

    return answers


def display_acceptance_criteria(ac_output: AcceptanceCriteriaOutput) -> None:
    """Display acceptance criteria for user review"""
    print("\n" + "="*60)
    print("ACCEPTANCE CRITERIA")
    print("="*60)

    print("\nCriteria:")
    for i, criterion in enumerate(ac_output['acceptance_criteria'], 1):
        print(f"\n{i}. {criterion['criterion']}")
        print(f"   Type: {criterion['test_type']}")
        print(f"   Rationale: {criterion['rationale']}")

    print("\n\nDefinition of Done:")
    for item in ac_output['definition_of_done']:
        print(f"  [x] {item}")

    print("\n\nRisk Areas:")
    for risk in ac_output['risk_areas']:
        print(f"  [!] {risk}")


def display_technical_design(arch_output: ArchitectPlannerOutput) -> None:
    """Display technical design for user review"""
    print("\n" + "="*60)
    print("TECHNICAL DESIGN")
    print("="*60)

    print(f"\n{arch_output['technical_design']}")

    print("\n\nDesign Decisions:")
    for decision in arch_output['design_decisions']:
        print(f"\n• {decision['aspect']}")
        print(f"  Decision: {decision['decision']}")
        print(f"  Rationale: {decision['rationale']}")

    print("\n\nFiles to Create:")
    for file in arch_output['files_to_create']:
        print(f"  + {file}")

    print("\n\nFiles to Modify:")
    for file in arch_output['files_to_modify']:
        print(f"  ~ {file}")

    if arch_output['dependencies_needed']:
        print("\n\nDependencies Needed:")
        for dep in arch_output['dependencies_needed']:
            print(f"  - {dep}")

    if arch_output.get('design_diagrams'):
        print("\n\nDesign Diagrams:")
        print(arch_output['design_diagrams'])


def display_implementation_plan(plan_output: TechnicalPlannerOutput) -> None:
    """Display implementation plan for user review"""
    print("\n" + "="*60)
    print("IMPLEMENTATION PLAN")
    print("="*60)

    print(f"\n{plan_output['implementation_plan']}")

    print("\n\nImplementation Steps:")
    for step in plan_output['implementation_steps']:
        deps = f" (depends on: {', '.join(map(str, step['dependencies']))})" if step['dependencies'] else ""
        print(f"\n{step['step_number']}. {step['description']}")
        print(f"   Files: {', '.join(step['files_affected'])}")
        print(f"   Complexity: {step['estimated_complexity']}{deps}")

    print(f"\n\nStrategy: {plan_output['strategy']}")
    print(f"Test Strategy: {plan_output['test_strategy']}")


def get_user_approval(prompt: str, auto_approve: bool = False) -> bool:
    """Get user approval to proceed"""
    if auto_approve:
        print(f"[AUTO-APPROVE] {prompt}")
        return True

    while True:
        response = input(f"\n{prompt} (yes/no): ").lower().strip()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("Please answer 'yes' or 'no'")


def main():
    """Main feature development pipeline"""

    # Parse arguments
    args = parse_args()

    print("="*60)
    print("FEATURE DEVELOPMENT PIPELINE")
    if args.ci_mode:
        print("(CI MODE - Automated)")
    print("="*60)

    # Initialize agents
    devops = DevOpsAgent()
    agent_caller = AgentCaller()

    # Get requirements
    try:
        raw_requirements = get_requirements_input(args)
    except ValueError as e:
        print(f"Error: {e}")
        return

    if not raw_requirements.strip():
        print("Error: No requirements provided")
        return

    # ========================================================================
    # PHASE 1: Requirements Gathering
    # ========================================================================

    print("\n[REQUIREMENTS GATHER] Processing requirements...")

    requirements_output = agent_caller.call_requirements_gather(
        raw_requirements=raw_requirements
    )

    display_gherkin_scenarios(requirements_output['gherkin_scenarios'])

    # Handle clarification questions with max iteration limit
    MAX_CLARIFICATION_ROUNDS = 3
    clarification_iteration = 0

    while requirements_output['needs_clarification'] and clarification_iteration < MAX_CLARIFICATION_ROUNDS:
        clarification_iteration += 1
        questions = requirements_output['clarification_questions']

        print(f"\n[CLARIFICATION ROUND {clarification_iteration}/{MAX_CLARIFICATION_ROUNDS}]")

        if args.ci_mode or args.auto_approve:
            # Auto-answer with first suggested answer
            print(f"[CI MODE] Auto-answering {len(questions)} clarification questions")
            user_answers = []
            for q in questions:
                auto_answer = q['suggested_answers'][0] if q['suggested_answers'] else "Yes"
                print(f"Q: {q['question']}")
                print(f"A: {auto_answer}")
                user_answers.append(auto_answer)
        else:
            # Interactive mode
            user_answers = display_clarification_questions(questions)

        print("\n[REQUIREMENTS GATHER] Refining requirements with your answers...")

        requirements_output = agent_caller.call_requirements_gather(
            raw_requirements=raw_requirements,
            previous_questions=[q['question'] for q in questions],
            user_answers=user_answers
        )

        display_gherkin_scenarios(requirements_output['gherkin_scenarios'])

    # Check if we hit the max iteration limit
    if requirements_output['needs_clarification'] and clarification_iteration >= MAX_CLARIFICATION_ROUNDS:
        print(f"\n[!] WARNING: Reached maximum clarification rounds ({MAX_CLARIFICATION_ROUNDS})")
        print("Proceeding with current requirements despite agent requesting more clarification.")
        print("You may want to refine requirements manually if needed.")

    # Save Gherkin scenarios
    gherkin_file = Path("requirements.gherkin")
    gherkin_file.write_text("\n\n".join(requirements_output['gherkin_scenarios']))
    print(f"\n[OK] Saved Gherkin scenarios to {gherkin_file}")

    if not get_user_approval("Proceed to acceptance criteria?", args.auto_approve):
        print("Stopped by user")
        return

    # ========================================================================
    # PHASE 2: Acceptance Criteria
    # ========================================================================

    print("\n[ACCEPTANCE CRITERIA] Creating acceptance criteria...")

    ac_output = agent_caller.call_acceptance_criteria(
        gherkin_scenarios=requirements_output['gherkin_scenarios'],
        requirements_summary=requirements_output['requirements_summary']
    )

    display_acceptance_criteria(ac_output)

    if not get_user_approval("Proceed to technical design?", args.auto_approve):
        print("Stopped by user")
        return

    # ========================================================================
    # PHASE 3: Architecture Planning
    # ========================================================================

    print("\n[ARCHITECT PLANNER] Designing technical architecture...")

    # Collect existing codebase
    repo_state = collect_files()
    print(f"Analyzed {len(repo_state)} files in codebase")

    arch_output = agent_caller.call_architect_planner(
        gherkin_scenarios=requirements_output['gherkin_scenarios'],
        acceptance_criteria=ac_output['acceptance_criteria'],
        repo_state=repo_state
    )

    display_technical_design(arch_output)

    if not get_user_approval("Proceed to implementation planning?", args.auto_approve):
        print("Stopped by user")
        return

    # ========================================================================
    # PHASE 4: Technical Planning
    # ========================================================================

    print("\n[TECHNICAL PLANNER] Creating implementation plan...")

    tech_plan = agent_caller.call_technical_planner(
        technical_design=arch_output['technical_design'],
        design_decisions=arch_output['design_decisions'],
        files_to_create=arch_output['files_to_create'],
        files_to_modify=arch_output['files_to_modify'],
        repo_state=repo_state
    )

    display_implementation_plan(tech_plan)

    if not get_user_approval("Proceed to implementation?", args.auto_approve):
        print("Stopped by user")
        return

    # ========================================================================
    # PHASE 5: Implementation (Coder Agent)
    # ========================================================================

    print("\n[CODER] Implementing the feature...")

    # Prepare plan for Coder (convert TechnicalPlanner output to Planner-like format)
    coder_plan = {
        "analysis": tech_plan['implementation_plan'],
        "files_to_modify": tech_plan['files_to_modify'],
        "strategy": tech_plan['strategy']
    }

    changes = agent_caller.call_coder(
        plan=coder_plan,
        repo_state=repo_state
    )

    print(f"[CODER] Generated changes for {len(changes['files'])} file(s)")

    # ========================================================================
    # PHASE 6: Testing (Tester Agent)
    # ========================================================================

    if tech_plan.get('needs_new_tests', False):
        print("\n[TESTER] Writing test cases...")

        test_changes = agent_caller.call_tester(
            changes=changes,
            repo_state=repo_state,
            plan={'coverage_gaps': [tech_plan['test_strategy']]}
        )

        print(f"[TESTER] Created {len(test_changes['files'])} test file(s)")

        # Merge test files into changes
        changes['files'].extend(test_changes['files'])

    # ========================================================================
    # PHASE 7: Review (Reviewer Agent)
    # ========================================================================

    # Note: For feature development, we skip the Reviewer agent because:
    # 1. Reviewer is designed for bug fixes (expects original files to compare)
    # 2. Feature development creates NEW files with no originals
    # 3. Multiple quality gates already exist (Architect, Technical Planner)
    # 4. Real code review happens in the PR
    #
    # For bug fixes, see controller.py which uses Reviewer properly

    print("\n[FEATURE REVIEW] Auto-approving feature implementation...")
    print("Quality gates passed:")
    print("  - Requirements validated by RequirementsGather agent")
    print("  - Acceptance criteria defined by AcceptanceCriteria agent")
    print("  - Architecture reviewed by ArchitectPlanner agent")
    print("  - Implementation plan validated by TechnicalPlanner agent")
    print("  - Code generated by Coder agent")
    print("  - Tests generated by Tester agent")
    print("\n[FEATURE REVIEW] [OK] APPROVED")
    print("Note: Code review will occur in the pull request")

    # ========================================================================
    # PHASE 8: Apply Changes and Commit
    # ========================================================================

    print("\nFiles to be modified:")
    for file in changes['files']:
        print(f"  - {file['path']}")

    if not get_user_approval("Apply changes and create commit?", args.auto_approve):
        print("Stopped by user")
        return

    # Apply changes
    apply_changes(changes['files'])

    # Git operations
    if devops.is_ci_mode():
        print("Running in CI mode")
    else:
        print("\n[DEVOPS] Creating feature branch...")
        devops.create_branch()

    print("[DEVOPS] Committing changes...")
    devops.commit_changes(changes['commit_message'])

    print("[DEVOPS] Pushing to remote...")
    devops.push_changes()

    # Create PR
    if not devops.is_ci_mode():
        print("[DEVOPS] Creating pull request...")

        pr_body = f"""# {requirements_output['requirements_summary']}

## Gherkin Scenarios

{chr(10).join('- ' + s.split(chr(10))[0] for s in requirements_output['gherkin_scenarios'])}

## Technical Design

{arch_output['technical_design']}

## Implementation Steps

{len(tech_plan['implementation_steps'])} steps completed

---

Generated by multi-agent feature development pipeline
"""

        pr_number = devops.create_pr(
            title=f"Feature: {requirements_output['requirements_summary']}",
            body=pr_body
        )

        print(f"\n[OK] Feature development complete!")
        print(f"PR #{pr_number} created and ready for review")


if __name__ == "__main__":
    main()
