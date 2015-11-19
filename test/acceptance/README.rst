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


2. Specify your sandbox location

.. code:: bash

    export ORA_SANDBOX_URL=https://{USER}:{PASSWORD}@{SANDBOX}

3. Run the tests

To run the acceptance tests:
    
.. code:: bash

    make test-acceptance

To run the accessibility tests:
    
.. code:: bash

    make test-a11y
