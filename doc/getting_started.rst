Getting Started
======

To get started you must have the git version of 'anaconda<http://docs.continuum.io/anaconda/install.html>' and 'conda<https://github.com/continuumio/conda>' installed on your system and create accounts on 'binstar.org<https://binstar.org/>' and 'pypi<https://pypi.python.org/pypi>'.

Install the binstar command line client:

``[conda | pip] install binstar_client``

Login:

``binstar login``

Test your login with the whoami command:

``binstar whoami``


Building a Conda Package and Uploading to Binstar
======

**Note** *We can not upload packages with the same name to Pypi so if you intend to following along I recommend changing the the '1' digit in my package name with a random number*


We are going to be uploading a package with a simple 'hello world' function.

To start we make a new directory and create a setup.py file which holds all the metadata:

```from distutils.core import setup

	setup(
  		name='binstar_test_package1',
  		author='xavier',
 		version='0.1.0',
 		packages=['binstar_test_package1',],
 	 	license='BSD',
 	   )
 ```

Next we create a subdirectory with an __init__.py and hello.py file:

```mkdir test_package1```

```cd test_package1```

```touch __init__.py```

hello.py contains:

```def hello():
		print ("hello world")
```

Our directory should look like this:

binstar_package/
	setup.py
	test_package1/
  		__init__.py
  		hello.py


To create a release, your source code needs to be packaged into a single archive file. This can be done with the sdist command:

```python setup.py sdist```

This will create a dist sub-directory in your project, and will wrap-up all of your project’s source code files into a distribution file, a compressed archive file in the form of:

binstar_test_package1-0.1.0.tar.gz

You can then claim your new project’s name by registering the package by running the command:

```python setup.py register```

Finally run:

```python setup.py sdist bdist_wininst upload```

This will upload the finished product to PyPI. We’ll also have created a bdist_wininst distribution file of our project, which will create a Windows installable file. 

Now your package will be available on pypi and installable through pip:

http://pypi.python.org/pypi/<projectname>

My version is on: https://pypi.python.org/pypi/binstar_test_package1



We can now build the conda package. If do not have it get the conda-recipies repo from Github: 

```git clone https://github.com/ContinuumIO/conda-recipes```

Navigate to the conda-recipes and run:
```conda skeleton pypi binstar_test_package1``` 

Then run:

```cd binstar_test_package1```

```conda build .```

You have just built a conda package. To upload it to binstar navigate to your anaconda's conda-bld folder with your operating system. Mine would be:

```cd anaconda/conda-bld/linux64/```

You will see a print out of you package name in the form of 'binstar upload path/to/binstar_test_package1'. Copy and paste the command:

```binstar upload binstar_test_package1```

You have know created a package and uploaded it to conda, pypi, and binstar. Check out your packages on 'https://binstar.org/username/package_name'
