define HELP

Commands:
  help                print this help text
  setup_conda         setup_conda
  setup_dev_requirements  install additional dev requirements
  lint                run all linters for the project (see: lint-bandit, lint-mypy, lint-pycodestyle, lint-pylint)
  lint-bandit         check source code for common security issues
  lint-mypy           perform static type check of the project
  lint-pycodestyle    check source code for PEP8 compliance
  lint-pylint         perform static code analysis for common issues

endef
export HELP

.PHONY: help setup_conda setup_dev_requirements lint lint-bandit lint-mypy lint-pycodestyle lint-pylint


setup_conda:
	@if [ -z "$${CONDA_SHLVL:+x}" ]; then echo "Conda is not installed." && exit 1; fi
	@conda create -y -n anaconda_client python=3.8
	@conda install -y -n anaconda_client --file requirements.txt
	@echo "\n\nConda environment has been created. To activate run \"conda activate anaconda_client\"."

setup_dev_requirements:
	@conda install -y -n anaconda_client --file requirements-dev.txt
	@pip install -r requirements-pip.txt

help:
	@echo "$${HELP}"

lint: lint-pycodestyle lint-pylint lint-mypy lint-bandit

lint-bandit:
	@bandit -qr binstar_client

lint-mypy:
	@mypy binstar_client

lint-pycodestyle:
	@pycodestyle binstar_client

lint-pylint:
	@pylint binstar_client