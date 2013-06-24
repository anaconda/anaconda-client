Getting Started
===============

To get started you must have: 

* Anaconda_ installed on your system 
* Git clones of the conda_ and conda recipes_ repositories
* Accounts on binstar_ and pypi_.

.. _anaconda: http://docs.continuum.io/anaconda/install.html

.. _conda: https://github.com/continuumio/conda

.. _recipes: https://github.com/ContinuumIO/conda-recipes

.. _binstar: https://binstar.org/

.. _pypi: https://pypi.python.org/pypi


Install the binstar command line client::

	$ [conda | pip] install binstar

Login::

	$ binstar login

Add the API token::

	$ binstar config

Test your login with the whoami command::

	$ binstar whoami


Building a Conda Package and Uploading to Binstar
=================================================

**Note:** *We cannot upload packages with the same name to PyPI so if you intend to follow along I recommend changing the the '1' digit in my package name with a random number*


We are going to be uploading a package with a simple 'hello world' function. To start let's make a new directory and create a setup.py file which holds the package metadata:


.. code-block:: python


	from distutils.core import setup

	    setup(
	        name='binstar_test_package1',
	  	author='xavier',
	        version='0.1.0',
	        packages=['binstar_test_package1',],
	        license='BSD',
	    )

Next we create a subdirectory with an __init__.py and hello.py file::

	$ mkdir binstar_test_package1

	$ cd binstar_test_package1

	$ touch __init__.py

Create hello.py containing:

.. code-block:: python

    def hello():
        print ("hello world")


Our directory should now look like this:

.. code-block:: python

	binstar_test_package1/
		setup.py
		binstar_test_package1/
  	           __init__.py
		    hello.py


To create a release, your source code needs to be packaged into a single archive file. This can be done with the sdist command::

	$ python setup.py sdist

This will create a dist sub-directory in your project and will wrap-up all of your project’s source code files into a distribution file, a compressed archive file in the form of:

binstar_test_package1-0.1.0.tar.gz

You now claim your new project’s name in the PyPI package directory by running::

	$ python setup.py register

Finally run::

	$ Python setup.py sdist upload

Now your package will be available on PyPI and installable through pip:


Check out http://pypi.python.org/pypi/<projectname> to see your upload.

My version is on: https://pypi.python.org/pypi/binstar_test_package1


Navigate to the conda-recipes repo and run::

	$ conda skeleton pypi binstar_test_package1

This will run a script and pull the package info from PyPi. Now cd into the newly created directory in conda-recipes, named after your package::

	$ cd binstar_test_package1

	$ conda build .

You have just built a conda package. The final step is uploading to binstar by copying and pasting the last line of the print out after running ```conda build .``` 

You will see a print out of your package name in the form of 'binstar upload path/to/binstar_test_package1'. My command is::

	$ binstar upload /home/xavier/anaconda/conda-bld/linux-64/binstar_test_package1-0.1.0-py27_0.tar.bz2

Since it is your first time creating a package and release you will have to fill out some text fields which could alternatively be done through the web app.

You have know created a package and uploaded it to conda, PyPI, and binstar. Check out your packages on 'https://binstar.org/<username>/<package_name>'
