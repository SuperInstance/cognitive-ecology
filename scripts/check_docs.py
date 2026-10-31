#!/usr/bin/env python3
"""Machine-checked documentation truth (round 18).

The wave-1 diligence play-test found the README contradicting itself
(240 vs 121 tests; seven vs eight examples) and a CHANGELOG with no
entry for a release that had already shipped and been tagged. Numbers
that live only in prose rot; numbers that are checked against the tree
on every push cannot rot quietly. This script turns doc drift into a
build failure.

Checks
------
* version      the newest numbered section in CHANGELOG.md equals
               pyproject.toml's version (an [Unreleased] section may
               sit above it; it is not a version claim);
* tests        every "N tests" / "N passing" claim in README.md and the
               Makefile test comment equals the actually collected
               pytest count for tests/;
* examples     README's "Examples (N, ...)" heading (digits or spelled
               out), its example-table row count, its "N runnable
               organisms" layout line, and the count of examples/*/
               directories that contain a main.py all agree;
* adrs         "N architecture decision records" in README.md and
               INDEX.md equals the count of docs/ADRs/*.md;
* tutorials    "N hands-on tutorials" (digits or spelled out) in
               README.md equals the count of
               docs/tutorials/tutorial_*.md;
* guides       "N guides" in README.md equals the count of docs/0*.md.

It prints one line per check (ok: actual == claimed) and exits 1 with
a FAIL list if anything drifted. Run from anywhere; all paths resolve
from this file's parent. Zero dependencies beyond pytest being
importable (collection is how the test count is measured).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# spelled-out numbers that appear in prose claims ("eight", "four", ...)
_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12,
}


def _to_int(token: str):
    """'257' -> 257; 'eight' -> 8; anything else -> None."""
    if token.isdigit():
        return int(token)
    return _WORDS.get(token.lower())


def _collected_test_count():
    """Run pytest --collect-only and count, tolerating both output
    formats (per-file grouped counts on pytest 8+, one node id per
    line on earlier versions). Returns None when collection itself
    fails — the caller reports that as a drift, loudly.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         str(ROOT / "tests")],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if proc.returncode != 0:
        return None
    grouped, ids = 0, 0
    for line in proc.stdout.splitlines():
        m = re.match(r"^.*\.py:\s*(\d+)\s*$", line)
        if m:  # pytest 8+ grouped form: "tests/test_why.py: 8"
            grouped += int(m.group(1))
        elif "::" in line:  # node-id form: one test per line
            ids += 1
    total = grouped + ids
    return total if total > 0 else None


def _claim(text: str, pattern: str, what: str, failures: list, actual):
    """Collect every match of a claim pattern; each must equal actual."""
    found = re.findall(pattern, text, re.MULTILINE)
    for token in found:
        claimed = _to_int(token)
        if claimed is None:
            failures.append(f"{what}: unreadable number {token!r}")
        elif claimed != actual:
            failures.append(f"{what}: claims {claimed}, tree says {actual}")


def main() -> int:
    failures: list = []

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    index = (ROOT / "INDEX.md").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    checks: list = []

    # --- version: newest numbered CHANGELOG section == pyproject ------
    m_version = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    m_changelog = re.search(r"^## \[(\d+\.\d+\.\d+)\]", changelog, re.MULTILINE)
    if not m_version or not m_changelog:
        failures.append("version: could not read pyproject version or "
                         "CHANGELOG's newest numbered section")
    else:
        ok = m_changelog.group(1) == m_version.group(1)
        checks.append(("version",
                       f"changelog {m_changelog.group(1)} vs pyproject "
                       f"{m_version.group(1)}"))
        if not ok:
            failures.append(
                f"version: CHANGELOG's newest release section is "
                f"{m_changelog.group(1)} but pyproject says "
                f"{m_version.group(1)} — release one of them")

    # --- tests ---------------------------------------------------------
    n_tests = _collected_test_count()
    if n_tests is None:
        failures.append("tests: pytest collection failed — cannot verify "
                        "test-count claims (this is itself a drift)")
    else:
        _claim(readme, r"\b(\d+)\s+tests\b", "README 'N tests'", failures, n_tests)
        _claim(readme, r"\b(\d+)\s+passing\b", "README 'N passing'", failures, n_tests)
        _claim(index, r"\bof the (\d+)\s+tests\b", "INDEX 'of the N tests'", failures, n_tests)
        _claim(makefile, r"\((\d+)\s+tests,", "Makefile test comment", failures, n_tests)
        checks.append(("tests", f"collected {n_tests}"))

    # --- examples ------------------------------------------------------
    ex_dirs = [d for d in (ROOT / "examples").iterdir()
               if d.is_dir() and (d / "main.py").exists()]
    n_ex = len(ex_dirs)
    _claim(readme, r"## Examples \((\w+),", "README 'Examples (N,'", failures, n_ex)
    _claim(readme, r"(\w+) runnable organisms", "README 'N runnable organisms'",
           failures, n_ex)
    rows = re.findall(r"^\| \[\d{2}_", readme, re.MULTILINE)
    if len(rows) != n_ex:
        failures.append(f"README example table: {len(rows)} rows vs "
                        f"{n_ex} example dirs on disk")
    checks.append(("examples", f"{n_ex} dirs / table rows {len(rows)}"))

    # --- ADRs ----------------------------------------------------------
    n_adrs = len(list((ROOT / "docs" / "ADRs").glob("*.md")))
    _claim(readme, r"(\d+) architecture decision records",
           "README 'N architecture decision records'", failures, n_adrs)
    _claim(index, r"(\d+) architecture decision records",
           "INDEX 'N architecture decision records'", failures, n_adrs)
    checks.append(("adrs", f"{n_adrs} on disk"))

    # --- tutorials -----------------------------------------------------
    n_tut = len(list((ROOT / "docs" / "tutorials").glob("tutorial_*.md")))
    _claim(readme, r"(\w+) hands-on tutorials",
           "README 'N hands-on tutorials'", failures, n_tut)
    checks.append(("tutorials", f"{n_tut} on disk"))

    # --- guides --------------------------------------------------------
    n_guides = len(list((ROOT / "docs").glob("0*.md")))
    _claim(readme, r"(\d+) guides", "README 'N guides'", failures, n_guides)
    checks.append(("guides", f"{n_guides} on disk"))

    # --- report --------------------------------------------------------
    for name, detail in checks:
        print(f"  ok   {name:10s} {detail}")
    if failures:
        print("\nDOCS-TRUTH FAILURES:")
        for f in failures:
            print(f"  FAIL {f}")
        print("\nNumbers in prose rot. Fix the docs (or the tree), "
              "then push again.")
        return 1
    print("\ndocs truth holds: every documented count matches the tree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
