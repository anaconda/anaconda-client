cd %RECIPE_DIR%\..
%PYTHON% setup.py install --old-and-unmanageable
if errorlevel 1 exit 1

del %SCRIPTS%\binstar.exe
