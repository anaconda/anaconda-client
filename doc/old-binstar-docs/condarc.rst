Binstar and .condarc
====================

The .condarc file is a user configuration file located in $HOME/.condarc.

While conda requires very little user configuration it will read minimal configuration from a .condarc file, if it is present.

The .condarc file follows the YAML_ syntax and is simple to understand.

.. _YAML: http://www.yaml.org/

Here is an example:

.. code-block:: yaml

	# This is a sample .condarc file
	# This .condarc file should be placed in $HOME/.condarc

	# conda will search *only* the channels listed here
	channels:
  	   - defaults
  	   - http://conda.anaconda.org/USER-NAME
  	   - http://conda.anaconda.org/USER-NAME-2

  	# environment locations:
  	   - ~/envs


This example shows that when searching or installing with the ``conda`` command it will first check the default conda locations and then the conda.binstar user repositories listed.


If you have already uploaded a file to anaconda.org, which can be done by following along the `Getting Started guide`_, you should now add your conda.binstar url to the .condarc file as shown above and run::

	$ conda search <test_package1>

.. _`Getting Started guide`: getting_started.rst

You will see the package name and version printed out.

To install the package run::

	$ conda install <test_package1>

The .condarc file is an excellent method for organizations to share searchable Binstar repos between developers.
