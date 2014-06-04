Performance Tests
=================

1. Install performance test requirements:

.. code:: bash

    cd ora2
    pip install -r requirements/perf.txt

2. Import ``course.tar.gz`` into Studio:

    * Course ID: 1
    * Course Org: ora2
    * Course Run: 1

3. Enable ``auto_auth`` in the LMS feature flags:

.. code:: javascript

    {
        "FEATURES": {
            "AUTOMATIC_AUTH_FOR_TESTING": true
        }
    }

4. Log in as a staff user and schedule a training task in the Course Staff Debug of the example based assessment problem.

5. **Optional**: Increase open file limit:

.. code:: bash

    ulimit -n 2048

6. Start the Locust server, and point it at the test server.  **NOTE**: You *must* include the trailing slash in the host URL.

.. code:: bash

    cd performance
    locust --host=http://example.com/


If your server has basic auth enabled, provide credentials with environment vars:

.. code:: bash

    cd performance
    BASIC_AUTH_USER=foo BASIC_AUTH_PASSWORD=bar locust --host=http://example.com/

7. Visit the `Locust web UI <http://localhost:8089>`_ to start the test.
