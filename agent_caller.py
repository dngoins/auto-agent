"""
Agent Caller - Unified interface for calling specialized agents.

This module handles:
- Building prompts from templates
- Role isolation (information filtering)
- Calling Claude with structured output
- Parsing and validating responses
"""

import json
import subprocess
from pathlib import Path
from typing import Optional
import fnmatch

from contracts import (
    # Bug fix pipeline
    PlannerInput, PlannerOutput, PLANNER_SCHEMA,
    CoderInput, CoderOutput, CODER_SCHEMA,
    TesterInput, TesterOutput, TESTER_SCHEMA,
    ReviewerInput, ReviewerOutput, REVIEWER_SCHEMA,
    # Feature development pipeline
    RequirementsGatherInput, RequirementsGatherOutput, REQUIREMENTS_GATHER_SCHEMA,
    AcceptanceCriteriaInput, AcceptanceCriteriaOutput, ACCEPTANCE_CRITERIA_SCHEMA,
    ArchitectPlannerInput, ArchitectPlannerOutput, ARCHITECT_PLANNER_SCHEMA,
    TechnicalPlannerInput, TechnicalPlannerOutput, TECHNICAL_PLANNER_SCHEMA
)


class AgentCaller:
    """
    Unified interface for calling different agents with role isolation.

    Each agent receives ONLY the information it needs - no more, no less.
    This enforces clean separation of concerns.
    """

    def __init__(self):
        self.prompt_dir = Path("prompts")

    # Agent Call Methods
    # ==================

    def call_planner(
        self,
        test_result: str,
        ci_logs: str,
        repo_state: dict,
        previous_attempt_failed: bool = False,
        failure_reason: Optional[str] = None
    ) -> PlannerOutput:
        """
        Call Planner agent with test failures and code.

        Role Isolation:
        - GETS: Test failures, current code files
        - GETS: Previous attempt context (for reflection)
        - NO ACCESS TO: Git history, commit logs, CI details, PR info
        """
        # Filter input - only Python files
        filtered_files = self._filter_files(repo_state, ["*.py"])

        # Build prompt with role-isolated data
        prompt = self._build_planner_prompt(
            test_output=test_result,
            ci_logs=ci_logs,
            repository_files=filtered_files,
            previous_attempt_failed=previous_attempt_failed,
            failure_reason=failure_reason
        )

        # Call Claude with schema validation
        response = self._call_claude(prompt, PLANNER_SCHEMA)
        return response

    def call_coder(
        self,
        plan: PlannerOutput,
        repo_state: dict
    ) -> CoderOutput:
        """
        Call Coder agent with repair plan.

        Role Isolation:
        - GETS: Repair plan, files to modify
        - NO ACCESS TO: Test output, commit history, CI logs
        """
        # Only give files that need modification
        filtered_files = self._get_specific_files(
            repo_state,
            plan["files_to_modify"]
        )

        # Build prompt with role-isolated data
        prompt = self._build_coder_prompt(
            repair_plan=plan,
            repository_files=filtered_files
        )

        # Call Claude with schema validation
        response = self._call_claude(prompt, CODER_SCHEMA)
        return response

    def call_tester(
        self,
        changes: CoderOutput,
        repo_state: dict,
        plan: PlannerOutput
    ) -> TesterOutput:
        """
        Call Tester agent to write/update tests.

        Role Isolation:
        - GETS: Modified code files, existing test files
        - NO ACCESS TO: Implementation details, git history
        - CANNOT: Modify implementation code
        """
        # Only give test files
        existing_tests = self._filter_files(
            repo_state,
            ["test_*.py", "*_test.py"]
        )

        # Build prompt with role-isolated data
        prompt = self._build_tester_prompt(
            modified_code=changes["files"],
            existing_tests=existing_tests,
            coverage_gaps=plan.get("coverage_gaps", [])
        )

        # Call Claude with schema validation
        response = self._call_claude(prompt, TESTER_SCHEMA)
        return response

    def call_reviewer(
        self,
        repo_state: dict,
        changes: CoderOutput,
        test_result: str
    ) -> ReviewerOutput:
        """
        Call Reviewer agent with changes.

        Role Isolation:
        - GETS: Original files, modified files, test output
        - NO ACCESS TO: Git operations, commit authority
        - CANNOT: Modify files, only approve/reject
        """
        # Get original versions of modified files
        original_files = self._get_specific_files(
            repo_state,
            [f["path"] for f in changes["files"]]
        )

        # Build prompt with role-isolated data
        prompt = self._build_reviewer_prompt(
            original_files=original_files,
            modified_files=changes["files"],
            test_output=test_result
        )

        # Call Claude with schema validation
        response = self._call_claude(prompt, REVIEWER_SCHEMA)
        return response

    # Prompt Building Methods
    # =======================

    def _build_planner_prompt(
        self,
        test_output: str,
        ci_logs: str,
        repository_files: dict,
        previous_attempt_failed: bool,
        failure_reason: Optional[str]
    ) -> str:
        """Build prompt for Planner agent"""
        template = (self.prompt_dir / "planner.md").read_text()

        # Format repository files
        files_text = self._format_files(repository_files)

        # Build reflection context
        reflection_text = ""
        if previous_attempt_failed:
            reflection_text = f"""
## Reflection Context

⚠️ The previous repair attempt FAILED.

Failure reason: {failure_reason}

**IMPORTANT:** You must analyze why the previous strategy failed and either:
1. Adjust your strategy if the approach was wrong
2. Keep the strategy if the implementation was wrong (reviewer feedback)

Output field `should_strategy_change`: true if you're changing approach.
"""

        # Combine all sections
        prompt = f"""{template}

{reflection_text}

## Test Output

{test_output}

## CI Logs

{ci_logs}

## Repository Files

{files_text}

Output your response as raw JSON only (no markdown, no explanations):
"""
        return prompt

    def _build_coder_prompt(
        self,
        repair_plan: PlannerOutput,
        repository_files: dict
    ) -> str:
        """Build prompt for Coder agent"""
        template = (self.prompt_dir / "coder.md").read_text()

        # Format repository files
        files_text = self._format_files(repository_files)

        # Format repair plan
        plan_text = f"""Analysis: {repair_plan['analysis']}

Strategy: {repair_plan['strategy']}

Files to modify: {', '.join(repair_plan['files_to_modify'])}
"""

        # Combine all sections
        prompt = f"""{template}

## Repair Plan

{plan_text}

## Repository Files

{files_text}

Output your response as raw JSON only (no markdown, no explanations):
"""
        return prompt

    def _build_tester_prompt(
        self,
        modified_code: list,
        existing_tests: dict,
        coverage_gaps: list
    ) -> str:
        """Build prompt for Tester agent"""
        template = (self.prompt_dir / "tester.md").read_text()

        # Format modified code
        code_text = ""
        for file in modified_code:
            code_text += f"\n--- {file['path']} ---\n{file['content']}\n"

        # Format existing tests
        tests_text = self._format_files(existing_tests)

        # Format coverage gaps
        gaps_text = "\n".join(f"- {gap}" for gap in coverage_gaps)

        # Combine all sections
        prompt = f"""{template}

## Modified Code

{code_text}

## Existing Tests

{tests_text}

## Coverage Gaps

{gaps_text}

Output your response as raw JSON only (no markdown, no explanations):
"""
        return prompt

    def _build_reviewer_prompt(
        self,
        original_files: dict,
        modified_files: list,
        test_output: str
    ) -> str:
        """Build prompt for Reviewer agent"""
        template = (self.prompt_dir / "reviewer.md").read_text()

        # Format original files
        original_text = self._format_files(original_files)

        # Format modified files
        modified_text = ""
        for file in modified_files:
            modified_text += f"\n--- {file['path']} ---\n{file['content']}\n"

        # Combine all sections
        prompt = f"""{template}

## Original Files

{original_text}

## Modified Files

{modified_text}

## Test Output

{test_output}

Output your response as raw JSON only (no markdown, no explanations):
"""
        return prompt

    # ========================================================================
    # FEATURE DEVELOPMENT AGENTS
    # ========================================================================

    def call_requirements_gather(
        self,
        raw_requirements: str,
        previous_questions: Optional[list] = None,
        user_answers: Optional[list] = None
    ) -> RequirementsGatherOutput:
        """
        Call RequirementsGather agent to transform raw requirements into Gherkin.

        Role Isolation:
        - GETS: Raw requirements, previous Q&A context
        - NO ACCESS TO: Codebase, implementation details
        """
        prompt = self._build_requirements_gather_prompt(
            raw_requirements=raw_requirements,
            previous_questions=previous_questions,
            user_answers=user_answers
        )

        response = self._call_claude(prompt, REQUIREMENTS_GATHER_SCHEMA)
        return response

    def call_acceptance_criteria(
        self,
        gherkin_scenarios: list,
        requirements_summary: str
    ) -> AcceptanceCriteriaOutput:
        """
        Call AcceptanceCriteria agent to create testable acceptance criteria.

        Role Isolation:
        - GETS: Gherkin scenarios, requirements summary
        - NO ACCESS TO: Codebase, implementation details
        """
        prompt = self._build_acceptance_criteria_prompt(
            gherkin_scenarios=gherkin_scenarios,
            requirements_summary=requirements_summary
        )

        response = self._call_claude(prompt, ACCEPTANCE_CRITERIA_SCHEMA)
        return response

    def call_architect_planner(
        self,
        gherkin_scenarios: list,
        acceptance_criteria: list,
        repo_state: dict
    ) -> ArchitectPlannerOutput:
        """
        Call ArchitectPlanner agent to design technical architecture.

        Role Isolation:
        - GETS: Gherkin scenarios, acceptance criteria, existing codebase
        - NO ACCESS TO: Implementation details, test output
        """
        # Filter repository files (only Python files for context)
        filtered_files = self._filter_files(repo_state, ["*.py"])

        prompt = self._build_architect_planner_prompt(
            gherkin_scenarios=gherkin_scenarios,
            acceptance_criteria=acceptance_criteria,
            repository_files=filtered_files
        )

        response = self._call_claude(prompt, ARCHITECT_PLANNER_SCHEMA)
        return response

    def call_technical_planner(
        self,
        technical_design: str,
        design_decisions: list,
        files_to_create: list,
        files_to_modify: list,
        repo_state: dict
    ) -> TechnicalPlannerOutput:
        """
        Call TechnicalPlanner agent to create implementation plan.

        Role Isolation:
        - GETS: Technical design, files to create/modify, existing codebase
        - NO ACCESS TO: Test output, CI logs
        """
        # Get specific files that will be modified
        filtered_files = self._get_specific_files(repo_state, files_to_modify)

        prompt = self._build_technical_planner_prompt(
            technical_design=technical_design,
            design_decisions=design_decisions,
            files_to_create=files_to_create,
            files_to_modify=files_to_modify,
            repository_files=filtered_files
        )

        response = self._call_claude(prompt, TECHNICAL_PLANNER_SCHEMA)
        return response

    # ========================================================================
    # FEATURE DEVELOPMENT PROMPT BUILDERS
    # ========================================================================

    def _build_requirements_gather_prompt(
        self,
        raw_requirements: str,
        previous_questions: Optional[list],
        user_answers: Optional[list]
    ) -> str:
        """Build prompt for RequirementsGather agent"""
        template = (self.prompt_dir / "requirements_gather.md").read_text()

        # Format previous Q&A if exists
        qa_context = ""
        if previous_questions and user_answers:
            qa_context = "\n## Previous Questions and Answers\n\n"
            for q, a in zip(previous_questions, user_answers):
                qa_context += f"Q: {q}\nA: {a}\n\n"

        prompt = f"""{template}

## Raw Requirements

{raw_requirements}

{qa_context}

Output your response as raw JSON only (no markdown, no explanations):
"""
        return prompt

    def _build_acceptance_criteria_prompt(
        self,
        gherkin_scenarios: list,
        requirements_summary: str
    ) -> str:
        """Build prompt for AcceptanceCriteria agent"""
        template = (self.prompt_dir / "acceptance_criteria.md").read_text()

        # Format Gherkin scenarios
        scenarios_text = "\n\n".join(gherkin_scenarios)

        prompt = f"""{template}

## Requirements Summary

{requirements_summary}

## Gherkin Scenarios

{scenarios_text}

Output your response as raw JSON only (no markdown, no explanations):
"""
        return prompt

    def _build_architect_planner_prompt(
        self,
        gherkin_scenarios: list,
        acceptance_criteria: list,
        repository_files: dict
    ) -> str:
        """Build prompt for ArchitectPlanner agent"""
        template = (self.prompt_dir / "architect_planner.md").read_text()

        # Format Gherkin scenarios
        scenarios_text = "\n\n".join(gherkin_scenarios)

        # Format acceptance criteria
        criteria_text = ""
        for ac in acceptance_criteria:
            criteria_text += f"- {ac['criterion']} ({ac['test_type']})\n"
            criteria_text += f"  Rationale: {ac['rationale']}\n\n"

        # Format repository files
        files_text = self._format_files(repository_files)

        prompt = f"""{template}

## Gherkin Scenarios

{scenarios_text}

## Acceptance Criteria

{criteria_text}

## Existing Codebase

{files_text}

Output your response as raw JSON only (no markdown, no explanations):
"""
        return prompt

    def _build_technical_planner_prompt(
        self,
        technical_design: str,
        design_decisions: list,
        files_to_create: list,
        files_to_modify: list,
        repository_files: dict
    ) -> str:
        """Build prompt for TechnicalPlanner agent"""
        template = (self.prompt_dir / "technical_planner.md").read_text()

        # Format design decisions
        decisions_text = ""
        for decision in design_decisions:
            decisions_text += f"**{decision['aspect']}**: {decision['decision']}\n"
            decisions_text += f"Rationale: {decision['rationale']}\n\n"

        # Format files
        files_text = self._format_files(repository_files)

        prompt = f"""{template}

## Technical Design

{technical_design}

## Design Decisions

{decisions_text}

## Files to Create

{', '.join(files_to_create)}

## Files to Modify

{', '.join(files_to_modify)}

## Existing Files (to be modified)

{files_text}

Output your response as raw JSON only (no markdown, no explanations):
"""
        return prompt

    # Helper Methods
    # ==============

    def _call_claude(self, prompt: str, schema: dict) -> dict:
        """Execute Claude CLI with structured output"""
        result = subprocess.run(
            ["claude", "--print", "--output-format", "json",
             "--json-schema", json.dumps(schema)],
            input=prompt,
            text=True,
            capture_output=True,
            shell=True
        )

        if result.returncode != 0:
            print(f"Error calling Claude: {result.stderr}")
            print(f"Command output: {result.stdout}")
            raise Exception(f"Claude call failed: {result.stderr}")

        try:
            response = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            print(f"Failed to parse Claude response as JSON: {e}")
            print(f"Raw stdout (first 500 chars): {result.stdout[:500]}")
            raise Exception(f"Invalid JSON from Claude: {e}")

        # When using --json-schema, the output is in structured_output
        if "structured_output" in response:
            return response["structured_output"]
        else:
            raise Exception("Unexpected response format from Claude")

    def _filter_files(self, repo_state: dict, patterns: list) -> dict:
        """Filter files by pattern (e.g., only *.py)"""
        filtered = {}
        for path, content in repo_state.items():
            if any(fnmatch.fnmatch(path, p) for p in patterns):
                filtered[path] = content
        return filtered

    def _get_specific_files(self, repo_state: dict, file_paths: list) -> dict:
        """Get only specific files, nothing more"""
        return {
            path: repo_state[path]
            for path in file_paths
            if path in repo_state
        }

    def _format_files(self, files: dict) -> str:
        """Format files dict into readable text"""
        result = ""
        for path, content in files.items():
            result += f"\n--- {path} ---\n{content}\n"
        return result
