import pytest

from claudecad.cli import main


def test_render_requires_outdir(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["render", "some.glb"])
    assert exc.value.code == 2  # argparse usage error


def test_render_missing_glb_reports_cleanly(tmp_path):
    # render_glb raises FileNotFoundError for a missing GLB; the CLI
    # surfaces it as a nonzero exit with a message, not a traceback
    rc = main(["render", str(tmp_path / "nope.glb"),
               "--outdir", str(tmp_path / "out")])
    assert rc == 1


def test_no_command_is_usage_error():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
