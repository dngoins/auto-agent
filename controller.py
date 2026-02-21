import subprocess
import json
import time
from pathlib import Path

from git_tools import create_gh_branch, git_commit, git_push
from ci_tools import create_pr, get_pr_status, parse_ci_results, extract_ci_logs, get_latest_run_logs

MAX_ITERS = 10


def run_tests():
    result = subprocess.run(
        ["pytest"],
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout


def collect_files():
    files_data = ""
    for file in Path(".").glob("*.py"):
        if "controller.py" in str(file):
            continue
        files_data += f"\n--- {file} ---\n"
        print(files_data)
        files_data += file.read_text()
    return files_data


def call_claude(prompt):
    schema = json.dumps({
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["continue", "complete"]},
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
        "required": ["status", "files", "commit_message"]
    })

    result = subprocess.run(
        ["claude", "--print", "--output-format", "json", "--json-schema", schema],
        input=prompt,
        text=True,
        capture_output=True,
        shell=True
    )
    if result.returncode != 0:
        print(f"Error calling Claude: {result.stderr}")
        return None
    return result.stdout


def apply_changes(files):
    for file in files:
        Path(file["path"]).write_text(file["content"])


# Create a new branch for this run
print("Creating new branch...")
create_gh_branch()

first_commit_made = False
pr_number = None
ci_logs = None

for iteration in range(MAX_ITERS):
    print(f"\n=== Iteration {iteration + 1} ===")

    # 1. Run local tests
    code, output = run_tests()

    # 2. If fail → ask Claude → apply changes → commit
    if code != 0 or ci_logs:
        print("Tests failed, consulting Claude...")

        files = collect_files()
        template = Path("prompt.md").read_text()

        # Build prompt with local test output and/or CI logs
        if ci_logs:
            test_section = "If CI failed, here are the logs:\n\n" + ci_logs + "\n\nRevise the code to fix these issues."
            prompt = template.replace("{{TEST_OUTPUT}}", "")
            prompt = prompt.replace("{{CI_LOGS}}", test_section)
        else:
            test_section = "The following tests failed:\n\n" + output
            prompt = template.replace("{{TEST_OUTPUT}}", test_section)
            prompt = prompt.replace("{{CI_LOGS}}", "")

        prompt = prompt.replace("{{FILE_CONTENTS}}", files)

        response = call_claude(prompt)

        if response is None:
            print("Failed to get response from Claude")
            break

        try:
            # Parse the CLI output wrapper
            cli_response = json.loads(response)

            # When using --json-schema, the output is in structured_output
            if "structured_output" in cli_response:
                parsed = cli_response["structured_output"]
            else:
                print("Unexpected response format from Claude")
                print(response)
                break
        except Exception as e:
            print(f"Invalid JSON from Claude: {e}")
            print(f"Response: {response}")
            break

        # Apply changes and commit
        print(f"Applying changes to {len(parsed['files'])} file(s)...")
        apply_changes(parsed["files"])
        git_commit(parsed["commit_message"])

    # 3. Push branch (force push after first commit to update same PR)
    if first_commit_made:
        print("Force pushing to update PR...")
        git_push(force=True)
    else:
        print("Pushing to remote...")
        git_push()
        first_commit_made = True

    # Create PR after first push
    if pr_number is None:
        print("Creating pull request...")
        pr_number = create_pr()

    # 4. Wait 30 seconds for CI
    print("Waiting 30 seconds for CI to run...")
    time.sleep(30)

    # 5. Check CI
    print("Checking CI status...")
    ci_status = get_pr_status(pr_number)
    all_passed, checks = parse_ci_results(ci_status)

    # 6. If failed → extract logs → feed back to Claude
    if all_passed and checks:
        print("All CI checks passed!")
        break
    else:
        print("CI checks failed, extracting logs...")
        ci_logs = extract_ci_logs(checks)

        # Get detailed logs from the latest workflow run
        print("Fetching detailed workflow logs...")
        run_logs = get_latest_run_logs()
        ci_logs += f"\n\nWorkflow Run Logs:\n{run_logs}"
        # 7. Repeat (continue loop)

print("Done.")