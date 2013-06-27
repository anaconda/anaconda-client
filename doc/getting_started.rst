Uploading a Conda Package
==========================

To get started you must have: 

<<<<<<< HEAD
* Anaconda_ installed on your system 
* Git clone of the conda_ and `conda recipes`_ repositories
=======
* Anaconda_ and Conda_ installed on your system 
>>>>>>> master
* Account on Binstar_

.. _Anaconda: http://docs.continuum.io/anaconda/install.html

<<<<<<< HEAD
.. _conda: https://github.com/continuumio/conda

.. _`conda recipes`: https://github.com/ContinuumIO/conda-recipes

.. _Binstar: https://binstar.org/
=======
.. _Conda: http://docs.continuum.io/conda/index.html
>>>>>>> master

.. _Binstar: https://binstar.org/

If you are not using Anaconda 1.6+ install the binstar command line client::

	$ [conda | pip] install binstar

Login::

	$ binstar login

Add the API token::

	$ binstar config

Test your login with the whoami command::

	$ binstar whoami

We are going to be uploading a package with a simple 'hello world' function. To follow along start by getting my demonstration package repo from Github::

	$ git clone https://github.com/Ghostface-jr/Test-Package

<<<<<<< HEAD
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

The bld.bat, build.sh, and meta.yaml are scripts and metadata for the Conda package. You can read the `Conda build`_ page for more info on those three files and their purpose.
=======
There are several files in the directory; setup.py is the standard python file and hello.py has our single ``hello_world()`` function. The bld.bat, build.sh, and meta.yaml are scripts and metadata for the Conda package. You can read the Conda build_ page for more info on those three files and their purpose.
>>>>>>> master

.. _`Conda build`: http://docs.continuum.io/conda/build.html

Now we create the package by running::

	$ conda build test_package/

That is all it takes to create a Conda package. 

The final step is uploading to binstar by copying and pasting the last line of the print out after running the ``conda build test_package/`` command. On my system the command is::

	$ binstar upload /home/xavier/anaconda/conda-bld/linux-64/test_package-0.1.0-py27_0.tar.bz2

Since it is your first time creating a package and release you will be prompted to fill out some text fields which could alternatively be done through the web app.

You will see a ``done`` printed out to confirm you have successfully uploaded your Conda package to Binstar. 

See the package on 'https://binstar.org/<username>/<package_name>'
