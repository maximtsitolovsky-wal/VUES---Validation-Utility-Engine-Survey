from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class GitCommandError(RuntimeError):
    """Raised when a git command fails."""


@dataclass(frozen=True)
class GitCommandResult:
    command: list[str]
    stdout: str
    stderr: str
    returncode: int


@dataclass(frozen=True)
class PushReceipt:
    branch: str
    local_head: str
    remote: str
    remote_head: str
    merge_base: str
    local_is_remote_head: bool
    remote_contains_local: bool
    dirty_worktree: bool
    ahead_behind: dict[str, int]
    status_short: str
    remotes: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch": self.branch,
            "local_head": self.local_head,
            "remote": self.remote,
            "remote_head": self.remote_head,
            "merge_base": self.merge_base,
            "local_is_remote_head": self.local_is_remote_head,
            "remote_contains_local": self.remote_contains_local,
            "dirty_worktree": self.dirty_worktree,
            "ahead_behind": self.ahead_behind,
            "status_short": self.status_short,
            "remotes": self.remotes,
        }


def run_git(*args: str, check: bool = True) -> GitCommandResult:
    command = ["git", *args]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    result = GitCommandResult(
        command=command,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
        returncode=completed.returncode,
    )
    if check and completed.returncode != 0:
        raise GitCommandError(
            f"git command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )
    return result


def get_remote_map() -> dict[str, str]:
    output = run_git("remote", "-v").stdout.splitlines()
    remotes: dict[str, str] = {}
    for line in output:
        parts = line.split()
        if len(parts) >= 3 and parts[2] == "(push)":
            remotes[parts[0]] = parts[1]
    return remotes


def parse_ahead_behind(branch: str, remote: str) -> dict[str, int]:
    counts = run_git("rev-list", "--left-right", "--count", f"{branch}...{remote}/{branch}").stdout
    ahead_str, behind_str = counts.split()
    return {"ahead": int(ahead_str), "behind": int(behind_str)}


def build_receipt(remote: str, branch: str) -> PushReceipt:
    remotes = get_remote_map()
    if remote not in remotes:
        raise GitCommandError(f"Remote '{remote}' not found. Known push remotes: {sorted(remotes)}")

    run_git("fetch", remote, branch)
    local_head = run_git("rev-parse", "HEAD").stdout
    remote_head = run_git("rev-parse", f"{remote}/{branch}").stdout
    merge_base = run_git("merge-base", "HEAD", f"{remote}/{branch}").stdout
    status_short = run_git("status", "--short", "--branch").stdout
    dirty_worktree = bool(run_git("status", "--porcelain").stdout)
    ahead_behind = parse_ahead_behind(branch, remote)

    return PushReceipt(
        branch=branch,
        local_head=local_head,
        remote=remote,
        remote_head=remote_head,
        merge_base=merge_base,
        local_is_remote_head=(local_head == remote_head),
        remote_contains_local=(merge_base == local_head),
        dirty_worktree=dirty_worktree,
        ahead_behind=ahead_behind,
        status_short=status_short,
        remotes=remotes,
    )


def print_human(receipt: PushReceipt) -> None:
    state = "VERIFIED" if receipt.local_is_remote_head else "NOT_PUSHED"
    print(f"state: {state}")
    print(f"branch: {receipt.branch}")
    print(f"remote: {receipt.remote}")
    print(f"local_head: {receipt.local_head}")
    print(f"remote_head: {receipt.remote_head}")
    print(f"merge_base: {receipt.merge_base}")
    print(
        "ahead_behind: "
        f"ahead={receipt.ahead_behind['ahead']} behind={receipt.ahead_behind['behind']}"
    )
    print(f"dirty_worktree: {receipt.dirty_worktree}")
    print(f"remote_contains_local: {receipt.remote_contains_local}")
    print("status_short:")
    print(receipt.status_short or "<clean>")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that the current HEAD actually exists on a git remote."
    )
    parser.add_argument("--remote", default="walmart-origin", help="Remote to verify against.")
    parser.add_argument("--branch", default=None, help="Branch to verify. Defaults to current branch.")
    parser.add_argument(
        "--format",
        choices=("human", "json"),
        default="human",
        help="Output format.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero unless local HEAD exactly matches remote/<branch> HEAD.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    branch = args.branch or run_git("rev-parse", "--abbrev-ref", "HEAD").stdout

    try:
        receipt = build_receipt(remote=args.remote, branch=branch)
    except GitCommandError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(receipt.to_dict(), indent=2))
    else:
        print_human(receipt)

    if args.strict and not receipt.local_is_remote_head:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
