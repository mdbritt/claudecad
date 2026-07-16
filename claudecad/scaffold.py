"""Stamp a ready-to-design claudeCAD project (`claudecad new <name>`).

The template ships as package data under claudecad/_scaffold/ (a real
source directory — identical in a repo checkout and in the wheel), so the
stamped project's gate runs green immediately: pyproject depending on
claudecad, the /cad skill, a designs/<name>/ from the template, out/.
"""
from __future__ import annotations

import re
from importlib import resources
from pathlib import Path

_NAME_RE = re.compile(r"[a-z][a-z0-9_]*\Z")

_PYPROJECT = """\
[project]
name = "{name}"
version = "0.1.0"
description = "A claudeCAD design project"
requires-python = ">=3.12"
dependencies = ["claudecad"]

[dependency-groups]
dev = ["pytest>=8"]
"""

_README = """\
# {name}

A claudeCAD design project. Design in chat with Claude Code (the /cad
skill drives the loop); the gate verifies; STEP comes out.

    uv sync
    uv run python -m designs.{name}.build      # build + verify + export
    uv run claudecad render out/glb/{name}.glb --outdir out/renders/{name}

Edit `designs/{name}/params.py` (every driving dimension) and
`designs/{name}/build.py` (parts + the verification gate). STEP lands in
`out/step/{name}.step` when — and only when — the gate passes.
"""

_GITIGNORE = """\
out/
__pycache__/
*.pyc
.venv/
"""


def new_project(name: str, parent: Path) -> Path:
    """Create `parent/name` as a ready-to-design project. Raises ValueError
    for invalid names or a non-empty existing target."""
    if not _NAME_RE.match(name or ""):
        raise ValueError(
            f"invalid project name {name!r}: need a python-identifier-safe "
            "lowercase name matching [a-z][a-z0-9_]*"
        )
    parent = Path(parent)
    target = parent / name
    if target.exists() and any(target.iterdir()):
        raise ValueError(f"target {target} exists and is not empty")

    scaffold = resources.files("claudecad") / "_scaffold"

    design_dst = target / "designs" / name
    design_dst.mkdir(parents=True, exist_ok=True)
    template = scaffold / "designs" / "_template"
    for fname in ("build.py", "params.py"):
        text = (template / fname).read_text()
        (design_dst / fname).write_text(text.replace("_template", name))

    # the /cad skill ships in _scaffold from the skill-sync task (single-
    # sourcing); guard so this task is independently green before it exists
    skill_src = scaffold / "skills" / "cad" / "SKILL.md"
    if skill_src.is_file():
        skill_dst = target / ".claude" / "skills" / "cad" / "SKILL.md"
        skill_dst.parent.mkdir(parents=True, exist_ok=True)
        skill_dst.write_text(skill_src.read_text())

    (target / "out").mkdir(exist_ok=True)
    (target / "out" / ".gitkeep").touch()
    (target / "pyproject.toml").write_text(_PYPROJECT.format(name=name))
    (target / "README.md").write_text(_README.format(name=name))
    (target / ".gitignore").write_text(_GITIGNORE)
    return target
