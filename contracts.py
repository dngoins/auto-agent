"""
Agent Contracts - Define JSON schemas and TypedDict contracts for each agent.

This module defines the input/output contracts for each specialized agent,
ensuring clean separation of concerns and type safety.
"""

from typing import TypedDict, List, Optional, Literal


# Planner Agent Contract
# ======================

class PlannerInput(TypedDict):
    """Input data for the Planner agent"""
    test_output: str
    ci_logs: str
    repository_files: dict  # {path: content}
    # Reflection layer fields
    previous_attempt_failed: bool
    failure_reason: Optional[str]


class PlannerOutput(TypedDict):
    """Output from the Planner agent"""
    analysis: str
    files_to_modify: List[str]
    strategy: str
    needs_new_tests: bool  # Flag for Tester agent
    coverage_gaps: List[str]  # What needs testing
    # Reflection decision
    should_strategy_change: bool


# Coder Agent Contract
# ====================

class FileChange(TypedDict):
    """Represents a file modification"""
    path: str
    content: str


class CoderInput(TypedDict):
    """Input data for the Coder agent"""
    repair_plan: PlannerOutput
    repository_files: dict  # {path: content}


class CoderOutput(TypedDict):
    """Output from the Coder agent"""
    files: List[FileChange]
    commit_message: str


# Tester Agent Contract
# =====================

class TesterInput(TypedDict):
    """Input data for the Tester agent"""
    modified_code: List[FileChange]
    existing_tests: dict  # {path: content}
    coverage_gaps: List[str]  # What needs testing


class TesterOutput(TypedDict):
    """Output from the Tester agent"""
    files: List[FileChange]  # New/updated test files
    test_strategy: str  # What tests were added


# Reviewer Agent Contract
# =======================

class ReviewIssue(TypedDict):
    """Represents a code review issue"""
    file: str
    line: int
    issue: str


class ReviewerInput(TypedDict):
    """Input data for the Reviewer agent"""
    original_files: dict  # {path: content}
    modified_files: List[FileChange]
    test_output: str


class ReviewerOutput(TypedDict):
    """Output from the Reviewer agent"""
    approved: bool
    issues: List[ReviewIssue]
    feedback: str


# JSON Schemas for Claude API
# ============================

PLANNER_SCHEMA = {
    "type": "object",
    "properties": {
        "analysis": {"type": "string"},
        "files_to_modify": {
            "type": "array",
            "items": {"type": "string"}
        },
        "strategy": {"type": "string"},
        "needs_new_tests": {"type": "boolean"},
        "coverage_gaps": {
            "type": "array",
            "items": {"type": "string"}
        },
        "should_strategy_change": {"type": "boolean"}
    },
    "required": ["analysis", "files_to_modify", "strategy", "needs_new_tests", "coverage_gaps", "should_strategy_change"]
}

CODER_SCHEMA = {
    "type": "object",
    "properties": {
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        },
        "commit_message": {"type": "string"}
    },
    "required": ["files", "commit_message"]
}

TESTER_SCHEMA = {
    "type": "object",
    "properties": {
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        },
        "test_strategy": {"type": "string"}
    },
    "required": ["files", "test_strategy"]
}

REVIEWER_SCHEMA = {
    "type": "object",
    "properties": {
        "approved": {"type": "boolean"},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file": {"type": "string"},
                    "line": {"type": "integer"},
                    "issue": {"type": "string"}
                },
                "required": ["file", "line", "issue"]
            }
        },
        "feedback": {"type": "string"}
    },
    "required": ["approved", "issues", "feedback"]
}
