Selenium Tests
==============

These are UI-level acceptance tests designed to be executed on an edx-platform sandbox instance.

The tests use the ``bok-choy`` library.  For a tutorial, see `here`__.

__ http://bok-choy.readthedocs.org/en/latest/tutorial.html


To use the tests:

1. Install the test requirements:

.. code:: bash

    cd edx-ora2
    make install-test


2. Run the tests

.. code:: bash

    cd edx-ora2/test/selenium
    export BASE_URL=https://{USER}:{PASSWORD}@example.com
    python tests.py