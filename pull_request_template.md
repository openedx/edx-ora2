## Please do the following to make sure your changes make it all the way out the door:

- [ ] Make sure your PR updates the version number in ``setup.py`` and ``package.json``
- [ ] Run ``make javascript sass`` if your changes include JS/CSS changes.
- [ ] Get a green Travis build for this PR
- [ ] Merge to master
- [ ] Create a release tag on GitHub https://github.com/edx/edx-ora2/releases
- [ ] Manually inspect diff at https://github.com/edx/edx-ora2/compare/0.x.n-1...0.x.n, email contributors
- [ ] Create PR to update `requirements/edx/{github.in,base.txt,development.txt,testing.txt}` in `edx-platform`.
- [ ] If manual testing of the changes against edx-platform is desired, create a sandbox (or use devstack).
- [ ] Get green build on the edx-platform PR, merge.
- [ ] Consider any feature flags that must be changed.
- [ ] Once your code has been released to production, try to test it there, too.
