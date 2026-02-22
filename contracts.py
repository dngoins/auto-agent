"""
Agent Contracts - Define JSON schemas and TypedDict contracts for each agent.

This module defines the input/output contracts for each specialized agent,
ensuring clean separation of concerns and type safety.

Agent Categories:
1. Bug Fix Pipeline: Planner → Coder → Tester → Reviewer
2. Feature Development Pipeline: RequirementsGather → AcceptanceCriteria →
   ArchitectPlanner → TechnicalPlanner → Coder → Tester → Reviewer
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


# ============================================================================
# FEATURE DEVELOPMENT PIPELINE CONTRACTS
# ============================================================================


# RequirementsGather Agent Contract
# ==================================

class ClarificationQuestion(TypedDict):
    """A clarification question about requirements"""
    question: str
    context: str  # Why this question is being asked
    suggested_answers: List[str]  # Optional suggested answers


class RequirementsGatherInput(TypedDict):
    """Input data for the RequirementsGather agent"""
    raw_requirements: str  # User's initial requirements (Gherkin or free form)
    previous_questions: Optional[List[dict]]  # Previous Q&A if iterating
    user_answers: Optional[List[str]]  # Answers to previous questions


class RequirementsGatherOutput(TypedDict):
    """Output from the RequirementsGather agent"""
    gherkin_scenarios: List[str]  # Well-formed Gherkin scenarios
    needs_clarification: bool  # True if more questions needed
    clarification_questions: List[ClarificationQuestion]  # Questions to ask
    requirements_summary: str  # High-level summary


# AcceptanceCriteria Agent Contract
# ==================================

class AcceptanceCriterion(TypedDict):
    """A single acceptance criterion"""
    criterion: str
    rationale: str  # Why this criterion matters
    test_type: str  # "unit", "integration", "e2e", "manual"


class AcceptanceCriteriaInput(TypedDict):
    """Input data for the AcceptanceCriteria agent"""
    gherkin_scenarios: List[str]  # From RequirementsGather
    requirements_summary: str


class AcceptanceCriteriaOutput(TypedDict):
    """Output from the AcceptanceCriteria agent"""
    acceptance_criteria: List[AcceptanceCriterion]
    definition_of_done: List[str]  # High-level completion checklist
    risk_areas: List[str]  # Potential risk areas to watch


# ArchitectPlanner Agent Contract
# ================================

class TechnicalDecision(TypedDict):
    """A technical design decision"""
    aspect: str  # e.g., "Data Model", "API Design", "Architecture Pattern"
    decision: str  # The chosen approach
    rationale: str  # Why this approach
    alternatives_considered: List[str]  # Other options evaluated


class ArchitectPlannerInput(TypedDict):
    """Input data for the ArchitectPlanner agent"""
    gherkin_scenarios: List[str]
    acceptance_criteria: List[AcceptanceCriterion]
    repository_files: dict  # Existing codebase context


class ArchitectPlannerOutput(TypedDict):
    """Output from the ArchitectPlanner agent"""
    technical_design: str  # Overall design description
    design_decisions: List[TechnicalDecision]
    files_to_create: List[str]  # New files needed
    files_to_modify: List[str]  # Existing files to modify
    dependencies_needed: List[str]  # External packages/libraries
    design_diagrams: Optional[str]  # ASCII diagrams if helpful


# TechnicalPlanner Agent Contract
# ================================

class ImplementationStep(TypedDict):
    """A single implementation step"""
    step_number: int
    description: str
    files_affected: List[str]
    dependencies: List[int]  # Step numbers this depends on
    estimated_complexity: str  # "low", "medium", "high"


class TechnicalPlannerInput(TypedDict):
    """Input data for the TechnicalPlanner agent"""
    technical_design: str
    design_decisions: List[TechnicalDecision]
    files_to_create: List[str]
    files_to_modify: List[str]
    repository_files: dict  # Current codebase


class TechnicalPlannerOutput(TypedDict):
    """Output from the TechnicalPlanner agent"""
    implementation_plan: str  # Overall plan description
    implementation_steps: List[ImplementationStep]
    files_to_modify: List[str]  # For Coder agent
    strategy: str  # Implementation strategy
    needs_new_tests: bool  # Flag for Tester agent
    test_strategy: str  # What tests should be written


# JSON Schemas for Feature Development Agents
# ============================================

REQUIREMENTS_GATHER_SCHEMA = {
    "type": "object",
    "properties": {
        "gherkin_scenarios": {
            "type": "array",
            "items": {"type": "string"}
        },
        "needs_clarification": {"type": "boolean"},
        "clarification_questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "context": {"type": "string"},
                    "suggested_answers": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["question", "context", "suggested_answers"]
            }
        },
        "requirements_summary": {"type": "string"}
    },
    "required": ["gherkin_scenarios", "needs_clarification", "clarification_questions", "requirements_summary"]
}

ACCEPTANCE_CRITERIA_SCHEMA = {
    "type": "object",
    "properties": {
        "acceptance_criteria": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "criterion": {"type": "string"},
                    "rationale": {"type": "string"},
                    "test_type": {"type": "string"}
                },
                "required": ["criterion", "rationale", "test_type"]
            }
        },
        "definition_of_done": {
            "type": "array",
            "items": {"type": "string"}
        },
        "risk_areas": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["acceptance_criteria", "definition_of_done", "risk_areas"]
}

ARCHITECT_PLANNER_SCHEMA = {
    "type": "object",
    "properties": {
        "technical_design": {"type": "string"},
        "design_decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "aspect": {"type": "string"},
                    "decision": {"type": "string"},
                    "rationale": {"type": "string"},
                    "alternatives_considered": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["aspect", "decision", "rationale", "alternatives_considered"]
            }
        },
        "files_to_create": {
            "type": "array",
            "items": {"type": "string"}
        },
        "files_to_modify": {
            "type": "array",
            "items": {"type": "string"}
        },
        "dependencies_needed": {
            "type": "array",
            "items": {"type": "string"}
        },
        "design_diagrams": {"type": "string"}
    },
    "required": ["technical_design", "design_decisions", "files_to_create", "files_to_modify", "dependencies_needed"]
}

TECHNICAL_PLANNER_SCHEMA = {
    "type": "object",
    "properties": {
        "implementation_plan": {"type": "string"},
        "implementation_steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "step_number": {"type": "integer"},
                    "description": {"type": "string"},
                    "files_affected": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "dependencies": {
                        "type": "array",
                        "items": {"type": "integer"}
                    },
                    "estimated_complexity": {"type": "string"}
                },
                "required": ["step_number", "description", "files_affected", "dependencies", "estimated_complexity"]
            }
        },
        "files_to_modify": {
            "type": "array",
            "items": {"type": "string"}
        },
        "strategy": {"type": "string"},
        "needs_new_tests": {"type": "boolean"},
        "test_strategy": {"type": "string"}
    },
    "required": ["implementation_plan", "implementation_steps", "files_to_modify", "strategy", "needs_new_tests", "test_strategy"]
}
