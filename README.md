# nbdemo

Demo notebooks for Nominal, published to https://nominal-io.github.io/nbdemo/.

The notebooks are MyST Markdown, edited through Jupytext. Sphinx and MyST-NB run them on build
and render them with `nominal-sphinx-theme`.

## Setup

Install [uv](https://docs.astral.sh/uv/) and [just](https://just.systems), then:

```shell
just install    # dependencies, JupyterLab, Jupytext and the docs tools
just notebook   # open the notebooks in JupyterLab
```

In JupyterLab, `.md` files open as notebooks and save back to `.md`, without outputs. For plain
Markdown, use **Open With → Editor**.

The notebooks need a `default`
[profile](https://nominal-io.github.io/nominal-client/guides/api-keys-setup/).

## Layout

```text
notebooks/          site root: index.md, running.md and one .md per demo
docs/conf.py        Sphinx config
docs/_ext/          the notebook-gallery directive behind the home page cards
notebooks/reference/ the Reference tab: how the site is built, and the nbdemo.data docs
src/nbdemo/data/    the sample data module, `from nbdemo.data.rf import ...`
gen/                scripts that generate datasets, for traceability
tests/              tests of nbdemo.data
.jupyter/           makes JupyterLab open .md files as notebooks
```

## Adding a demo

1. Put the notebook in `notebooks/`. The home page and sidebar list it. To group demos, use a
   folder with an `index.md` like `notebooks/index.md`.
2. Start it with a short `#` heading, a `{.lead}` line, then a summary paragraph:

   ```markdown
   # W-band radios

   {.lead}
   Component data and a field test
   ```

   The optional front-matter `icon` key sets the card's [octicon](https://primer.style/octicons/).
   To convert an `.ipynb`: `uv run jupytext --to md:myst <notebook>.ipynb`.
3. Add its dependencies with `uv add --group notebooks <package>`.
4. Check and build:

   ```shell
   just fix          # format notebook code to 85 columns
   just build-docs   # run changed notebooks and build; warnings fail the build
   just serve-docs   # preview at http://127.0.0.1:8000
   ```

## Sample data

`nbdemo.data` holds sample datasets, grouped by domain (`aero`, `med`, `rf`). Each dataset is a file
path and, where it makes sense, its format's own Python object and a pandas DataFrame:

```python
from nbdemo.data.med import ecg_mitbih_119

ecg_mitbih_119.path  # a Path, to pass to your own loader
ecg_mitbih_119.native  # a wfdb.Record
ecg_mitbih_119.df  # a pandas.DataFrame
```

It has no dependencies of its own; install the extras for the formats you read, such as `nbdemo[med]`.
The Reference tab of the site documents it.

```shell
just test         # its tests
just gen-flight   # regenerate the simulated flight telemetry
```

## Running on build

The build runs each notebook with the `default` profile, which creates resources in its
workspace. Before creating anything, a notebook archives what its earlier executions created, as
the hidden cleanup cells do. MyST-NB caches results in `_build/.jupyter_cache` and reruns a
notebook only when its code changes. Without a `default` profile, pages show no outputs.

CI writes the profile from these settings, and keeps the cache between builds:

| Setting | Kind | Value |
| --- | --- | --- |
| `NOMINAL_DOCS_KEY` | secret | API key for the workspace |
| `NOMINAL_BASE_URL` | variable | API URL, such as `https://api.gov.nominal.io/api` |
| `NOMINAL_WORKSPACE_RID` | variable | optional workspace RID |

Each PR's **docs preview** status links to its built site. Merging to `main` publishes it.

## Unreleased dependencies

`[tool.uv.sources]` in `pyproject.toml` installs nominal-client from `main`, for the notebook
cards and diagrams, and instro from its `issue-709-docs-notebooks` branch. Once they
release, remove each entry and run `uv lock --upgrade-package <name>`.
