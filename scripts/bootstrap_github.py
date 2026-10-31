#!/usr/bin/env python3
"""Create the GitHub repo (if missing) and push the current branch.

Auth comes from the GITHUB_PAT environment variable — never from a file that
ships with the repo, never in a URL, never in git config. The push uses a
credential helper that reads the token from the environment at call time.

Usage:
    python scripts/bootstrap_github.py [--name cognitive-ecology] [--private]
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

import httpx

DESCRIPTION = (
    "A persistent cognitive ecology: WHY (live justification) as the "
    "conservation law governing a world of processes, attention, scripts, "
    "and sleep."
)


def sh(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}", file=sys.stderr)
    return subprocess.run(cmd, check=True, **kwargs)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="cognitive-ecology")
    parser.add_argument("--private", action="store_true")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_PAT")
    if not token:
        print("GITHUB_PAT not set in environment", file=sys.stderr)
        return 2
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    with httpx.Client(timeout=30) as client:
        me = client.get("https://api.github.com/user", headers=headers)
        if me.status_code != 200:
            print(f"whoami failed: {me.status_code} {me.text[:200]}", file=sys.stderr)
            return 2
        login = me.json()["login"]
        uid = me.json()["id"]
        display_name = me.json().get("name") or login

        sh(["git", "config", "user.name", display_name])
        sh(["git", "config", "user.email", f"{uid}+{login}@users.noreply.github.com"])

        existing = client.get(
            f"https://api.github.com/repos/{login}/{args.name}", headers=headers
        )
        if existing.status_code == 404:
            created = client.post(
                "https://api.github.com/user/repos",
                headers=headers,
                json={
                    "name": args.name,
                    "description": DESCRIPTION,
                    "private": args.private,
                    "has_issues": True,
                    "has_wiki": False,
                },
            )
            if created.status_code not in (200, 201):
                print(
                    f"create failed: {created.status_code} {created.text[:300]}",
                    file=sys.stderr,
                )
                return 2
            print(f"created repo {login}/{args.name} (private={args.private})")
        elif existing.status_code == 200:
            print(f"repo {login}/{args.name} already exists")
        else:
            print(f"lookup failed: {existing.status_code}", file=sys.stderr)
            return 2

    remote_url = f"https://github.com/{login}/{args.name}.git"
    remotes = subprocess.run(
        ["git", "remote"], capture_output=True, text=True, check=True
    ).stdout.split()
    if "origin" not in remotes:
        sh(["git", "remote", "add", "origin", remote_url])

    # Credential helper reads $GITHUB_PAT from the environment at push time;
    # the token never lands in argv, URLs, or .git/config.
    helper = "!f() { echo username=x-access-token; echo password=$GITHUB_PAT; }; f"
    sh(["git", "-c", f"credential.helper={helper}", "push", "-u", "origin", "main"])
    print(f"pushed -> https://github.com/{login}/{args.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
