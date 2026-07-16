import os
import shutil

import pytest

import claudecad.render as render


def test_env_override_strict(monkeypatch, tmp_path):
    monkeypatch.setenv("BLENDER_BIN", str(tmp_path / "nope"))
    with pytest.raises(FileNotFoundError, match="BLENDER_BIN"):
        render.find_blender()


def test_env_override_accepts_executable(monkeypatch, tmp_path):
    fake = tmp_path / "blender"
    fake.write_text("#!/bin/sh\n")
    fake.chmod(0o755)
    monkeypatch.setenv("BLENDER_BIN", str(fake))
    assert render.find_blender() == str(fake)


def test_path_lookup_wins_over_globs(monkeypatch):
    monkeypatch.delenv("BLENDER_BIN", raising=False)
    monkeypatch.setattr(shutil, "which",
                        lambda name: "/fake/bin/blender"
                        if name == "blender" else None)
    assert render.find_blender() == "/fake/bin/blender"


def test_glob_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("BLENDER_BIN", raising=False)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    fake = tmp_path / "Blender 4.5 LTS.app" / "Contents" / "MacOS"
    fake.mkdir(parents=True)
    (fake / "Blender").write_text("#!/bin/sh\n")
    monkeypatch.setattr(
        render, "_PLATFORM_GLOBS",
        (str(tmp_path / "Blender*.app" / "Contents" / "MacOS" / "Blender"),))
    assert render.find_blender() == str(fake / "Blender")


def test_helpful_error_when_nothing_found(monkeypatch):
    monkeypatch.delenv("BLENDER_BIN", raising=False)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.setattr(render, "_PLATFORM_GLOBS", ())
    with pytest.raises(FileNotFoundError, match="BLENDER_BIN=/path/to"):
        render.find_blender()
