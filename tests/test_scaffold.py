import build123d


def test_build123d_version():
    major, minor, *_ = build123d.__version__.split(".")
    assert (int(major), int(minor)) == (0, 11)


def test_claudecad_imports():
    import claudecad  # noqa: F401
