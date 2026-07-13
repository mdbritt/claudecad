"""End-to-end render smoke test. Runs real Blender headlessly (~30-60s)."""
from build123d import Torus

from tools.export import export_glb
from tools.render import render_glb


def test_render_torus(tmp_path):
    glb = tmp_path / "torus.glb"
    export_glb({"torus": Torus(20, 3)}, glb)
    pngs = render_glb(glb, tmp_path / "renders", views=("persp",), res=(480, 360), samples=24)
    assert len(pngs) == 1
    assert pngs[0].stat().st_size > 10_000
