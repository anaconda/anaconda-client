define HELP

Commands:
  help                print this help text
  init                initialize development environment
  lint                run all linters for the project (see: lint-bandit, lint-mypy)
  lint-bandit         check source code for common security issues
  lint-mypy           perform static type check of the project
  test                run all automated tests (see: test-pytest, test-autotest)
  test-pytest         run all pytest tests
  test-autotest       run autotest against production server
  build-wheel         build the standard python wheel and sdist
  build-conda         build the conda package
  install-hooks       install pre-commit hooks
  pre-commit          run pre-commit across all files

endef
export HELP

# Conda-related paths
conda_env_dir ?= ./env

# Command aliases
CONDA_EXE ?= conda
CONDA_RUN := $(CONDA_EXE) run --prefix $(conda_env_dir) --no-capture-output

.PHONY: help init lint lint-bandit lint-mypy test test-pytest build-wheel build-conda install-hooks pre-commit

help:
	@echo "$${HELP}"

init:
	@if [ -z "$${CONDA_SHLVL:+x}" ]; then echo "Conda is not installed." && exit 1; fi
	@conda create \
		--channel defaults \
		--channel anaconda-cloud \
		--yes \
		--prefix $(conda_env_dir) \
		python=3.11 \
		pip \
		--file requirements.txt \
		--file requirements-extra.txt
	@conda run \
		--prefix $(conda_env_dir) \
		pip install -r requirements-dev.txt
	@conda run \
		--prefix $(conda_env_dir) \
		pip install -e . --no-deps
	@echo "\n\nConda environment has been created. To activate run \"conda activate $(conda_env_dir)\"."

check: lint test

lint:  lint-mypy lint-bandit

lint-bandit:
	@bandit -s B113 -qr binstar_client
	@bandit -s B101,B113 -qr tests

lint-mypy:
	@mypy binstar_client tests

test: test-pytest test-autotest

test-pytest: .coveragerc
	@pytest tests/

test-autotest:
	@cd autotest && bash -e autotest.sh

build-wheel:
	@python -m build

build-conda:
	VERSION=`hatch version` conda build -c defaults -c conda-forge --override-channels conda.recipe --output-folder ./conda-bld

install-hooks:
	pre-commit install-hooks

pre-commit:
	@if ! which pre-commit >/dev/null; then \
		echo "Install pre-commit via brew/conda"; \
		echo "  e.g. 'brew install pre-commit'"; \
		exit 1; \
	fi
	pre-commit run --verbose --show-diff-on-failure --color=always --all-files

.coveragerc:
	@python scripts/refresh_coveragerc.py
