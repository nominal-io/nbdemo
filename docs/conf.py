"""Sphinx config for the Nominal demo notebooks site."""

import sys
from pathlib import Path

from nominal.config import NominalConfig
from nominal.exceptions import NominalConfigError
from nominal_sphinx_theme import theme_options

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "_ext"))

project = "Nominal demos"
copyright = "Nominal, Inc."

extensions = [
    "myst_nb",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinxcontrib.mermaid",
    "gallery",
    "nominal_sphinx_theme",
]

exclude_patterns = ["**/.ipynb_checkpoints"]

# -- MyST ---------------------------------------------------------------------
myst_heading_anchors = 3
myst_enable_extensions = ["colon_fence", "deflist", "attrs_inline", "attrs_block"]
# A plain ```mermaid fence renders in Sphinx, and in JupyterLab too.
myst_fence_as_directive = ["mermaid"]

# -- MyST-NB: run each notebook on build, as the nominal-client examples do ----------
# The cache (in _build) re-runs only notebooks whose code changed. CI keeps it between builds.
nb_execution_mode = "cache"
nb_execution_cache_path = str(HERE.parent / "_build" / ".jupyter_cache")
nb_execution_raise_on_error = True
nb_execution_show_tb = True  # print a failing cell's traceback, not only the log file's path
nb_execution_timeout = 600  # per cell; uploads wait for Nominal to ingest the data
# Notebooks connect with the "default" profile; without it, they render unexecuted.
try:
    NominalConfig.from_yaml().get_profile("default")
except (FileNotFoundError, NominalConfigError):
    nb_execution_excludepatterns = ["**/*.md"]

# -- Intersphinx: references such as {py:class}`~nominal.core.Asset` link to the client's docs ----------
intersphinx_mapping = {"nominal": ("https://nominal-io.github.io/nominal-client", None)}

# -- HTML: nominal-sphinx-theme (Shibuya, styled like the other Nominal docs) ----
html_theme = "shibuya"
# Also published at dev.nominal.io/demos/: the header links back to the hub.
nominal_hub_url = "https://dev.nominal.io/"
html_title = "Nominal demos"
html_static_path = ["_static"]
html_css_files = ["nbdemo.css"]
html_copy_source = False
html_show_sourcelink = False

# The repository is private, so the public site doesn't link to it.
html_sidebars = {"**": ["sidebars/localtoc.html"]}
html_theme_options = theme_options(
    toctree_maxdepth=1,
    nav_links=[{"title": "Demos", "url": "index"}],
)
