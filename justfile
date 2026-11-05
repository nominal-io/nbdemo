set positional-arguments := true

# list the available commands
default:
    @just --list

# install the notebooks' dependencies, JupyterLab, Jupytext and the docs tools
install:
    uv sync
    @just _jupyterlab-settings

# make this environment's JupyterLab open .md files as notebooks
_jupyterlab-settings:
    mkdir -p .venv/share/jupyter/lab/settings
    cp .jupyter/overrides.json .venv/share/jupyter/lab/settings/overrides.json

# open the notebooks in JupyterLab, where .md files open as notebooks
notebook *args: _jupyterlab-settings
    uv run jupyter lab notebooks "$@"

# lint the docs extension, and check the formatting of notebook code | fix with `just fix`
check:
    uv run ruff check docs
    uv run ruff format --check docs
    uv run jupytext --from myst --pipe-fmt ipynb --check "ruff format --line-length 85 --check --stdin-filename notebook.ipynb -" $(grep -rl '^kernelspec:' notebooks --include='*.md')

# format the docs extension and notebook code (note: mutates the notebooks)
fix:
    uv run ruff check --fix docs
    uv run ruff format docs
    uv run jupytext --from myst --pipe-fmt ipynb --pipe "ruff format --line-length 85 --stdin-filename notebook.ipynb -" $(grep -rl '^kernelspec:' notebooks --include='*.md')

# build the site into _build/html, running changed notebooks with the `default` profile; warnings fail the build
build-docs:
    rm -rf _build/html
    uv run sphinx-build -E -W --keep-going -b dirhtml -c docs notebooks _build/html

# preview the site at http://127.0.0.1:8000, rebuilding on changes
serve-docs:
    uv run sphinx-autobuild -b dirhtml -c docs notebooks _build/html --watch docs --ignore "**/.ipynb_checkpoints/**" --ignore "**/rf_radio_data/**"
