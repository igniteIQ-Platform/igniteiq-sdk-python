#!/usr/bin/env python3
"""Does CI actually test the Python version we promise consumers?

`pyproject.toml` says `requires-python = ">=3.10"`. That string is a promise to everyone
who runs `pip install igniteiq-vault`, and it is only worth anything if something runs the
package on that interpreter. Nothing did for two releases: the floor said 3.9, no job ever
started a 3.9, and both 0.1.0 and 0.2.0 shipped unable to import there at all.

Raising the floor to 3.10 fixed the claim. It did not fix the mechanism that let the claim
rot, which was that the floor and the test matrix were two independent facts that agreed
only while someone remembered they should. This is the machine that remembers.

  python3 scripts/check_python_floor.py --self-test
  python3 scripts/check_python_floor.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def parse_floor(pyproject_text: str) -> tuple[int, int] | None:
    m = re.search(r'^\s*requires-python\s*=\s*"[><=~^ ]*(\d+)\.(\d+)', pyproject_text, re.M)
    return (int(m.group(1)), int(m.group(2))) if m else None


def parse_matrices(workflow_text: str) -> list[tuple[int, int]]:
    """Every `python: [...]` matrix in the workflow, as its LOWEST version."""
    out = []
    for line in re.findall(r'^\s*python:\s*\[(.+?)\]\s*$', workflow_text, re.M):
        versions = [tuple(int(p) for p in v.split(".")[:2])
                    for v in re.findall(r'"(\d+\.\d+)"', line)]
        if versions:
            out.append(min(versions))
    return out


def assess(floor, matrix_lows):
    if floor is None:
        return 1, "Could not read requires-python from pyproject.toml. Not a pass — nothing was compared."
    if not matrix_lows:
        # The failure this exists for, in its most dangerous form: a green CI that never
        # started the interpreter we promise. Absence of a matrix reads as absence of a
        # problem unless something says otherwise.
        return 1, "No `python: [...]` matrix found in ci.yml. Nothing is testing the declared floor."
    shown = ".".join(map(str, floor))
    bad = [m for m in matrix_lows if m != floor]
    if bad:
        return 1, (
            f"requires-python promises >={shown}, but a CI matrix starts at "
            f"{', '.join('.'.join(map(str, m)) for m in bad)}. "
            f"Either test the floor or stop promising it."
        )
    return 0, f"requires-python >={shown} and every CI matrix starts at {shown}."


def self_test() -> int:
    fails = []

    def eq(got, want, what):
        if got != want:
            fails.append(f"{what}: got {got!r} want {want!r}")

    eq(parse_floor('requires-python = ">=3.10"'), (3, 10), "parses the floor")
    eq(parse_floor('# requires-python = ">=3.9"\nrequires-python = ">=3.10"'), (3, 10),
       "a commented-out floor does not win")
    eq(parse_matrices('        python: ["3.10", "3.12"]'), [(3, 10)], "parses a matrix low")

    eq(assess((3, 10), [(3, 10), (3, 10)])[0], 0, "agreement passes")
    eq(assess((3, 10), [(3, 12)])[0], 1, "a matrix above the floor fails")
    eq(assess((3, 10), [(3, 10), (3, 12)])[0], 1, "ONE lagging matrix is enough to fail")
    # Both ways of learning nothing must fail, or this check certifies silence as agreement.
    eq(assess(None, [(3, 10)])[0], 1, "an unreadable floor fails")
    eq(assess((3, 10), [])[0], 1, "no matrix at all fails")

    if fails:
        print("self-test FAIL:", file=sys.stderr)
        for f in fails:
            print("  " + f, file=sys.stderr)
        return 1
    print("self-test OK — drift fails, and 'could not compare' never reads as agreement")
    return 0


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return self_test()
    code, message = assess(parse_floor(PYPROJECT.read_text()),
                           parse_matrices(WORKFLOW.read_text()))
    print(("::error::" if code else "") + message)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
