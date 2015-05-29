Uploading a Pypi Package to Binstar
=================================================

Converting a PyPI package into a Conda package and uploading to Binstar is a very simple process. All you need is the Conda_ tool and the PyPI url of your package.

.. _Conda: http://docs.continuum.io/conda/intro.html

If you would like to follow along use my demonstration package located at: https://pypi.python.org/pypi/binstar_test_package1

The first step is to run::

	$ conda skeleton pypi binstar_test_package1

This will run a script to pull the package information from the PyPi repo and create a new directory containing the bld.bat, build.sh, meta.yaml files.

Cd into the new package and build a Conda package::

	$ cd binstar_test_package1

	$ conda build .

The final step is uploading to binstar by copying and pasting the last line of the print out after running ``conda build .``.

On my machine the command is::

	$ binstar upload /home/xavier/anaconda/conda-bld/linux-64/binstar_test_package1-0.1.0-py27_0.tar.bz2

After seeing ``done`` you have successfully converted a PyPI package (already on binstar) to a Conda package
and then uploaded the Conda package to Binstar.  See your packages on 'https://anaconda.org/<username>/<package_name>'
