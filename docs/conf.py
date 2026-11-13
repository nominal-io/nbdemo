"""Sphinx config for the Nominal demo notebooks site."""

import os
import sys
from pathlib import Path

from nominal.config import NominalConfig
from nominal.exceptions import NominalConfigError
from nominal_sphinx_theme import intersphinx, theme_options

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "_ext"))

project = "Notebook Demos"
copyright = "Nominal, Inc."

extensions = [
    "myst_nb",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
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
# Size each diagram to its content, not to a fixed 500px.
mermaid_height = "auto"

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
    # The pages under reference/ need no profile, so they always run.
    nb_execution_excludepatterns = [
        str(path.relative_to(HERE.parent / "notebooks"))
        for path in (HERE.parent / "notebooks").rglob("*.md")
        if "reference" not in path.relative_to(HERE.parent / "notebooks").parts
    ]

# Run the notebooks in this environment's kernel. A `python3` kernel in the user's own Jupyter folder would
# otherwise win, and it can point at another project's environment.
os.environ["JUPYTER_PATH"] = str(Path(sys.prefix) / "share" / "jupyter")
# The reference pages download into a folder of their own, so a build never depends on what is cached.
os.environ["NBDEMO_CACHE"] = str(HERE.parent / "_build" / "samples-cache")

# -- Autodoc: the nbdemo.data reference pages, written from its docstrings ----------------
autodoc_member_order = "bysource"
autodoc_preserve_defaults = True
python_use_unqualified_type_names = True
add_module_names = False
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_use_rtype = False

# -- Intersphinx: references such as {py:class}`~nominal.core.Asset`, and the names in code cells
# (through the theme's sphinx-codeautolink), link to the client's and instro's docs ----------
intersphinx_mapping = {
    **intersphinx("nominal", "instro"),
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs", None),
}

# -- HTML: nominal-sphinx-theme (Shibuya, styled like the other Nominal docs) ----
html_theme = "shibuya"
# Also published at dev.nominal.io/demos/: the header links back to the hub.
nominal_hub_url = "https://dev.nominal.io/"
html_title = "Notebook Demos"
html_static_path = ["_static"]
html_css_files = ["nbdemo.css"]
html_copy_source = False
html_show_sourcelink = False

# The repository is private, so the public site doesn't link to it.
html_sidebars = {"**": ["sidebars/localtoc.html"]}
html_theme_options = theme_options(
    toctree_maxdepth=1,
    nav_links=[
        {"title": "Demos", "url": "index"},
        {"title": "Reference", "url": "reference/index"},
    ],
)
