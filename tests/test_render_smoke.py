"""End-to-end render smoke test. Runs real Blender headlessly (~30-60s)."""
import os
import shutil
from pathlib import Path

import pytest
from build123d import Torus

from claudecad.export import export_glb
from claudecad.render import DEFAULT_BLENDER, render_glb

_blender = os.environ.get("BLENDER_BIN", DEFAULT_BLENDER)
pytestmark = pytest.mark.skipif(
    not (Path(_blender).exists() or shutil.which(_blender)),
    reason="Blender not available (set BLENDER_BIN); render loop is optional",
)


def test_render_torus(tmp_path):
    glb = tmp_path / "torus.glb"
    export_glb({"torus": Torus(20, 3)}, glb)
    pngs = render_glb(glb, tmp_path / "renders", views=("persp",), res=(480, 360), samples=24)
    assert len(pngs) == 1
    assert pngs[0].stat().st_size > 10_000


def test_render_failure_raises_despite_stale_png(tmp_path):
    """A failed render must raise, even when a stale PNG from a previous
    run sits in the outdir (Blender exits non-zero via --python-exit-code)."""
    bad_glb = tmp_path / "bad.glb"
    bad_glb.write_bytes(b"glTF garbage that is not a valid file")
    outdir = tmp_path / "renders"
    outdir.mkdir()
    (outdir / "persp.png").write_bytes(b"stale" * 1000)  # would pass the old check
    with pytest.raises(RuntimeError):
        render_glb(bad_glb, outdir, views=("persp",), res=(320, 240), samples=8)
