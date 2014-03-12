Fixtures
========

Dummy courseware, users, submissions, and assessments to make it easier to proof the UI in the LMS.

These are meant to be installed in a devstack VM.
See https://github.com/edx/configuration/wiki/edX-Developer-Stack for
detailed installation and troubleshooting instructions.

Usage
-----

1. Run the installation script.
```
cd edx-tim
./fixtures/install.sh
```
**WARNING**: This will wipe out all student and course state before installing the fixtures.

2. Start the LMS:
```
cd edx-platform
rake devstack[lms]
```

3. Log in as user "proof@example.com" with password "edx".

4. In the "Tim" course, you will find problems in each of the available states.
**NOTE**: There are currently more problems in the course than states.


Generating fixtures
-------------------

To regenerate test fixtures (perhaps after running a database migration):
```
cd edx-tim
./fixtures/dump.sh
```

This will create new JSON fixtures in edx-tim/fixtures, which you can commit
to the edx-tim repo.
