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

## With an agent

Give this prompt to Claude Code, or another coding agent that can run commands, to set up a working
copy. It installs what is missing, clones the repository, installs the dependencies and checks the
setup. It does not run the demos, because they create resources in your Nominal workspace.

```text
Set up a working copy of the nbdemo notebooks on my machine.

1. Check that git, uv (https://docs.astral.sh/uv/) and just (https://just.systems) are installed.
   Install what is missing, in the way that suits my operating system, and tell me what you installed.
2. Clone git@github.com:nominal-io/nbdemo.git into the current folder. If I'm already inside a clone,
   use it. If the clone fails because of SSH access, stop and tell me. Don't change my git config or
   SSH keys.
3. In the clone, run `just install`. Fix the errors you can, and report the ones you can't.
4. Check for a Nominal profile named `default` with `uv run nom config profile list`. If it's missing,
   don't ask me to paste an API key into this chat. Tell me to create an API key in Nominal and to run
   this command in my own terminal, then wait until I say it's done:
   `uv run nom config profile add default --base-url <API URL> --token <API key>`
   Then check the profile list again.
5. Run `just test` to check that the nbdemo.data module works.
6. Don't run the demos or build the docs. They create resources in my Nominal workspace. Start
   JupyterLab with `just notebook` in the background, and give me its address.
7. Summarize what you set up, and what I need to do next.
```
