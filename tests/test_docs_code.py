"""Docs code must run, not read pretty (round 18).

The wave-1 hobbyist persona hit a TypeError on the quickstart's first
copy-paste (`Tiny(rt)` — the doc shipped broken for days, and every
cold user hit it in minute one). This test extracts the doc's code
block and EXECUTES it, so a doc can never again rot into a crash: if
you edit docs/01_quick_start.md, this test is your gate. It also pins
the doc's homeostasis promise (a sawtooth, not a pinned zero).
"""
import re
from pathlib import Path

from cognitive_ecology import Runtime  # noqa: F401  (the doc imports it)


def _first_python_block(doc: Path) -> str:
    """The quickstart's 60-second organism, exactly as shipped in prose."""
    text = doc.read_text(encoding="utf-8")
    blocks = re.findall(r"```python\n(.*?)```", text, re.DOTALL)
    assert blocks, f"no python block found in {doc}"
    return blocks[0]


def test_quickstart_code_block_runs_and_oscillates(capsys):
    doc = (Path(__file__).resolve().parent.parent
           / "docs" / "01_quick_start.md")
    code = _first_python_block(doc)

    ns: dict = {}
    exec(compile(code, str(doc), "exec"), ns)  # a TypeError here = doc rot

    rt = ns["rt"]
    # the doc's own promise: homeostasis oscillates — a sawtooth, not a
    # drive pinned at 0 or 1 (which docs/07 calls a diagnosis)
    levels = [r.tensions["curiosity"] for r in rt.run(30)]
    assert rt.why.conservation()["invariant_ok"] is True
    assert max(levels) >= 0.29, "the drive must build up before easing"
    assert min(levels) <= 0.01, "the relief must actually land"
    assert levels != sorted(levels), "must oscillate, not climb"

    # the doc's print loop produced teaching output (it is an organism)
    assert "['observe']" in capsys.readouterr().out
