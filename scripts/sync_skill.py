"""Single-source the /cad skill.

.claude/skills/cad/SKILL.md is the ONE source of truth. Two consumers need
byte-identical copies tracked in git: skills/cad/SKILL.md (the Claude Code
plugin layout) and claudecad/_scaffold/skills/cad/SKILL.md (package data
the scaffolder stamps into new projects). Run with no args to write the
copies; --check (CI) exits 1 if any copy is missing or drifted.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / ".claude" / "skills" / "cad" / "SKILL.md"
COPIES = [
    REPO / "skills" / "cad" / "SKILL.md",
    REPO / "claudecad" / "_scaffold" / "skills" / "cad" / "SKILL.md",
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify copies match the source instead of writing")
    args = ap.parse_args()

    src_text = SRC.read_text()
    drifted = []
    for dst in COPIES:
        if args.check:
            if not dst.is_file() or dst.read_text() != src_text:
                drifted.append(dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SRC, dst)
            print(f"synced {dst.relative_to(REPO)}")
    if drifted:
        rels = ", ".join(str(d.relative_to(REPO)) for d in drifted)
        print(f"skill copies drifted from {SRC.relative_to(REPO)}: {rels}\n"
              f"run: python scripts/sync_skill.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
