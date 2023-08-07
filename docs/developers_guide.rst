ORA2 Developer Guide
====================

.. contents::

Where is the code
-----------------
ORA is broken into two separate repositories:

- `edx-ora2 <https://github.com/openedx/edx-ora2>`_

- `edx-submissions <https://github.com/openedx/edx-submissions>`_

Using ORA with docker devstack
------------------------------
Note - "from inside the lms", means you've run ``make lms-shell`` from the devstack directory and are on a command prompt inside the lms container.

1. Clone edx-ora2 repo into ../src/ directory (relative to your 'devstack' repo location). 

2. From the src directory, run the following command to install ora2 in the lms's and studio's virtual environments:

- ``make install-local-ora``

Alternatively, one can log into either lms (``make lms-shell``) or studio (``make studio-shell``) and execute the following commands to uninstall ora2 and reinstall your local copy:

- ``pip uninstall ora2 -y; pip install -e /edx/src/edx-ora2/``

3. Now, get your edx-ora2 development environment set up: (the virtual environment MUST be named **edx-ora2**)
This must be done from inside either lms or studio docker container.

- ``cd /edx/src/edx-ora2``
- ``virtualenv edx-ora2``
- ``source edx-ora2/bin/activate``
- ``make install``
- ensure that your virtual environment is named **edx-ora2**. Using a different name will cause errors when trying to generate translations.

4. Now, in the devstack directory on your host, run:

- ``make lms-restart lms-logs``

5. That's it, you're good to go! See Makefile for all the available commands, most are fairly self-explanatory
In order to simulate a given tox environment (django18, django111, quality, js), run tox -e <env> for the env in question (after re-activating your edx-ora2 virtual environment).
Usually, you can just run the underlying make commands for quicker tests, as requirements aren't re-installed.

Working with submission dependencies
------------------------------------
ORA code also depends on edx-submissions. As a result, anytime a new version of edx-submissions is released, ORA code must be updated as follows.

For devstack:

- ``make lms-shell``   # get into docker container
- ``cd /edx/src/edx-ora2`` # goto into ora2 folder
- ``source edx-ora2/bin/activate`` # activate ora2 virtual environment
- ``pip install -U edx-submissions`` # installs latest version of submissions from pypi
- ``pip install -e /edx/src/edx-submissions`` # installs latest local version of submissions

Available make commands
-----------------------
- ``make install-local-ora`` - installs your local ORA2 code into the LMS and Studio python virtualenvs
- ``make static`` - builds static JS/SASS files for LMS and Studio
- ``make quality`` - run the JSHint quality tests
- ``make test`` - run all the tests
- ``make test`` - acceptance - run the acceptance tests
- ``make test-a11y`` - run the accessibility tests
- ``make test-js`` - run the JavaScript tests
- ``make test-js-debug`` - run the JavaScript tests in debug mode in Chrome
- ``make test-python`` - run the Python tests
- ``make test-sandbox`` - run all the sandbox tests (currently acceptance and a11y)

Making Translations
-------------------
If any changes are made to the .html files, it is necessary to re-do the translations:

- be inside the shell
- ``cd /edx/src/edx-ora2``
- ``source edx-ora2/bin/activate``
- ``make check_translations_up_to_date``

The above command will generate translations files which will have to be checked into git.

Building Static Files
---------------------
This is required if there were any JS/SCSS changes:

- from local directory (not in lms shell)
- ``npm run build``

Hot Reload Frontend Changes
---------------------------
This is required if there were any JS/SCSS changes:

- from local directory (not in lms shell)
- ``npm run start`` to start dev server
  - If there is port conflict, change PORT in ``.env.development``
- from devstack directory (not in lms shell)
- ``make lms-restart studio-restart``
  - **NOTE**: cms does not support hot reload at the moment

Running Unit Tests
------------------
ORA2 supports pytest. In order to run unit tests, do the following:

- be inside the shell
- ``cd /edx/src/edx-ora2``
- ``source edx-ora2/bin/activate``
- ``pytest <relative path to the unit test file>``

Debugging with PDB
------------------
The simplest way to debug ORA2 code is with PDB - Python's built in debugger. 
One caveat: Since ORA2 has code that executes either in studio or lms context, one must be attached to the corret shell 
in order for the breakpoints to be hit.

Debugging JavaScript
--------------------
For debugging JS in Devstack, first follow the instructions for "Hot Reload JS". This enables source maps and allows for placing breakpoints in source-mapped files from the browser dev tools.

  - Locate code by browsing to ``webpack:///./openassessment/xblock/static/js/src/``. 
    - **NOTE** The path should be within ``iframe`` for ``lms``.
    - **TIP** Use ``CTRL + P`` or ``Command + P`` to find the file through chrome dev tools.
  - breakpoints should toggle with hot-reloading.

Other Resources
---------------
`ORA user documentation <http://edx.readthedocs.org/projects/edx-partner-course-staff/en/latest/exercises_tools/open_response_assessments/index.html>`_

`ORA analytics documentation <https://edx.readthedocs.io/projects/devdata/en/latest/internal_data_formats/ora2_data.html>`_
