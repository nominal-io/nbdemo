import importlib.util
from pathlib import Path

import pytest

import nominal_samples as ns

pytest.importorskip("numpy")
pytest.importorskip("pandas")

SCRIPT = Path(__file__).parent.parent / "gen" / "aero_flight_dc.py"


def test_flight_script_reproduces_the_checked_in_file():
    spec = importlib.util.spec_from_file_location("aero_flight_dc", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.to_csv(module.generate()) == ns.aero.flight_dc.path.read_text()
