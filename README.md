# Anaconda Client

This is a command line client that provides an interface to [anaconda.org](https://anaconda.org/).

## Quickstart:

First, create an account on [anaconda.org](https://anaconda.org/), if you may still don't have one.

Then, install `anaconda-client` into your conda environment:

```bash
conda install anaconda-client
```

Log into your account:

```bash
anaconda login
```

Test your login wit the `whoami` command:

```bash
anaconda whoami
```

For a complete tutorial on building and uploading Conda packages to [anaconda.org](https://anaconda.org) visit the [documentation page](https://docs.anaconda.org/anacondaorg/).

For channel notices (conda user-facing messages), see [doc/channel_notices.md](doc/channel_notices.md).

## Local development

Setup conda environment:

```bash
make init
```

Activate development environment:

```bash
conda activate anaconda_client
```

Run anaconda-client commands:

```bash
python -m binstar_client.scripts.cli --version
```

### Pre-commit Setup in Local

Pre-commit also runs in the [GitHub workflow](.github/workflows/pre-commit.yaml) on pull requests. Installing it locally is recommended so you catch formatting and lint issues before pushing, and avoid back-and-forth commits when CI auto-fixes files. Set this up **from the development environment** (`./env`, Python 3.11) — some hooks require Python ≥ 3.10.

```bash
conda activate ./env        # Need not run if anaconda-client env is already activated
pip install pre-commit
pre-commit install          # wire git hooks to this env's Python
pre-commit install-hooks    # download hook environments
```

After `pre-commit install`, hooks run automatically on each `git commit` — you do not need to run anything extra before pushing. Optionally, `make pre-commit` runs all hooks across the entire repo (useful before opening a PR).
If commits still fail with a Python 3.9 error, the git hook was likely installed from a different environment (for example base Miniconda). Re-install from `./env`:

```bash
conda activate ./env    # Need not run if anaconda-client env is already activated
pre-commit clean
pre-commit install
pre-commit install-hooks
```
and run `git commit` to commit all changes.
