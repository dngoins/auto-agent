#!/usr/bin/env python3
"""
Extract requirements from GitHub event context.

Supports:
- Issues with 'auto-implement' label
- PRs with 'auto-implement' label or '[AUTO-IMPLEMENT]' title
- Pushed .gherkin files
- Manual workflow_dispatch input
"""

import os
import sys
import json
from pathlib import Path


def extract_from_issue(event_data):
    """Extract requirements from GitHub issue"""
    issue = event_data['issue']
    return {
        'source': 'issue',
        'issue_number': issue['number'],
        'text': issue['body'] or '',
        'title': issue['title']
    }


def extract_from_pr(event_data):
    """Extract requirements from PR description"""
    pr = event_data['pull_request']
    return {
        'source': 'pr',
        'pr_number': pr['number'],
        'text': pr['body'] or '',
        'title': pr['title']
    }


def extract_from_file_push(event_data):
    """Extract requirements from pushed .gherkin file"""
    # Method 1: Try to get from commits in event data
    commits = event_data.get('commits', [])
    gherkin_files = []

    for commit in commits:
        added = commit.get('added', [])
        modified = commit.get('modified', [])
        all_files = added + modified

        gherkin_files.extend([
            f for f in all_files
            if f.endswith('.gherkin')
        ])

    # Method 2: If no files found in commits, scan the directories
    if not gherkin_files:
        print("No .gherkin files found in commit data, scanning directories...", file=sys.stderr)

        # Scan features/ and requirements/ directories
        for directory in ['features', 'requirements']:
            dir_path = Path(directory)
            if dir_path.exists():
                for gherkin_file in dir_path.glob('*.gherkin'):
                    # Skip template files
                    if gherkin_file.name not in ['TEMPLATE.gherkin', 'QUICKSTART.gherkin']:
                        gherkin_files.append(str(gherkin_file))

        if not gherkin_files:
            print("No .gherkin files found in features/ or requirements/ directories", file=sys.stderr)
            return None

    # Read the first .gherkin file found
    file_path = Path(gherkin_files[0])

    print(f"Found .gherkin file: {file_path}", file=sys.stderr)

    if file_path.exists():
        content = file_path.read_text()
        print(f"Successfully read {len(content)} characters from {file_path}", file=sys.stderr)
        return {
            'source': 'file',
            'file_path': str(file_path),
            'text': content,
            'title': f"Feature from {file_path.name}"
        }
    else:
        print(f"File path does not exist: {file_path}", file=sys.stderr)

    return None


def extract_from_workflow_dispatch(event_data):
    """Extract requirements from manual workflow input"""
    inputs = event_data.get('inputs', {})
    return {
        'source': 'manual',
        'text': inputs.get('requirements', ''),
        'skip_questions': inputs.get('auto_approve', 'false') == 'true',
        'title': 'Manual Feature Request'
    }


def main():
    event_name = os.environ.get('GITHUB_EVENT_NAME')
    event_path = os.environ.get('GITHUB_EVENT_PATH')

    print(f"Event name: {event_name}", file=sys.stderr)
    print(f"Event path: {event_path}", file=sys.stderr)

    if not event_path or not Path(event_path).exists():
        print("Error: GitHub event data not found", file=sys.stderr)
        sys.exit(1)

    with open(event_path) as f:
        event_data = json.load(f)

    # Debug: Show event structure
    print(f"Event data keys: {list(event_data.keys())}", file=sys.stderr)

    # Extract based on event type
    requirements = None

    if event_name == 'issues':
        print("Processing issue event...", file=sys.stderr)
        requirements = extract_from_issue(event_data)
    elif event_name == 'pull_request':
        print("Processing pull request event...", file=sys.stderr)
        requirements = extract_from_pr(event_data)
    elif event_name == 'push':
        print("Processing push event...", file=sys.stderr)
        requirements = extract_from_file_push(event_data)
    elif event_name == 'workflow_dispatch':
        print("Processing workflow dispatch event...", file=sys.stderr)
        requirements = extract_from_workflow_dispatch(event_data)
    else:
        print(f"Unknown event type: {event_name}", file=sys.stderr)

    if not requirements:
        print(f"Error: Could not extract requirements from {event_name} event", file=sys.stderr)
        print("Check the logs above for details", file=sys.stderr)
        sys.exit(1)

    # Output for GitHub Actions
    # Set output variables using new syntax
    output_file = os.environ.get('GITHUB_OUTPUT')
    if output_file:
        with open(output_file, 'a') as f:
            f.write(f"source={requirements['source']}\n")
            f.write(f"text<<EOF\n{requirements['text']}\nEOF\n")
            f.write(f"title={requirements.get('title', 'Feature Request')}\n")

    # Also print for debugging
    print(f"Requirements extracted from: {requirements['source']}")
    print(f"Title: {requirements.get('title')}")
    print(f"Text length: {len(requirements['text'])} characters")


if __name__ == '__main__':
    main()
