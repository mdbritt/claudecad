"""claudecad command line: render GLBs (and, in later tasks, scaffold
projects). Stdlib only — argparse; no new runtime dependencies."""
from __future__ import annotations

import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="claudecad",
        description="Verification-first parametric CAD tooling for "
                    "Claude Code projects.")
    sub = ap.add_subparsers(dest="command", required=True)

    new = sub.add_parser(
        "new", help="stamp a ready-to-design claudeCAD project")
    new.add_argument("name")
    new.add_argument("--dir", default=".",
                     help="parent directory (default: cwd)")

    render = sub.add_parser(
        "render", help="render a GLB into studio PNGs via headless Blender")
    render.add_argument("glb")
    render.add_argument("--outdir", required=True)
    render.add_argument("--views", default="persp,top,front,detail")
    render.add_argument("--res", default="1280x960")
    render.add_argument("--samples", type=int, default=64)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "new":
        from pathlib import Path

        from claudecad.scaffold import new_project
        try:
            target = new_project(args.name, Path(args.dir))
        except ValueError as e:
            print(f"claudecad new: {e}", file=sys.stderr)
            return 1
        print(f"created {target} — next: cd {target} && uv sync, "
              "then design in chat")
        return 0
    if args.command == "render":
        from claudecad.render import render_glb
        w, h = (int(v) for v in args.res.split("x"))
        try:
            render_glb(args.glb, args.outdir,
                       tuple(args.views.split(",")), (w, h), args.samples)
        except FileNotFoundError as e:
            print(f"claudecad render: {e}", file=sys.stderr)
            return 1
        return 0
    raise AssertionError(f"unhandled command {args.command!r}")


if __name__ == "__main__":
    raise SystemExit(main())
