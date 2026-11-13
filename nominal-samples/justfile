set positional-arguments := true

default:
    @just --list

# development install with dependencies
install:
    uv sync

# run unit tests; `just test -m network` also downloads real files
test *args:
    uv run pytest "$@"

check-types:
    uv run mypy

check-format:
    uv run ruff format --check

check-imports:
    uv run ruff check

# run all static analysis checks
check: check-format check-types check-imports

fix:
    uv run ruff format
    uv run ruff check --fix

# run all tests and checks
verify: install test check

# regenerate aero/flight_dc/telemetry.csv; then update its sha256 in dataset.toml with `just hash-files`
gen-flight:
    uv run --group gen python gen/aero_flight_dc.py

# print [[files]] manifest entries for a dataset folder, such as src/nominal_samples/aero/flight_dc
hash-files folder:
    uv run python scripts/hash_files.py "{{ folder }}"

# the docs group is empty below Python 3.12
_check-docs-python:
    uv run python -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else f'The docs toolchain needs Python >= 3.12 (found {sys.version.split()[0]}). Recreate it with: uv sync --python 3.13 --group docs')"

# build the docs site into docs/_build/dirhtml, running the notebooks; warnings fail the build
build-docs: _check-docs-python
    uv run --group docs sphinx-build -E -W -n --keep-going -b dirhtml docs docs/_build/dirhtml

# live-preview the docs on http://127.0.0.1:8000
serve-docs: _check-docs-python
    uv run --group docs sphinx-autobuild -b dirhtml docs docs/_build/dirhtml --watch src --ignore docs/_build

# open the docs notebooks in JupyterLab, with .md pages opening as notebooks
notebook:
    uv run --group docs --group notebook jupyter lab docs
