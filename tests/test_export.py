import pytest
from build123d import Pos, Torus, import_step

from tools.export import export_design, export_glb


def _parts():
    return {"link_1": Torus(20, 3), "link_2": Pos(50, 0, 0) * Torus(20, 3)}


def test_step_roundtrip_and_names(tmp_path):
    path = tmp_path / "two_tori.step"
    export_design(_parts(), path, assembly_label="pair")
    back = import_step(str(path))
    assert len(back.solids()) == 2
    total = sum(s.volume for s in back.solids())
    assert total == pytest.approx(2 * 3553.06, rel=1e-3)
    text = path.read_text()
    for name in ("pair", "link_1", "link_2"):
        assert name in text


def test_glb_export(tmp_path):
    path = tmp_path / "two_tori.glb"
    export_glb(_parts(), path)
    data = path.read_bytes()
    assert data[:4] == b"glTF"
    assert len(data) > 10_000
