# nbdemo

Demo notebooks for the Nominal platform, published to https://nominal-io.github.io/nbdemo/.

The repository is private, but the published site is public. Check each notebook's outputs
before merging. The site build swaps the UUIDs in resource IDs for stand-ins, but everything else
in the outputs is published as is, including names, properties and data.

The site works like the [nominal-client](https://github.com/nominal-io/nominal-client) examples.
The notebooks are MyST Markdown files, edited through Jupytext. Sphinx and MyST-NB run them on
build and render them with `nominal-sphinx-theme`.

## Setup

Install [uv](https://docs.astral.sh/uv/) and [just](https://just.systems), then:

```shell
just install    # the notebooks' dependencies, JupyterLab, Jupytext and the docs tools
just notebook   # open the notebooks in JupyterLab
```

In this project's JupyterLab, `.md` files open as notebooks: `just install` sets that up from
`.jupyter/overrides.json`. Saving writes back to the `.md` file. Outputs aren't saved in the
repository. To open a file as plain Markdown, use **Open With → Editor**.

The notebooks connect to Nominal with a `default`
[profile](https://nominal-io.github.io/nominal-client/guides/api-keys-setup/).

## Layout

```text
notebooks/                 site root
  index.md                 home page: a card for each notebook
  running.md               how readers run the notebooks
  jupytext.toml            reads and saves the .md files as MyST notebooks
  rf_radio_field_test.md   W-band radio demo
  notebook_display.md      the client's notebook cards
  bench_bringup.md         bench bring-up demo, with instro
.jupyter/
  overrides.json           JupyterLab opens .md files as notebooks
docs/
  conf.py                  Sphinx config
  _ext/gallery.py          the notebook-gallery directive behind the cards
```

## Adding a demo

1. Put the notebook in `notebooks/`. The home page lists it with a card, and the sidebar lists it
   too. To group demos, put them in a folder with an `index.md` that has a `#` heading, a one-line
   summary, a `notebook-gallery` and a globbed toctree, like `notebooks/index.md`. The home page
   then shows a card for the folder.
2. Start the notebook with a short `#` heading, which becomes its card's and the sidebar's title,
   then a `{.lead}` line that says more, then a summary paragraph:

   ```markdown
   # W-band radios

   {.lead}
   Component data and a field test
   ```

   The optional front-matter `icon` key gives the card an [octicon](https://primer.style/octicons/).
   To start from an `.ipynb`, convert it with `uv run jupytext --to md:myst <notebook>.ipynb`.
3. Add the notebook's dependencies to `pyproject.toml` with `uv add <package>`.
4. Check it and build the site:

   ```shell
   just fix          # format the notebook code at 85 columns, so it fits the page
   just build-docs   # run changed notebooks and build the site; warnings fail the build
   just serve-docs   # preview at http://127.0.0.1:8000
   ```

## Running the notebooks on build

The build runs each notebook with the `default` profile, so the notebooks create resources in
that profile's workspace. A notebook should archive what its earlier runs created before creating
anything, so readers see one set of data: see the hidden cleanup cell in the RF demo. MyST-NB
caches the results in `_build/.jupyter_cache`, and runs a notebook again only when its code
changes. Without a `default` profile, the build still succeeds, but the pages show the notebooks
without outputs.

CI writes the `default` profile from repository settings, and keeps the cache between builds:

| Setting | Kind | Value |
| --- | --- | --- |
| `NOMINAL_DOCS_KEY` | secret | API key for the workspace the notebooks run in |
| `NOMINAL_BASE_URL` | variable | API URL, such as `https://api.gov.nominal.io/api` |
| `NOMINAL_WORKSPACE_RID` | variable | optional workspace RID |

Pull requests build the site, and the PR's **docs preview** status links to it, served at
`https://renderdoc.cloudflare-admins.workers.dev/nominal-io/nbdemo/pull/<number>/`.
Merging to `main` publishes it.

## The client version

The notebooks' cards come from nominal-client PR #1260, and their relationship diagrams from
PR #1272, so `pyproject.toml` installs the client from #1272's branch. Once the PR is released,
remove the `nominal` entry from `[tool.uv.sources]` and run
`uv lock --upgrade-package nominal` to switch to the PyPI release.
