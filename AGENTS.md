# Multi-Agent Architecture Documentation

## Overview

This autonomous agent system uses a multi-agent architecture with strict role separation. There are two main pipelines:

1. **Bug Fix Pipeline**: Automatically fixes failing tests
2. **Feature Development Pipeline**: Develops new features from requirements

## Architecture Principles

### Role Isolation

Each agent has ONE job and receives ONLY the information it needs:

- **Planner**: Gets test failures + code (NO git/CI data)
- **Coder**: Gets plan + files (NO test output)
- **Tester**: Gets modified code + existing tests (NO implementation access)
- **Reviewer**: Gets files + test output (NO commit authority)
- **DevOps**: Handles state changes (NO code decisions)

### Agent Contracts

All agents communicate through well-defined JSON contracts (see `contracts.py`):

- Input contracts specify what data each agent receives
- Output contracts specify what data each agent produces
- JSON schemas enforce structure validation

### Quality Gates

- **Reviewer Agent**: Acts as quality gate before any commit
- **Reflection Layer**: Prevents infinite loops and repetitive strategies
- **Safety Mechanisms**: Runaway loop protection, max iterations

---

## Bug Fix Pipeline

**When to use**: You have failing tests that need to be fixed automatically.

**Pipeline Flow**:
```
Controller → Planner → Coder → [Tester] → Reviewer → DevOps
```

### Agents

#### 1. Planner Agent (`prompts/planner.md`)
- **Input**: Test failures, current code, previous attempt context
- **Output**: Analysis, files to modify, repair strategy
- **Responsibilities**: Analyze failures, create repair strategy, learn from previous attempts
- **Does NOT**: Write code, see git history

#### 2. Coder Agent (`prompts/coder.md`)
- **Input**: Repair plan, files to modify
- **Output**: Modified files, commit message
- **Responsibilities**: Implement the plan exactly as specified
- **Does NOT**: See test output, make strategic decisions

#### 3. Tester Agent (`prompts/tester.md`)
- **Input**: Modified code, existing tests, coverage gaps
- **Output**: New/updated test files
- **Responsibilities**: Write comprehensive test cases
- **Does NOT**: Modify implementation code
- **When Called**: Only when Planner sets `needs_new_tests` flag

#### 4. Reviewer Agent (`prompts/reviewer.md`)
- **Input**: Original files, modified files, test output
- **Output**: Approval status, issues, feedback
- **Responsibilities**: Review changes, approve or reject
- **Does NOT**: Modify files, has no commit authority

#### 5. DevOps Agent (`devops_agent.py`)
- **Input**: Approved changes
- **Output**: Git commits, PR updates, CI status
- **Responsibilities**: Git operations, CI/PR management
- **Does NOT**: Make code decisions

### Running the Bug Fix Pipeline

```bash
# Local mode (creates new branch and PR)
python controller.py

# CI mode (runs automatically on PR)
# Triggered by GitHub Actions workflow
```

### Configuration

- **MAX_ITERS**: Maximum iterations before stopping (default: 10)
- **MAX_REVIEWER_RETRIES**: Max times reviewer can reject (default: 3)
- **Runaway Protection**: Stops after 7 agent commits

### Reflection Layer

The Planner receives context from previous failed attempts:

- **previous_attempt_failed**: Boolean flag
- **failure_reason**: Why the previous attempt failed
- **should_strategy_change**: Planner decides if approach needs changing

This prevents the agent from repeating the same failed strategy.

---

## Feature Development Pipeline

**When to use**: You want to develop a new feature from requirements.

**Pipeline Flow**:
```
RequirementsGather → AcceptanceCriteria → ArchitectPlanner →
TechnicalPlanner → Coder → Tester → Reviewer → DevOps
```

### Agents

#### 1. RequirementsGather Agent (`prompts/requirements_gather.md`)
- **Input**: Raw requirements (Gherkin or free form), previous Q&A
- **Output**: Well-formed Gherkin scenarios, clarification questions
- **Responsibilities**:
  - Transform raw requirements into Gherkin
  - Ask clarifying questions for ambiguities
  - Iterate until requirements are clear
- **Does NOT**: Design or implement

**Example Interaction**:
```
User: "Add user login"

Agent: "I need clarification on the following:

Q: What should happen if a user enters incorrect password?
   Context: Need to define error handling behavior
   Suggested answers:
   1. Show error message and allow retry
   2. Lock account after 3 failed attempts
   3. Both: show error and lock after multiple failures

Your answer?"
```

#### 2. AcceptanceCriteria Agent (`prompts/acceptance_criteria.md`)
- **Input**: Gherkin scenarios, requirements summary
- **Output**: Acceptance criteria, definition of done, risk areas
- **Responsibilities**:
  - Create SMART acceptance criteria
  - Define what "done" means
  - Identify potential risks
- **Does NOT**: Design or implement

**Output Structure**:
```json
{
  "acceptance_criteria": [
    {
      "criterion": "User can log in with valid credentials",
      "rationale": "Core functionality",
      "test_type": "e2e"
    }
  ],
  "definition_of_done": [
    "All acceptance criteria met and tested",
    "Code reviewed and approved"
  ],
  "risk_areas": [
    "Session management and token expiration",
    "Password security"
  ]
}
```

#### 3. ArchitectPlanner Agent (`prompts/architect_planner.md`)
- **Input**: Gherkin scenarios, acceptance criteria, existing codebase
- **Output**: Technical design, design decisions, files to create/modify
- **Responsibilities**:
  - Design technical architecture
  - Make explicit design decisions with rationale
  - Identify files and dependencies needed
  - Create design diagrams (ASCII)
- **Does NOT**: Write code

**Design Decisions Structure**:
```json
{
  "aspect": "Authentication Method",
  "decision": "Use JWT tokens",
  "rationale": "Enables stateless authentication",
  "alternatives_considered": [
    "Session-based auth",
    "OAuth 2.0"
  ]
}
```

#### 4. TechnicalPlanner Agent (`prompts/technical_planner.md`)
- **Input**: Technical design, design decisions, files to create/modify
- **Output**: Implementation plan with ordered steps
- **Responsibilities**:
  - Break design into implementation steps
  - Order steps by dependencies
  - Estimate complexity
  - Plan test strategy
- **Does NOT**: Write code

**Implementation Steps**:
```json
{
  "step_number": 1,
  "description": "Add password_hash field to User model",
  "files_affected": ["src/models/user.py"],
  "dependencies": [],
  "estimated_complexity": "low"
}
```

#### 5-8. Coder, Tester, Reviewer, DevOps
Same as Bug Fix Pipeline (agents are reused)

### Running the Feature Development Pipeline

```bash
python feature_controller.py
```

**Interactive Process**:

1. Enter requirements (Gherkin or free form)
2. Review generated Gherkin scenarios
3. Answer clarification questions (if any)
4. Review and approve acceptance criteria
5. Review and approve technical design
6. Review and approve implementation plan
7. Agent implements feature
8. Review final code
9. Approve to commit and create PR

**User Approval Gates**:
- After Gherkin scenarios are finalized
- After acceptance criteria
- After technical design
- After implementation plan
- Before applying changes

---

## File Structure

```
├── controller.py                    # Bug fix pipeline orchestrator
├── feature_controller.py            # Feature development orchestrator
├── agent_caller.py                  # Unified agent calling interface
├── devops_agent.py                  # DevOps operations (git, CI, PR)
├── contracts.py                     # Agent contracts and JSON schemas
│
├── prompts/
│   ├── planner.md                   # Bug fix planner
│   ├── coder.md                     # Implementation agent
│   ├── tester.md                    # Test writing agent
│   ├── reviewer.md                  # Code review agent
│   ├── requirements_gather.md       # Requirements gathering
│   ├── acceptance_criteria.md       # Acceptance criteria creation
│   ├── architect_planner.md         # Architecture design
│   └── technical_planner.md         # Implementation planning
│
└── [deprecated]
    ├── git_tools.py                 # Moved to devops_agent.py
    ├── ci_tools.py                  # Moved to devops_agent.py
    └── prompt.md                    # Replaced by agent-specific prompts
```

---

## Agent Communication

### Information Flow (Bug Fix)

```
1. Test Failure
   ↓
2. Planner (sees: tests, code)
   ↓ plan
3. Coder (sees: plan, files)
   ↓ changes
4. Tester (sees: changes, existing tests) [if needed]
   ↓ test files
5. Reviewer (sees: original, modified, test output)
   ↓ approval/rejection
6. DevOps (sees: approved changes)
   ↓ commit, push, PR
7. CI runs tests
   ↓ success/failure
8. Repeat if failed (with reflection)
```

### Information Flow (Feature Development)

```
1. User Requirements
   ↓
2. RequirementsGather
   ↓ Gherkin scenarios
3. AcceptanceCriteria
   ↓ acceptance criteria
4. ArchitectPlanner
   ↓ technical design
5. TechnicalPlanner
   ↓ implementation plan
6. Coder
   ↓ code changes
7. Tester
   ↓ test files
8. Reviewer
   ↓ approval
9. DevOps
   ↓ commit, PR
```

---

## Safety Mechanisms

### Runaway Loop Protection

Prevents infinite agent loops:
- Checks recent commit history
- Stops if 7+ agent commits detected
- Requires manual intervention

### Max Iterations

Bug fix pipeline stops after 10 iterations to prevent:
- Excessive API costs
- Infinite debugging loops

### Strategy Repetition Detection

Detects if the same strategy is tried 3+ times:
- Compares recent strategies
- Stops if no progress is being made

### Reviewer Quality Gate

All code must pass reviewer approval:
- Checks correctness
- Verifies adherence to plan
- Identifies bugs and issues
- Provides actionable feedback

---

## Extending the System

### Adding a New Agent

1. **Define Contract** (`contracts.py`):
```python
class NewAgentInput(TypedDict):
    # Input fields

class NewAgentOutput(TypedDict):
    # Output fields

NEW_AGENT_SCHEMA = {
    # JSON schema
}
```

2. **Create Prompt** (`prompts/new_agent.md`):
```markdown
You are the [Name] Agent.

Your role: [Description]

Rules:
- [Rule 1]
- Output ONLY valid JSON

Output format:
{
  "field": "value"
}
```

3. **Add to AgentCaller** (`agent_caller.py`):
```python
def call_new_agent(self, input_data) -> NewAgentOutput:
    prompt = self._build_new_agent_prompt(input_data)
    return self._call_claude(prompt, NEW_AGENT_SCHEMA)

def _build_new_agent_prompt(self, input_data) -> str:
    # Build prompt from template
```

4. **Integrate into Pipeline**:
- Update controller to call new agent
- Connect to other agents
- Add approval gates if needed

---

## Best Practices

### For Bug Fixes

- Let the Planner analyze failures thoroughly
- Trust the Reviewer - rejections prevent bad commits
- Review the reflection layer if stuck in loops
- Check for strategy repetition

### For Feature Development

- Provide clear, detailed requirements
- Answer clarification questions thoughtfully
- Review each stage before proceeding
- Consider the acceptance criteria carefully

### For Both

- Monitor agent outputs for quality
- Check reviewer feedback when rejected
- Review final changes before commit
- Use appropriate agent for the task

---

## Troubleshooting

### Agent Stuck in Loop

**Problem**: Same strategy repeated 3+ times

**Solution**:
- Check reflection layer logs
- Review reviewer feedback
- Consider manual intervention
- Simplify the problem

### Reviewer Always Rejects

**Problem**: Code keeps getting rejected

**Solution**:
- Review rejection reasons carefully
- Check if plan is clear enough
- Verify acceptance criteria
- Consider if problem is too complex

### Questions Never Satisfied

**Problem**: RequirementsGather keeps asking questions

**Solution**:
- Provide more detailed requirements
- Answer questions completely
- Use Gherkin format from the start

### Tests Still Failing After Max Iterations

**Problem**: Reached MAX_ITERS without fix

**Solution**:
- Review iteration history
- Check if problem is within agent capabilities
- Consider manual debugging
- Simplify test cases

---

## Performance Considerations

### API Costs

- Bug fix: 3-4 Claude calls per iteration
- Feature dev: 4-8 Claude calls total
- Use haiku model for Reviewer (cheaper)

### Iteration Time

- Bug fix iteration: ~2-5 minutes
- Feature dev pipeline: ~5-10 minutes total
- CI wait time: 30 seconds between checks

### Token Usage

- Planner: High (sees all code + tests)
- Coder: Medium (sees plan + files)
- Reviewer: Medium (sees files + tests)
- Others: Low to Medium

---

## Future Enhancements

- [ ] Parallel agent execution where possible
- [ ] Agent performance metrics and logging
- [ ] User preference learning
- [ ] Incremental feature implementation
- [ ] Integration with more CI/CD platforms
- [ ] Agent fine-tuning based on success rates
- [ ] Cost optimization strategies
