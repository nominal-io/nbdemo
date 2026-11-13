"""Sphinx config for the nominal-samples docs: guides, example notebooks and the API reference."""

import os
import sys
from pathlib import Path

from nominal_sphinx_theme import theme_options

HERE = Path(__file__).parent

project = "nominal-samples"
copyright = "Nominal, Inc."

extensions = [
    "myst_nb",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_codeautolink",
    "sphinx_design",
    "nominal_sphinx_theme",
]

exclude_patterns = ["_build", "**/.ipynb_checkpoints"]

# Single backticks in docstrings (`Dataset`) link to the named object.
default_role = "py:obj"

myst_enable_extensions = ["colon_fence", "attrs_block"]
myst_heading_anchors = 3

# Run each notebook on build; the cache (in _build) re-runs only notebooks that changed.
nb_execution_mode = "cache"
nb_execution_cache_path = str(HERE / "_build" / ".jupyter_cache")
nb_execution_raise_on_error = True
nb_execution_show_tb = True
nb_execution_timeout = 180

# Run the notebooks in this environment's kernel. A `python3` kernel in the user's own Jupyter folder would
# otherwise win, and it can point at another project's environment.
os.environ["JUPYTER_PATH"] = str(Path(sys.prefix) / "share" / "jupyter")

# Plotly figures as HTML (plotly.js from its CDN), so they stay interactive in the docs.
os.environ["PLOTLY_RENDERER"] = "notebook_connected"
# The notebooks download into a folder of their own, so a build never depends on what is cached.
os.environ["NOMINAL_SAMPLES_CACHE"] = str(HERE / "_build" / "samples-cache")

autodoc_member_order = "bysource"
autodoc_typehints = "signature"
autodoc_preserve_defaults = True
python_use_unqualified_type_names = True
add_module_names = False

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_use_rtype = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs", None),
}

codeautolink_concat_default = True  # a page's code blocks run in order, like a notebook

html_theme = "shibuya"
html_title = "nominal-samples"
html_static_path = ["_static"]
html_css_files = ["notebooks.css"]
html_copy_source = False
nominal_hub_url = "https://dev.nominal.io/"
html_sidebars = {"**": ["sidebars/localtoc.html"]}
html_theme_options = theme_options(
    github_url="https://github.com/nominal-io/nominal-samples",
    nav_socials=["github"],
    # header tabs; each tab is a folder, and the sidebar shows only its toctree
    nav_links=[
        {"title": "Guides", "url": "index"},
        {"title": "Examples", "url": "examples/index"},
        {"title": "Reference", "url": "reference/index"},
    ],
)
