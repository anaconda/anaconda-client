define HELP

Commands:
  help                print this help text
  init                initialize development environment
  lint                run all linters for the project (see: lint-bandit, lint-mypy, lint-pycodestyle, lint-pylint)
  lint-bandit         check source code for common security issues
  lint-mypy           perform static type check of the project
  lint-pycodestyle    check source code for PEP8 compliance
  lint-pylint         perform static code analysis for common issues
  test                run all automated tests (see: test-pytest, test-autotest)
  test-pytest         run all pytest tests
  test-autotest       run autotest against production server

endef
export HELP

# Conda-related paths
conda_env_dir ?= ./env

# Command aliases
CONDA_EXE ?= conda
CONDA_RUN := $(CONDA_EXE) run --prefix $(conda_env_dir) --no-capture-output

.PHONY: help init lint lint-bandit lint-mypy lint-pycodestyle lint-pylint test test-pytest

help:
	@echo "$${HELP}"

init:
	@if [ -z "$${CONDA_SHLVL:+x}" ]; then echo "Conda is not installed." && exit 1; fi
	@conda create \
		--channel defaults \
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

lint: lint-pycodestyle lint-pylint lint-mypy lint-bandit

lint-bandit:
	@bandit -s B113 -qr binstar_client
	@bandit -s B101,B113 -qr tests

lint-mypy:
	@mypy binstar_client tests

lint-pycodestyle:
	@pycodestyle binstar_client tests

lint-pylint:
	@pylint binstar_client tests

test: test-pytest test-autotest

test-pytest: .coveragerc
	@pytest tests/

test-autotest:
	@cd autotest && bash -e autotest.sh

.coveragerc:
	@python scripts/refresh_coveragerc.py
