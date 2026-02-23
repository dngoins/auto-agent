# Multi-Agent Autonomous Development System

An intelligent agent system that automatically fixes bugs and develops features using Claude AI with strict role separation and quality gates.

## 🎯 What Does This Do?

This system provides **two autonomous pipelines**:

1. **Bug Fix Pipeline** - Automatically fixes failing tests
2. **Feature Development Pipeline** - Develops features from requirements

Both pipelines use a multi-agent architecture where each agent has ONE specific job with strict information boundaries.

## 🚀 Quick Start

### Option 1: Automatic Feature Development with .gherkin Files

**This is the easiest way to develop new features!**

1. **Copy a template:**
   ```bash
   cp features/QUICKSTART.gherkin features/my-feature.gherkin
   ```

2. **Edit `features/my-feature.gherkin` with your feature idea:**
   ```gherkin
   Feature: User Login
     As a user
     I want to log in with email and password
     So that I can access my account

     Scenario: Successful login
       Given I am on the login page
       When I enter valid credentials
       Then I should see my dashboard
   ```

3. **Push to GitHub:**
   ```bash
   git checkout -b feature/my-feature
   git add features/my-feature.gherkin
   git commit -m "Add my feature requirements"
   git push origin feature/my-feature
   ```

4. **✨ Magic happens automatically!**
   - Workflow triggers and processes requirements
   - Creates implementation with tests
   - Opens a PR with the code
   - Takes 5-10 minutes total

**See it in action:** Go to the [Actions tab](../../actions) to watch the workflow run!

### Option 2: Local Feature Development

Test locally before pushing to GitHub:

```bash
# Install dependencies
pip install pytest

# Run the feature development pipeline
python feature_controller.py --requirements-file features/my-feature.gherkin --auto-approve

# This will:
# - Process your requirements
# - Design the architecture
# - Write the code
# - Write tests
# - Create a branch and PR locally
```

### Option 3: GitHub Issue Trigger

1. Create a new issue
2. Write your requirements in the issue body (Gherkin or free form)
3. Add label: `auto-implement`
4. Watch the Actions tab!

### Option 4: Manual Workflow

1. Go to [Actions](../../actions) → "Feature Development Agent"
2. Click "Run workflow"
3. Paste your requirements
4. Click "Run workflow"

## 📁 Repository Structure

```
├── .github/workflows/
│   ├── tests.yml                  # Run tests on push/PR
│   ├── agent.yml                  # Auto-fix failing tests
│   └── feature-development.yml    # Auto-develop features
│
├── features/                      # Put your .gherkin files here!
│   ├── QUICKSTART.gherkin         # Simple template
│   ├── TEMPLATE.gherkin           # Comprehensive template
│   └── README.md                  # Detailed usage guide
│
├── prompts/                       # Agent prompts
│   ├── requirements_gather.md     # Requirements clarification
│   ├── acceptance_criteria.md     # Define "done"
│   ├── architect_planner.md       # Technical design
│   ├── technical_planner.md       # Implementation plan
│   ├── planner.md                 # Bug fix strategy
│   ├── coder.md                   # Code implementation
│   ├── tester.md                  # Test writing
│   └── reviewer.md                # Code review
│
├── scripts/
│   └── extract_requirements.py    # Extract from GitHub events
│
├── controller.py                  # Bug fix orchestrator
├── feature_controller.py          # Feature dev orchestrator
├── agent_caller.py                # Agent interface
├── devops_agent.py                # Git/CI operations
├── contracts.py                   # Agent contracts
└── AGENTS.md                      # Complete documentation

```

## 🏗️ How It Works

### Feature Development Pipeline

```
Your .gherkin file
    ↓
RequirementsGather  → Clarifies requirements, asks questions
    ↓
AcceptanceCriteria  → Defines what "done" means
    ↓
ArchitectPlanner    → Designs technical architecture
    ↓
TechnicalPlanner    → Creates implementation steps
    ↓
Coder               → Writes the code
    ↓
Tester              → Writes test cases
    ↓
Reviewer            → Quality gate (approves/rejects)
    ↓
DevOps              → Creates PR with everything
```

### Bug Fix Pipeline

```
Test Failure
    ↓
Planner    → Analyzes failure, creates repair strategy
    ↓
Coder      → Implements the fix
    ↓
Tester     → Adds missing tests (if needed)
    ↓
Reviewer   → Checks quality (approves/rejects)
    ↓
DevOps     → Commits, pushes, enables auto-merge
    ↓
CI runs tests → If pass, PR auto-merges!
```

## 🎓 Using .gherkin Files (Feature Development)

### What is a .gherkin File?

A `.gherkin` file contains your feature requirements in a structured format that both humans and the AI can understand.

**Example:**
```gherkin
Feature: Search Functionality
  As a user
  I want to search for items by name
  So that I can quickly find what I need

  Scenario: Successful search
    Given I am on the homepage
    And there are items in the database
    When I type "laptop" in the search box
    And I click the search button
    Then I should see a list of laptops
    And the results should be sorted by relevance
```

### Step-by-Step: Creating Your First Feature

#### 1. Choose a Template

```bash
# For simple features:
cp features/QUICKSTART.gherkin features/my-feature.gherkin

# For complex features with multiple scenarios:
cp features/TEMPLATE.gherkin features/my-feature.gherkin
```

#### 2. Write Your Requirements

Edit the file with your feature idea. Use this format:

```gherkin
Feature: [What you're building]
  As a [type of user]
  I want to [do something]
  So that [I get some benefit]

  Scenario: [What happens]
    Given [starting situation]
    When [user takes action]
    Then [expected result]
```

**Tips:**
- Be specific: "When I click the Submit button" not "When I submit"
- Include error cases: "When I enter invalid email, Then I see error message"
- One feature per file
- Multiple scenarios are good!

#### 3. Test Locally (Optional but Recommended)

```bash
# See what will be generated before pushing
python feature_controller.py --requirements-file features/my-feature.gherkin --auto-approve
```

This runs locally and shows you:
- How requirements are interpreted
- The technical design
- Generated code
- Tests

#### 4. Push to GitHub

```bash
# Create a feature branch (NOT main/master)
git checkout -b feature/my-feature

# Add your .gherkin file
git add features/my-feature.gherkin

# Commit
git commit -m "Add my feature requirements"

# Push
git push origin feature/my-feature
```

#### 5. Watch the Magic

- Go to [Actions tab](../../actions)
- You'll see "Feature Development Agent" running
- Click to view detailed logs
- After 5-10 minutes, a PR will be created!

#### 6. Review the PR

The PR will contain:
- ✅ Implementation code
- ✅ Test cases
- ✅ Technical design documentation
- ✅ Gherkin scenarios (refined)
- ✅ Acceptance criteria

Review the code, test it, and merge!

### What Happens Behind the Scenes

When you push a `.gherkin` file:

1. **GitHub triggers the workflow** (< 1 min)
   - Detects `.gherkin` file in `features/` or `requirements/`
   - Starts `feature-development.yml` workflow

2. **Requirements Processing** (1-2 min)
   - `extract_requirements.py` reads your file
   - `RequirementsGather` agent clarifies (auto-answers questions)
   - Generates structured Gherkin scenarios

3. **Planning Phase** (2-3 min)
   - `AcceptanceCriteria` agent defines what "done" means
   - `ArchitectPlanner` agent designs the technical solution
   - `TechnicalPlanner` agent creates step-by-step plan

4. **Implementation** (3-5 min)
   - `Coder` agent writes the code
   - `Tester` agent writes test cases
   - `Reviewer` agent checks quality

5. **PR Creation** (< 1 min)
   - Code pushed to your branch
   - PR created with comprehensive description
   - You get notified

### Troubleshooting

**Workflow doesn't trigger:**
- ✓ Are you on a feature branch? (not main/master)
- ✓ Is the file in `features/` or `requirements/`?
- ✓ Does it end with `.gherkin`?
- ✓ Check [Actions](../../actions) for error messages

**Pipeline fails:**
- Check the workflow logs in Actions tab
- Look for "Extract requirements" step - did it find your file?
- Verify `ANTHROPIC_API_KEY` is set in repository secrets
- Try running locally first to debug

**Generated code not what you expected:**
- Make requirements more specific
- Add more scenarios for edge cases
- Include examples in your Gherkin
- Try again with refined requirements!

## ⚙️ Setup

### Prerequisites

- Python 3.11+
- Node.js (for Claude CLI)
- GitHub repository
- Anthropic API key

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd agent-test

# Install Python dependencies
pip install pytest

# Install Claude CLI
npm install -g @anthropic-ai/claude-code
```

### Configuration

#### For Local Use

Set your API key:
```bash
export ANTHROPIC_API_KEY=your-key-here
```

#### For GitHub Actions

1. Go to repository Settings → Secrets and variables → Actions
2. Add secret: `ANTHROPIC_API_KEY`
3. Value: Your Anthropic API key from https://console.anthropic.com/

That's it! `GITHUB_TOKEN` is provided automatically.

## 📚 Documentation

- **[AGENTS.md](AGENTS.md)** - Complete agent architecture guide
- **[features/README.md](features/README.md)** - .gherkin file usage guide
- **[GitHub Actions Workflows](.github/workflows/)** - Workflow configurations

## 🎯 Examples

### Example 1: Simple Feature

**File:** `features/hello-world.gherkin`
```gherkin
Feature: Hello World Function
  As a developer
  I want a hello world function
  So that I can test the system

  Scenario: Say hello
    Given the application is running
    When I call hello("World")
    Then I should get "Hello, World!"
```

**Result:** Function created, tested, PR opened in ~5 minutes

### Example 2: CRUD Operations

**File:** `features/user-management.gherkin`
```gherkin
Feature: User Management
  As an admin
  I want to manage users
  So that I can control access

  Scenario: Create user
    Given I am logged in as admin
    When I create a user with email "new@example.com"
    Then the user should be saved
    And I should see a success message

  Scenario: Delete user
    Given a user exists with email "old@example.com"
    When I delete the user
    Then the user should be removed
```

**Result:** Complete CRUD implementation with tests

### Example 3: Real-World Feature

See `features/TEMPLATE.gherkin` for a comprehensive authentication example with:
- Multiple scenarios
- Error handling
- Security considerations
- Edge cases

## 🛡️ Safety Features

- **Reviewer Quality Gate**: All code reviewed before commit
- **Max Iterations**: 10 iterations maximum per run
- **Runaway Protection**: Stops after 7 agent commits
- **Strategy Detection**: Detects and stops repetitive strategies
- **Permissions**: Scoped workflow permissions

## 💰 Cost Optimization

**Per Feature Development:**
- 7-9 Claude API calls
- ~$0.50-$2.00 depending on complexity

**Tips to reduce costs:**
- Provide clear, complete requirements upfront
- Use Gherkin format (reduces clarifications)
- Test locally first
- Start with simple features

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Test locally
4. Push and create PR
5. The agents might even review it! 😄

## 📄 License

[Your License]

## 🙋 Support

- **Issues**: Create an issue (or use `auto-implement` label!)
- **Discussions**: Start a discussion
- **Documentation**: Check [AGENTS.md](AGENTS.md)

---

**Ready to build something awesome?**

1. Copy `features/QUICKSTART.gherkin` to `features/my-idea.gherkin`
2. Fill in your feature idea
3. Push to a feature branch
4. Watch it build itself! 🚀
