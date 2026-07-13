"""Drive headless Blender to render a GLB into studio PNGs."""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

DEFAULT_BLENDER = "/Applications/Blender 4.5 LTS.app/Contents/MacOS/Blender"
SCENE_SCRIPT = Path(__file__).parent / "blender_scene.py"
DEFAULT_VIEWS = ("persp", "top", "front", "detail")


def render_glb(
    glb_path,
    outdir,
    views=DEFAULT_VIEWS,
    res=(1280, 960),
    samples=64,
) -> list[Path]:
    glb_path, outdir = Path(glb_path), Path(outdir)
    if not glb_path.exists():
        raise FileNotFoundError(glb_path)
    outdir.mkdir(parents=True, exist_ok=True)
    blender = os.environ.get("BLENDER_BIN", DEFAULT_BLENDER)
    written = [outdir / f"{v}.png" for v in views]
    for p in written:
        p.unlink(missing_ok=True)
    cmd = [
        blender, "--factory-startup", "-b", "--python-exit-code", "1",
        "-P", str(SCENE_SCRIPT), "--",
        str(glb_path), str(outdir), ",".join(views),
        f"{res[0]}x{res[1]}", str(samples),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    missing = [p for p in written if not p.exists() or p.stat().st_size == 0]
    if proc.returncode != 0 or missing:
        tail = "\n".join((proc.stderr or proc.stdout).splitlines()[-25:])
        raise RuntimeError(
            f"Blender render failed (rc={proc.returncode}, missing={missing}):\n{tail}"
        )
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("glb")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--views", default=",".join(DEFAULT_VIEWS))
    ap.add_argument("--res", default="1280x960")
    ap.add_argument("--samples", type=int, default=64)
    args = ap.parse_args()
    w, h = (int(v) for v in args.res.split("x"))
    for png in render_glb(
        args.glb, args.outdir, tuple(args.views.split(",")), (w, h), args.samples
    ):
        print(png)


if __name__ == "__main__":
    main()
