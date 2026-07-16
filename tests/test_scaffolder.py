import subprocess
import sys

import pytest

from claudecad.scaffold import new_project


def test_new_project_structure(tmp_path):
    target = new_project("mypart", tmp_path)
    assert target == tmp_path / "mypart"
    assert (target / "pyproject.toml").exists()
    assert (target / "designs" / "mypart" / "build.py").exists()
    assert (target / "designs" / "mypart" / "params.py").exists()
    assert (target / "out" / ".gitkeep").exists()
    assert (target / ".gitignore").exists()
    assert (target / "README.md").exists()


def test_template_strings_renamed(tmp_path):
    target = new_project("mypart", tmp_path)
    build = (target / "designs" / "mypart" / "build.py").read_text()
    assert "_template" not in build
    assert "designs.mypart.build" in build      # usage line renamed
    assert "out/glb/mypart.glb" in build        # artifact path renamed
    assert "from claudecad.export import" in build


def test_refuses_nonempty_target(tmp_path):
    (tmp_path / "mypart").mkdir()
    (tmp_path / "mypart" / "junk.txt").write_text("x")
    with pytest.raises(ValueError, match="not empty"):
        new_project("mypart", tmp_path)


def test_rejects_bad_names(tmp_path):
    for bad in ("My-Part", "1part", "designs/evil", ""):
        with pytest.raises(ValueError):
            new_project(bad, tmp_path)


def test_stamped_build_runs_green(tmp_path):
    """The stamped project's gate runs end-to-end with THIS checkout's
    claudecad on the path — the in-repo half of the clean-room story
    (the CI clean-room job repeats this against the built wheel)."""
    target = new_project("demo", tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "designs.demo.build"],
        cwd=target, capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (target / "out" / "step" / "demo.step").exists()
