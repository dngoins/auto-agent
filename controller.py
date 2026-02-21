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
    result = subprocess.run(
        ["claude", "--print"],
        input=prompt,
        text=True,
        capture_output=True,
        shell=True
    )
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

    try:
        parsed = json.loads(response)
    except:
        print("Invalid JSON from Claude")
        break

    if parsed.get("status") == "complete":
        print("Agent marked complete.")
        break

    apply_changes(parsed["files"])
    git_commit(parsed["commit_message"])

print("Done.")