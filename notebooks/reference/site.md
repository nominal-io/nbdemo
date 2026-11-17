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
Demos are MyST Markdown notebooks. Sphinx and MyST-NB run them and publish the executed pages.

## Notebooks

- Each demo is a `.md` file in `notebooks/` with notebook front matter. Edit it in JupyterLab through
  Jupytext (`just notebook`); it saves back to Markdown without outputs.
- A folder with an `index.md` groups pages. The home page shows a card for each notebook and folder,
  through the `notebook-gallery` directive in `docs/_ext/gallery.py`.
- Add a demo's dependencies to the `notebooks` group in `pyproject.toml`.

## Build

- `just build-docs` runs Sphinx, configured in `docs/conf.py`. Warnings fail the build.
- MyST-NB executes each notebook in the project environment and caches results in
  `_build/.jupyter_cache`. A notebook reruns only when its code changes.
- Most demos need a Nominal `default` profile. Without one, those notebooks aren't run and their pages
  have no outputs. The Reference pages need no profile.
- The theme is `nominal-sphinx-theme`. Changes every Nominal site should share go there.

## Publishing

CI runs `just check`, `just test` and `just build-docs`. Pull requests get a docs preview. A push to
`main` deploys to GitHub Pages, and the docs hub at dev.nominal.io publishes the site too.

## Commands

| Command | Does |
| --- | --- |
| `just install` | Install dependencies and tools |
| `just notebook` | Open the notebooks in JupyterLab |
| `just serve-docs` | Preview at http://127.0.0.1:8000 |
| `just build-docs` | Build into `_build/html` |
| `just check` / `just fix` | Lint, type-check and format |
| `just test` | Run the tests |

The [Data](data.md) section covers `nbdemo.data`.
