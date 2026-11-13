"""Allocations inside one trailing-whitespace SEARCH on a large parent.

Default diff evolution calls apply_diff_blocks, which calls _find_search_lines
once per SEARCH block. The parent is the real 2911-line database.py source: a
stand-in for a large program the diff applier patches. The SEARCH block is 80
lines from the end of that file with three trailing spaces added to each line,
which is the mismatch the function documents (LLMs add or drop trailing
spaces). Exact equality therefore fails and the whitespace-tolerant scan runs.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import emit, load_alloccount  # noqa: E402
from openevolve.utils.code_utils import _find_search_lines  # noqa: E402

NEEDLE = 80
RUNS = 5


def workload():
    text = (ROOT / "openevolve" / "database.py").read_text(encoding="utf-8")
    lines = text.split("\n")
    start = len(lines) - NEEDLE - 1
    # Spaces are on the SEARCH side, as an LLM block would emit them.
    search = [line + "   " for line in lines[start : start + NEEDLE]]
    return lines, search


def check(lines, search, index):
    if index < 0:
        raise SystemExit("search did not match")
    found = [line.rstrip() for line in lines[index : index + len(search)]]
    wanted = [line.rstrip() for line in search]
    if found != wanted:
        raise SystemExit(f"match at {index} is not the whitespace-tolerant block")


def main():
    counter = load_alloccount()
    lines, search = workload()
    check(lines, search, _find_search_lines(lines, search))

    samples = []
    for _ in range(RUNS):
        counter.start()
        try:
            index = _find_search_lines(lines, search)
        finally:
            samples.append(counter.stop())
        check(lines, search, index)
    emit("allocations", samples)


if __name__ == "__main__":
    main()
