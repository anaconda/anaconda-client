define HELP

Commands:
  help                print this help text
  init                initialize development environment
  lint                run all linters for the project (see: lint-bandit, lint-mypy, lint-pycodestyle, lint-pylint)
  lint-bandit         check source code for common security issues
  lint-mypy           perform static type check of the project
  lint-pycodestyle    check source code for PEP8 compliance
  lint-pylint         perform static code analysis for common issues
  test                run unit tests

endef
export HELP

.PHONY: help init lint lint-bandit lint-mypy lint-pycodestyle lint-pylint test

help:
	@echo "$${HELP}"

init:
	@if [ -z "$${CONDA_SHLVL:+x}" ]; then echo "Conda is not installed." && exit 1; fi
	@conda create -y -n anaconda_client python=3.8 --file requirements.txt --file requirements-extra.txt
	@conda run -n anaconda_client pip install -r requirements-dev.txt
	@echo "\n\nConda environment has been created. To activate run \"conda activate anaconda_client\"."

lint: lint-pycodestyle lint-pylint lint-mypy lint-bandit

lint-bandit:
	@bandit -qr binstar_client
	@bandit -s B101 -qr tests

lint-mypy:
	@mypy binstar_client tests

lint-pycodestyle:
	@pycodestyle binstar_client tests

lint-pylint:
	@pylint binstar_client tests

test:
	@python scripts/refresh_coveragerc.py
	@pytest tests/ -x -rw --durations 10 --cov=binstar_client --cov-report term-missing
