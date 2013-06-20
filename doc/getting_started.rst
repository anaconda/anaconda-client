
Getting Started
======

After creating an account on 'binstar.org<https://binstar.org/>' install the binstar command line client.

``[conda | pip] install binstar_client``

``binstar login``

Test your login with the whoami command

``binstar whoami``


Building a Conda Package and uploading to Binstar
======

In an empty directory create a setup.py file and write the metadata

```from distutils.core import setup

	setup(
  		name='binstar-test-package',
 		version='0.1.0',
 		packages=['binstar-test-package',],
 	 	license='BSD',
 	   )```

Next we create a directory and add an empty init.py file

```mkdir binstar-test-package```

```cd binstar-test-package```

```touch init.py```

This will make our directory look like this:

binstar-package/
	setup.py
	binstar-test-package/
  		init.py

```python setup.py sdist```

At this point we will upload the package to 'pypi<https://pypi.python.org/pypi>' so sign up for an account if you have not before.

To create a release, your source code needs to be packaged into a single archive file. This can be done with the sdist command:

```python setup.py sdist```

This will create a dist sub-directory in your project, and will wrap-up all of your project’s source code files into a distribution file, a compressed archive file in the form of:

binstar-test-package-0.1dev.tar.gz

Your project will have to choose a name which is not already taken on PyPI. You can then claim your new project’s name by registering the package by running the command:

```python setup.py register```

Finally run 

```python setup.py sdist bdist_wininst upload```

This will upload the finished product to PyPI. We’ll also create a bdist_wininst distribution file of our project, which will create a Windows installable file. 


Now your package will be available on pypi and installable through pip

http://pypi.python.org/pypi/<projectname>


We can now build the conda package


conda skeleton pypi binstar-test-package
conda build .