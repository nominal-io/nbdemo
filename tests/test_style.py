import pytest


def test_set_plotly_style_registers_the_template():
    pio = pytest.importorskip("plotly.io")
    from nbdemo.style import TEMPLATE, set_plotly_style

    previous = pio.templates.default
    try:
        set_plotly_style()
        assert TEMPLATE in pio.templates
        assert pio.templates.default == f"plotly_white+{TEMPLATE}"
    finally:
        pio.templates.default = previous
