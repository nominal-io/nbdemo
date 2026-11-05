# Running the notebooks

Each demo is a MyST Markdown notebook in the [nbdemo](https://github.com/nominal-io/nbdemo)
repository. To run one, clone the repository, then install its dependencies with
[uv](https://docs.astral.sh/uv/) and [just](https://just.systems):

```shell
git clone git@github.com:nominal-io/nbdemo.git
cd nbdemo
just install
just notebook
```

`just notebook` opens the notebooks in JupyterLab, where `.md` files open as notebooks.

The notebooks need a `default` [profile](https://nominal-io.github.io/nominal-client/guides/api-keys-setup/)
for the [Nominal Python Client](https://nominal-io.github.io/nominal-client/).
They create resources in that profile's workspace.

## Without uv and just

To open a notebook in your own environment, install JupyterLab and
[Jupytext](https://jupytext.readthedocs.io), plus the packages the notebook imports:

```shell
pip install jupyterlab jupytext
```

Then open the notebook in JupyterLab with **Open With → Jupytext Notebook**.
