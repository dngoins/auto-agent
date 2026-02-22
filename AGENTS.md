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

## GitHub Actions Integration

The feature development pipeline can be triggered automatically via GitHub Actions in four ways:

### Automatic Trigger Methods

#### 1. Requirements File Push

Push a `.gherkin` file to trigger automatic development:

```bash
# Create features directory
mkdir -p features

# Create requirements file
cat > features/user-auth.gherkin <<EOF
Feature: User Authentication
  As a user
  I want to log in securely
  So that I can access my account

Scenario: Successful login
  Given a user exists with email "user@example.com"
  When the user logs in with correct credentials
  Then the user should be redirected to the dashboard
EOF

# Commit and push (must be on feature branch, not main)
git checkout -b feature/user-auth
git add features/user-auth.gherkin
git commit -m "Add user authentication feature requirements"
git push origin feature/user-auth
```

**What happens:**
1. GitHub triggers `feature-development.yml` workflow
2. Requirements extracted from `.gherkin` file
3. Pipeline runs automatically in CI mode
4. Implementation pushed to the same branch
5. PR can be created manually or automatically

**File locations:**
- `features/*.gherkin` - Recommended for features
- `requirements/*.gherkin` - Alternative location

**Note:** Pushes to `main` or `master` branches are ignored to prevent accidental triggers.

#### 2. GitHub Issue

Create an issue with the `auto-implement` label:

**Steps:**
1. Go to Issues tab
2. Click "New issue"
3. Enter title: `Add password reset functionality`
4. Write requirements in body (Gherkin or free form):
   ```
   Feature: Password Reset
     As a user
     I want to reset my forgotten password
     So that I can regain access to my account

   Scenario: Request password reset
     Given I forgot my password
     When I click "Forgot Password"
     Then I should receive a reset email
   ```
5. Add label: `auto-implement`

**What happens:**
1. GitHub triggers `feature-development.yml` workflow
2. `extract_requirements.py` reads issue body
3. `feature_controller.py` runs in CI mode with auto-approve
4. RequirementsGather processes requirements
5. Clarification questions auto-answered with first suggestion
6. Pipeline creates implementation
7. New PR is created with the implementation
8. Comment posted to issue with PR link

#### 3. Pull Request

Create or update a PR with `auto-implement` label or `[AUTO-IMPLEMENT]` in title:

**Option A: Using Label**
```bash
# Create PR first
gh pr create --title "Add user preferences" \
  --body "Feature: User Preferences\n\nUsers should be able to customize their settings"

# Add label
gh pr edit --add-label "auto-implement"
```

**Option B: Using Title Pattern**
```bash
# Create PR with special title
gh pr create --title "[AUTO-IMPLEMENT] Add user preferences" \
  --body "Feature: User Preferences\n\nUsers should be able to customize their settings"
```

**What happens:**
1. PR creation/update triggers workflow (label or title pattern match)
2. Requirements extracted from PR description
3. Pipeline runs and generates code
4. Code pushed to the PR branch
5. PR updated with implementation details
6. Comment added with completion status

#### 4. Manual Workflow Dispatch

Trigger via GitHub Actions UI with custom requirements:

**Steps:**
1. Go to Actions tab in repository
2. Select "Feature Development Agent" workflow
3. Click "Run workflow" button
4. Select branch
5. Enter requirements in text box
6. Choose auto-approve setting
7. Click "Run workflow"

**Parameters:**
- **requirements** (required): Feature requirements (Gherkin or free form)
- **auto_approve** (optional, default: true): Skip approval gates

**What happens:**
1. Workflow starts with provided input
2. Requirements used directly from input parameter
3. Pipeline runs with specified settings
4. Implementation pushed to selected branch
5. PR can be created if needed

### CI Mode Behavior

When running in CI mode (`--ci-mode --auto-approve`):

**Requirements Input:**
- From environment variable `REQUIREMENTS_TEXT`
- Set by `extract_requirements.py` script
- No interactive input required

**Clarification Questions:**
- Automatically answered with first suggested answer
- Logged to workflow output for visibility
- Example:
  ```
  [CI MODE] Auto-answering 2 clarification questions
  Q: What should happen if a user enters an incorrect password?
  A: Show error message and allow retry
  ```

**Approval Gates:**
- All stages auto-approved
- Reviewer agent still runs as quality gate
- Will fail workflow if Reviewer rejects
- No user input required

**Output:**
- Detailed logs for each agent
- Gherkin scenarios saved to `requirements.gherkin`
- Acceptance criteria logged
- Design decisions logged
- PR created with comprehensive description

**Git Operations:**
- Uses "feature-agent-bot" as commit author
- Force pushes to update existing branches
- Creates new branch if in local mode
- Updates existing PR or creates new one

### Environment Variables

**Required Secrets:**

Set in repository Settings → Secrets and variables → Actions:

- **`ANTHROPIC_API_KEY`** (required): Your Anthropic API key for Claude
  - Get from: https://console.anthropic.com/
  - Used to call Claude API for all agents

- **`GITHUB_TOKEN`** (automatic): Automatically provided by GitHub Actions
  - No manual setup required
  - Used for git operations, PR creation, commenting

**Workflow Environment:**

Set automatically by the workflow:

- `REQUIREMENTS_SOURCE`: Where requirements came from (issue/pr/file/manual)
- `REQUIREMENTS_TEXT`: The actual requirements text
- `REQUIREMENTS_TITLE`: Title/name of the feature
- `CI`: `'true'` to indicate CI environment
- `GITHUB_ACTIONS`: `'true'` to indicate GitHub Actions
- `GH_TOKEN`: Copy of `GITHUB_TOKEN` for gh CLI

### Safety Mechanisms

All existing safety mechanisms apply to CI mode:

**Max Iterations:**
- Default: 10 iterations maximum
- Prevents infinite loops
- Each iteration logged separately

**Runaway Loop Protection:**
- Checks for 7+ consecutive agent commits
- Stops workflow if detected
- Requires manual intervention

**Strategy Repetition Detection:**
- Detects if same strategy tried 3+ times
- Stops to prevent wasteful iterations
- Logs strategy changes

**Reviewer Quality Gate:**
- All code must pass Reviewer approval
- Will fail workflow if Reviewer rejects
- Provides detailed feedback in logs
- Manual review still recommended before merge

**Cost Controls:**
- Workflow timeout: 360 minutes (can be reduced)
- Only runs on specific triggers
- Requires explicit labels or file paths
- Main/master branches excluded from file triggers

### Workflow Permissions

The workflow requires these permissions (set in workflow file):

```yaml
permissions:
  contents: write      # To push code changes
  issues: write        # To comment on issues
  pull-requests: write # To create and comment on PRs
```

**What each permission allows:**
- **contents:write** - Push commits to branches, create branches
- **issues:write** - Post comments on issues, add labels
- **pull-requests:write** - Create PRs, post comments, edit PR descriptions

### Debugging Workflows

**View Workflow Runs:**
1. Go to Actions tab
2. Click on workflow run
3. Click on job to see steps
4. Expand each step to see logs

**Common Issues:**

**Workflow not triggering:**
- Check if event type matches (`push`, `issues`, `pull_request`, `workflow_dispatch`)
- Verify label name is exactly `auto-implement`
- For files, ensure path matches `features/*.gherkin` or `requirements/*.gherkin`
- Check branch is not `main` or `master` for file triggers

**Requirements extraction fails:**
- Check workflow logs for `extract_requirements.py` step
- Verify GitHub event data is accessible
- Ensure file exists for file-based triggers
- Check issue/PR body is not empty

**Pipeline fails:**
- Check `ANTHROPIC_API_KEY` is set in repository secrets
- Verify API key is valid and has sufficient credits
- Check agent logs for specific errors
- Review Reviewer feedback if code was rejected

**PR creation fails:**
- Verify `GITHUB_TOKEN` has correct permissions
- Check branch doesn't already have a PR
- Ensure git user is configured

### Local vs CI Mode

**Local Mode (interactive):**
```bash
python feature_controller.py
# Prompts for stdin input
# Asks clarification questions
# Requires approval at each stage
# Creates new branch
```

**CI Mode (automated):**
```bash
python feature_controller.py --ci-mode --auto-approve
# Reads from REQUIREMENTS_TEXT environment variable
# Auto-answers clarification questions
# Auto-approves all stages
# Uses existing branch or creates new one
```

**File-based (local):**
```bash
python feature_controller.py --requirements-file features/my-feature.gherkin --auto-approve
# Reads from specified file
# Auto-approves stages
# Creates new branch
```

### Usage Examples

#### Example 1: Issue-Triggered Development

**User creates issue:**
```
Title: Add export functionality
Labels: auto-implement

Body:
Feature: Data Export
  As a user
  I want to export my data to CSV
  So that I can use it in Excel

Scenario: Export to CSV
  Given I have data in my account
  When I click "Export to CSV"
  Then I should download a CSV file with my data
```

**Workflow execution:**
1. Triggers on issue labeled
2. Extracts requirements from issue body
3. Creates branch `agent-<timestamp>`
4. Runs through full pipeline
5. Creates PR with title "Feature: Data Export"
6. Comments on issue: "✅ Feature development pipeline completed. Check PR #123"

#### Example 2: File-Based Development

**Developer workflow:**
```bash
# Create feature branch
git checkout -b feature/notifications

# Write requirements
mkdir -p features
cat > features/notifications.gherkin <<EOF
Feature: Email Notifications
  As a user
  I want to receive email notifications
  So that I stay informed

Scenario: Weekly digest
  Given I am subscribed to weekly digest
  When it is Monday 9am
  Then I should receive an email with weekly updates
EOF

# Commit and push
git add features/notifications.gherkin
git commit -m "Add email notifications requirements"
git push origin feature/notifications
```

**What happens:**
1. Triggers on file push to `features/*.gherkin`
2. Reads requirements from file
3. Runs pipeline on same branch
4. Pushes implementation to `feature/notifications`
5. Developer can create PR manually

#### Example 3: PR Enhancement

**Quick feature request:**
```bash
# Create branch and PR
git checkout -b add-search
gh pr create --title "[AUTO-IMPLEMENT] Add search functionality" \
  --body "Add a search bar that allows users to search through items by name or description"

# Workflow triggers automatically
# Implementation added to branch
# PR updated with code
```

### Best Practices

**For Requirements Files:**
- Use Gherkin format for clarity
- One feature per file
- Name files descriptively: `user-auth.gherkin`, `data-export.gherkin`
- Put in `features/` directory
- Commit to feature branch, not main

**For Issues:**
- Use clear, descriptive titles
- Include user stories in body
- Use Gherkin format if possible
- Add `auto-implement` label only when ready
- One feature per issue

**For PRs:**
- Use `[AUTO-IMPLEMENT]` prefix in title
- Or add `auto-implement` label
- Include detailed requirements in description
- Review generated code before merging
- Test the implementation

**For Manual Triggers:**
- Use for one-off features
- Provide complete requirements
- Enable auto-approve for faster execution
- Review the PR before merging

### Cost Optimization

**API Call Breakdown:**
- RequirementsGather: 1-3 calls (if questions asked)
- AcceptanceCriteria: 1 call
- ArchitectPlanner: 1 call
- TechnicalPlanner: 1 call
- Coder: 1 call
- Tester: 1 call (if needed)
- Reviewer: 1 call
- **Total: 7-9 Claude API calls per feature**

**Tips:**
- Provide complete requirements to avoid clarification loops
- Use Gherkin format to reduce ambiguity
- Test locally first with `--requirements-file` flag
- Monitor API usage in Anthropic console
- Consider using smaller model for simple features

---

## Future Enhancements

- [ ] Parallel agent execution where possible
- [ ] Agent performance metrics and logging
- [ ] User preference learning
- [ ] Incremental feature implementation
- [ ] Integration with more CI/CD platforms
- [ ] Agent fine-tuning based on success rates
- [ ] Cost optimization strategies
- [ ] GitHub App for easier authentication
- [ ] Slack/Discord notifications for workflow completion
- [ ] Dashboard for monitoring agent activity
