"""Fast smoke: every design module imports and exposes main().

Catches bitrot in designs/ (which the heavy build gates only catch when
someone runs a full build)."""
import importlib

import pytest

DESIGNS = ["designs.bolt.build", "designs.bolt.params",
           "designs.carabiner.build", "designs.carabiner.params",
           "designs.cuban_bracelet.build", "designs.cuban_bracelet.params",
           "designs.cuban_bracelet.probe", "designs.simple_curb.build",
           "designs.simple_curb.params", "designs._template.build",
           "designs._template.params", "designs.bearing_608.build",
           "designs.bearing_608.params", "designs.snapbox.build",
           "designs.snapbox.params"]


@pytest.mark.parametrize("module", DESIGNS)
def test_design_module_imports(module):
    mod = importlib.import_module(module)
    if module.endswith(".build"):
        assert callable(getattr(mod, "main"))
