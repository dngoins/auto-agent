import subprocess
import time


def create_gh_branch():
    BRANCH = f"agent-{int(time.time())}"
    subprocess.run(["git", "checkout", "-b", BRANCH])
    subprocess.run(["git", "push", "-u", "origin", BRANCH])
    return BRANCH


def git_commit(message):
    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", message])


def git_push(force=False):
    if force:
        subprocess.run(["git", "push", "--force"])
    else:
        subprocess.run(["git", "push"])
