"""A plotly style for the demo notebooks' plots."""

from __future__ import annotations

TEMPLATE = "nbdemo"
"""Name the style is registered under in ``plotly.io.templates``."""

_GRID = "rgba(128, 128, 128, 0.2)"


def set_plotly_style() -> None:
    """Make the nbdemo style the default for plotly figures.

    The style is wide and transparent, with faint gridlines and grey text, so plots sit on the page in
    both dark and light themes. Lines start at teal. It applies to every plotly figure made afterwards.
    Adapted from panominal's style.

    The style is registered as ``"nbdemo"`` and layered on ``plotly_white``. To use it for one figure,
    pass ``template="plotly_white+nbdemo"`` after calling this once.

    Needs plotly, from the ``plotly`` extra (``nbdemo[plotly]``).
    """
    import plotly.io as pio
    from plotly.colors import qualitative

    axis = dict(gridcolor=_GRID, linecolor=_GRID, zeroline=False)
    pio.templates[TEMPLATE] = dict(
        layout=dict(
            paper_bgcolor="rgba(0, 0, 0, 0)",
            plot_bgcolor="rgba(0, 0, 0, 0)",
            font=dict(color="#8a8a8a", family="Geist, sans-serif"),
            colorway=qualitative.Plotly[2:] + qualitative.Plotly[:2],  # teal first
            height=320,
            margin=dict(l=50, r=10, t=40, b=40),
            xaxis=axis,
            yaxis=axis,
            legend=dict(orientation="h", x=0, y=1.02, yanchor="bottom"),  # top left, clear of the toolbar
            hovermode="x unified",
        )
    )
    pio.templates.default = f"plotly_white+{TEMPLATE}"
