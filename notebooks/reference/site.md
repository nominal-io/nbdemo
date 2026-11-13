---
jupytext:
  text_representation:
    format_name: myst
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

# How the site is built

{.lead}
Each demo is a MyST Markdown notebook. Sphinx runs the notebooks and publishes the executed pages to
GitHub Pages.

## Layout

Notebooks are the site's pages, and the rest of the repository builds, tests and supports them. This
cell lists the folders of the repository that built this page:

```{code-cell} ipython3
from pathlib import Path

root = next(p for p in Path.cwd().parents if (p / "pyproject.toml").exists())
skip = {"__pycache__", "_build", "_nominal_snippets", ".ipynb_checkpoints"}


def show(folder, depth=0, limit=2):
    for path in sorted(folder.iterdir()):
        if path.name in skip or path.name.startswith("."):
            continue
        if path.is_dir():
            print("  " * depth + path.name + "/")
            if depth < limit - 1:
                show(path, depth + 1, limit)


for name in ("docs", "notebooks", "src", "tests", "gen"):
    print(f"{name}/")
    show(root / name, 1)
```

## Notebooks

A demo is a `.md` file in `notebooks/`. It starts with front matter that marks it as a notebook, then a
`#` heading, a `{.lead}` line and the content. Code cells are `{code-cell}` blocks. JupyterLab opens
these files as notebooks, through Jupytext, and saves them back as Markdown without outputs, so a diff
shows only what changed.

A folder with an `index.md` groups pages. Its toctree lists the pages in the sidebar. The home page
shows a card for each notebook and each folder, through the `notebook-gallery` directive in
`docs/_ext/gallery.py`. This Reference tab is a folder that the gallery leaves out, because it
documents the repository rather than being a demo.

## The build

`just build-docs` runs Sphinx with the configuration in `docs/conf.py`. MyST-NB executes each notebook
and puts the outputs on the page. It keeps the results in `_build/.jupyter_cache` and runs a notebook
again only when its code changes. Warnings fail the build.

Most demos connect to Nominal with a `default` profile, and they create resources in its workspace.
Without the profile, the build skips executing those notebooks, and their pages show no outputs. The
pages in this Reference tab need no profile, so they always run.

The kernel that runs the notebooks is the one in the environment that runs the build, so a notebook sees
the packages that `uv sync` installed, including `nbdemo` itself.

The look comes from `nominal-sphinx-theme`, which gives these pages the same style as the other Nominal
docs. A change that every site should share goes in the theme, not here.

## Publishing

CI runs these steps on every push and pull request:

1. `just check` lints the Python, checks types and checks the formatting of notebook code.
2. `just test` runs the tests of `nbdemo.data`.
3. `just build-docs` builds the site.

A pull request gets a docs preview, linked from its **docs preview** status. A push to `main` deploys the
site to GitHub Pages, and the docs hub at dev.nominal.io also publishes it.

## Commands

| Command | What it does |
| --- | --- |
| `just install` | Installs the dependencies, JupyterLab, Jupytext and the docs tools |
| `just notebook` | Opens the notebooks in JupyterLab |
| `just build-docs` | Builds the site into `_build/html` |
| `just serve-docs` | Previews the site on http://127.0.0.1:8000, rebuilding on changes |
| `just check` | Lints, type-checks and checks notebook formatting |
| `just fix` | Formats the Python and notebook code |
| `just test` | Runs the tests |

The [sample data](data.md) pages describe `nbdemo.data`, which the notebooks use.
