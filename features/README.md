# Feature Requirements Directory

This directory contains feature requirements in Gherkin format. Pushing `.gherkin` files here triggers automatic feature development!

## 🚀 Quick Start

1. **Copy a template:**
   - `QUICKSTART.gherkin` - Simple, minimal template
   - `TEMPLATE.gherkin` - Comprehensive with examples and best practices

2. **Fill in your feature idea**

3. **Choose how to run it:**

### Option A: Push to GitHub (Automatic)
```bash
# Copy and fill in a template
cp features/QUICKSTART.gherkin features/my-feature.gherkin
# Edit features/my-feature.gherkin with your idea

# Create feature branch and push
git checkout -b feature/my-feature
git add features/my-feature.gherkin
git commit -m "Add my feature requirements"
git push origin feature/my-feature

# ✨ Workflow triggers automatically!
# Check the Actions tab to see progress
```

### Option B: Local Testing (Recommended First)
```bash
# Test locally before pushing
python feature_controller.py --requirements-file features/my-feature.gherkin --auto-approve

# This runs the full pipeline locally:
# - Shows you what will be generated
# - Creates a branch and PR
# - No CI needed
```

### Option C: GitHub Issue
```bash
# Copy the content of your .gherkin file
cat features/my-feature.gherkin

# Create a new issue:
# 1. Go to Issues → New Issue
# 2. Paste the Gherkin content
# 3. Add label: auto-implement
# 4. Create issue
#
# ✨ Pipeline runs automatically!
```

### Option D: Manual Workflow
```
1. Go to Actions tab
2. Click "Feature Development Agent"
3. Click "Run workflow"
4. Paste your .gherkin file content
5. Click "Run workflow"
```

## 📝 Template Guide

### QUICKSTART.gherkin
Best for:
- Simple features
- Quick ideas
- First-time users
- Minimal boilerplate

### TEMPLATE.gherkin
Best for:
- Complex features
- Multiple scenarios
- Edge cases and errors
- Learning Gherkin syntax

## 📋 File Naming

Use descriptive names:
- ✅ `user-authentication.gherkin`
- ✅ `data-export.gherkin`
- ✅ `search-functionality.gherkin`
- ❌ `feature.gherkin`
- ❌ `test.gherkin`

## 🎯 What Happens When You Push

1. **Workflow Triggers** (< 1 min)
   - GitHub detects `.gherkin` file push
   - `feature-development.yml` workflow starts

2. **Requirements Processing** (1-2 min)
   - RequirementsGather reads your file
   - Clarifies requirements (auto-answers if needed)
   - Creates structured Gherkin scenarios

3. **Planning** (2-3 min)
   - AcceptanceCriteria defines what "done" means
   - ArchitectPlanner designs the technical solution
   - TechnicalPlanner creates implementation steps

4. **Implementation** (3-5 min)
   - Coder writes the code
   - Tester writes test cases
   - Reviewer checks quality

5. **PR Creation** (< 1 min)
   - Code pushed to your branch
   - PR created with detailed description
   - Link back to your requirements file

## 💡 Tips for Great Requirements

**Be Specific:**
```gherkin
# ❌ Vague
When the user clicks the button
Then something happens

# ✅ Specific
When the user clicks the "Submit" button
Then a success message "Form submitted!" should be displayed
And the form should be cleared
```

**Include Edge Cases:**
```gherkin
Scenario: Successful case
  Given valid input
  When action happens
  Then success

Scenario: Error case
  Given invalid input
  When action happens
  Then error message shown
```

**Write from User Perspective:**
```gherkin
# ❌ Implementation-focused
Given the database has a User record
When the authentication service validates credentials
Then a JWT token is generated

# ✅ User-focused
Given I am a registered user
When I log in with my email and password
Then I should see my dashboard
```

## 🔍 Examples

See the templates for complete examples, or check existing `.gherkin` files in this directory for real examples.

## 🐛 Troubleshooting

**Workflow doesn't trigger:**
- Make sure you're on a feature branch (not main/master)
- Verify file extension is `.gherkin`
- File must be in `features/` or `requirements/` directory
- Check Actions tab for any errors

**Pipeline fails:**
- Check Actions logs for specific error
- Verify `ANTHROPIC_API_KEY` is set in repository secrets
- Review your Gherkin syntax
- Try running locally first

**Want to stop a running workflow:**
- Go to Actions tab
- Click on the running workflow
- Click "Cancel workflow"

## 📚 Learn More

- [Full documentation](../AGENTS.md) - Complete guide to all features
- [Gherkin syntax](https://cucumber.io/docs/gherkin/reference/) - Official Gherkin reference
- [GitHub Actions logs](../../actions) - See workflow runs

## 🎓 Tutorial: Your First Feature

1. **Start simple:**
   ```bash
   cat > features/hello-world.gherkin <<EOF
   Feature: Hello World
     As a developer
     I want to create a hello world function
     So that I can test the pipeline

     Scenario: Say hello
       Given the application is running
       When I call the hello function with name "World"
       Then I should receive "Hello, World!"
   EOF
   ```

2. **Test locally first:**
   ```bash
   python feature_controller.py --requirements-file features/hello-world.gherkin --auto-approve
   ```

3. **Push to GitHub:**
   ```bash
   git checkout -b feature/hello-world
   git add features/hello-world.gherkin
   git commit -m "Add hello world feature"
   git push origin feature/hello-world
   ```

4. **Watch the magic:**
   - Go to Actions tab
   - Watch the workflow run
   - Check the created PR
   - Review the generated code

5. **Iterate:**
   - If not perfect, update the `.gherkin` file
   - Push again - workflow reruns
   - Review, refine, repeat

Happy feature building! 🚀
