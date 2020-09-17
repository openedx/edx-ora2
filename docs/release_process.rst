ORA2 Release Processs
=====================

.. contents::

Github Checklist
----------------
- create a PR on edx-ora2 containing the version bump. This needs to happen in  `setup.py <https://github.com/edx/edx-ora2/blob/4cc85e5a057fe8ea2d876e7c27344deb67df54d3/setup.py#L39>`_ and `package.json <https://github.com/edx/edx-ora2/blob/4cc85e5a057fe8ea2d876e7c27344deb67df54d3/package.json#L3>`_
- get a green Travis build on said PR
- merge to master
- green build on master
- create a release `tag on GitHub <https://github.com/edx/edx-ora2/releases>`_
- ORA2 is a dependency in platform. If immediate release is needed, create PR to update `requirements files` in `edx-platform`. See `PR for reference <https://github.com/edx/edx-platform/pull/24830>`_ . Otherwise, a bot will automatically update the requirements in platform.
- If manual testing of the changes against edx-platform is desired, create a sandbox.
- get green build on the edx-platform PR, merge
- manually test changes on stage

Updating translations
---------------------
If you change any text that is ultimately wrapped by ugettext (in a python, JS, or HTML file), you'll have to update translations.

Do the following inside **your docker container**, with the **virtual env activated**:


- Run make ``check_translations_up_to_date`` - this extracts and compiles translations, and checks if the resulting files are up-to-date

- Because the detect_changed_source_translations make target looks at your remote branch for determining the up-to-datedness of your files, you'll have to:

  - commit your changed translation files (git diff for a quick sanity check first)
 
  - push these changes to your remote branch
 
- The translations quality check on travis should now pass.

  - To verify that you're in a good state, you can again run ``make check_translations_up_to_date`` from your container.  It should pass.  It will also modify the POT timestamps of some files - you can discard these by doing git checkout . (this just resets your locally changed files to their remote branch state).
 
Releasing edx-submissions
-------------------------
- ensure that the release number has been bumped in setup.py

- create a corresponding release in `edx submissions on GitHub: <https://github.com/edx/edx-submissions/releases>`_

- generate a diff between the new tag and the old one

  - e.g. https://github.com/edx/edx-submissions/compare/0.1.2...0.1.3 
  - verify that only the expected changes are included 
  - ask anyone with commits to verify their changes on stage
 
- create a PR to update edx-platform to refer to the new release:

  - modify the edx-submissions line in requirements files in edx platform 
  - Once the PR has been merged, edx-submissions will release with the next edx-platform release
  - Note: this means that it should be tested on stage as with any other platform change
  
Releasing edx-ora2
------------------
- smoke test the current state of ORA on the `nightly stage of master sandbox <http://ora2.sandbox.edx.org/>`_. This sandbox is built automatically once a day by a `Jenkins job <http://jenkins.edx.org:8080/view/ora2/>`_ which is also used for running automated tests

- ensure that the release number has been bumped in setup.py

- create a corresponding release on GitHub: https://github.com/edx/edx-ora2/releases

- generate a diff between the new tag and the old one

  - e.g. https://github.com/edx/edx-ora2/compare/0.2.2...0.2.3
  - verify that only the expected changes are included
  - ask anyone with commits to verify their changes on stage
 
- create a PR to update edx-platform to refer to the new release if immediate release is needed. Otherwise an automated job will auto-update the edx-platform version around 5am EST

- Once the PR has been merged, ORA will release with the next edx-platform release
