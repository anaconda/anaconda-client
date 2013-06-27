Getting Started
===============

To get started you must have: 

* Anaconda_ installed on your system 
* Git clone of the conda_ and `conda recipes`_ repositories
* Account on Binstar_

.. _anaconda: http://docs.continuum.io/anaconda/install.html

.. _conda: https://github.com/continuumio/conda

.. _`conda recipes`: https://github.com/ContinuumIO/conda-recipes

.. _Binstar: https://binstar.org/


If you are not using Anaconda 1.6+ install the binstar command line client::

	$ [conda | pip] install binstar

Login::

	$ binstar login

Add the API token::

	$ binstar config

Test your login with the whoami command::

	$ binstar whoami


Building a Conda Package and Uploading to Binstar
=================================================


We are going to be uploading a package with a simple 'hello world' function. To make this easy we start by getting the package repo from Github::

	$ git clone https://github.com/Ghostface-jr/Test-Package

This a small directory that looks like this:

.. code-block:: python

	package/
		setup.py
		test_package/
  	       __init__.py
		   hello.py
		   bld.bat
		   build.sh
		   meta.yaml

Setup.py is the standard file holding the metadata and hello.py has our single ``hello_world()`` function. 

The bld.bat, build.sh, and meta.yaml are scripts and metadata for the Conda package. You can read the Conda build_ page for more info on those three files and their purpose.

.. _build: http://docs.continuum.io/conda/build.html

Now we create the package by running::

	$ conda build test_package/


That is all it takes to create a conda package, the final step is uploading to binstar by copying and pasting the last line of the print out after running ```conda build test_package/``` command.

The print out should be in the form of 'binstar upload path/to/test_package'. On my system the command is::

	$ binstar upload /home/xavier/anaconda/conda-bld/linux-64/test_package-0.1.0-py27_0.tar.bz2

Since it is your first time creating a package and release you will be prompted to fill out some text fields which could alternatively be done through the web app.

You will see a ```done``` printed out and you have now just created a conda package and uploaded it to binstar. Check out your package on 'https://binstar.org/<username>/<package_name>'
