Selenium Tests
==============

These are UI-level acceptance and accessibility tests designed to be run against an edx-platform sandbox instance.

The tests use the ``bok-choy`` library.  For a tutorial, see `here`__.

__ http://bok-choy.readthedocs.org/en/latest/tutorial.html


To use the tests:

1. Install the test requirements:

.. code:: bash

    cd edx-ora2
    pip install -r requirements/test-acceptance.txt


2. Prepare for tests

.. code:: bash

    cd edx-ora2/test/acceptance
    export BASE_URL=https://{USER}:{PASSWORD}@example.com

3. Run the tests

To run the acceptance tests:
    
.. code:: bash

    python tests.py

To run the accessibility tests, which must be run with phantomjs as the browser:
    
.. code:: bash

    SELENIUM_BROWSER=phantomjs python accessibility.py
