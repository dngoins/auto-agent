import subprocess
import json
import os
from pathlib import Path
from anthropic import Anthropic

MAX_ITERS = 5


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


def git_commit(message):
    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", message])


for iteration in range(MAX_ITERS):
    print(f"\n=== Iteration {iteration + 1} ===")

    code, output = run_tests()

    if code == 0:
        print("Tests passed.")
        break

    files = collect_files()

    template = Path("prompt.md").read_text()
    prompt = template.replace("{{TEST_OUTPUT}}", output)
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

    # Apply the changes
    print(f"Applying changes to {len(parsed['files'])} file(s)...")
    apply_changes(parsed["files"])

    # Verify tests pass after applying changes
    code, output = run_tests()
    if code == 0:
        print("Tests passed after applying changes!")
        git_commit(parsed["commit_message"])
        break
    else:
        print("Tests still failing after changes, continuing...")
        git_commit(parsed["commit_message"])

print("Done.")