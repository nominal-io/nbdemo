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

# lint the docs extension and nbdemo, check types, and check the formatting of notebook code | fix with `just fix`
check:
    uv run ruff check
    uv run ruff format --check
    uv run mypy
    uv run jupytext --from myst --pipe-fmt ipynb --check "ruff format --line-length 85 --check --stdin-filename notebook.ipynb -" $(grep -rl '^kernelspec:' notebooks --include='*.md')

# format the Python code and notebook code (note: mutates the notebooks)
fix:
    uv run ruff check --fix
    uv run ruff format
    uv run jupytext --from myst --pipe-fmt ipynb --pipe "ruff format --line-length 85 --stdin-filename notebook.ipynb -" $(grep -rl '^kernelspec:' notebooks --include='*.md')

# build the site into _build/html, running changed notebooks with the `default` profile; warnings fail the build
build-docs:
    rm -rf _build/html
    uv run sphinx-build -E -W --keep-going -b dirhtml -c docs notebooks _build/html

# preview the site at http://127.0.0.1:8000, rebuilding on changes
serve-docs:
    uv run sphinx-autobuild -b dirhtml -c docs notebooks _build/html --watch docs --watch src --ignore "**/.ipynb_checkpoints/**" --ignore "**/rf_radio_data/**"

# run the tests of nbdemo.data; `just test -m network` also downloads real files
test *args:
    uv run pytest "$@"

# regenerate nbdemo.data's aero/flight_dc telemetry; then update its sha256 in dataset.toml with `just hash-files`
gen-flight:
    uv run --group gen python gen/aero_flight_dc.py

# print [[files]] manifest entries for a dataset folder, such as src/nbdemo/data/aero/flight_dc
hash-files folder:
    uv run python scripts/hash_files.py "{{ folder }}"
