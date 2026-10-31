#!/usr/bin/env python3
"""Secrets guard: fail if any tracked file looks like it contains a key.

Runs in CI and as a pre-push hook. Patterns are deliberately narrow (real key
shapes, not the word "token"). A hit is a build failure, not a warning —
rotate the key, then fix the file.
"""

from __future__ import annotations

import re
import subprocess
import sys

PATTERNS = [
    r"ghp_[A-Za-z0-9]{20,}",
    r"github_pat_[A-Za-z0-9_]{20,}",
    r"apikey_[0-9a-f]{16,}",
    r"sk-cp-[A-Za-z0-9_\-]{20,}",
    r"sk-di-[A-Za-z0-9]{8,}",
    r"sk-ant-[A-Za-z0-9_\-]{20,}",
    r"AKIA[0-9A-Z]{16}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
]


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    ).stdout
    return [f for f in out.splitlines() if f]


def main() -> int:
    files = tracked_files()
    if not files:
        print("check_secrets: no tracked files (ok)")
        return 0
    bad: list[tuple[str, str]] = []
    for path in files:
        try:
            with open(path, encoding="utf-8", errors="ignore") as handle:
                text = handle.read()
        except OSError:
            continue
        for pattern in PATTERNS:
            if re.search(pattern, text):
                bad.append((path, pattern))
    if bad:
        for path, pattern in bad:
            print(f"SECRET-LIKE MATCH: {path} matches /{pattern}/", file=sys.stderr)
        print(
            "check_secrets: FAILED — if these are real keys, rotate them now",
            file=sys.stderr,
        )
        return 1
    print(f"check_secrets: {len(files)} tracked files clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
