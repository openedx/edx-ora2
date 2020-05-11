# Change Review and Release Process

Before Merging a pull request:

- [ ] Bump version number in [setup.py](../setup.py) and [package.json](../package.json)
- [ ] Run `make javascript sass` if your changes include JS/CSS changes
- [ ] Get a green Travis build for this PR
- [ ] Address PR comments
- [ ] Get approving review from code owners

## Publish to PyPi

When a PR is ready to release, do the following to publish a new version of ORA:

- [ ] Merge to master
- [ ] Create a [release tag on GitHub](https://github.com/edx/edx-ora2/releases) with updated version number (e.g. `v3.1.4`)
- [ ] Manually inspect diff at https://github.com/edx/edx-ora2/compare/0.x.n-1...0.x.n, email contributors
- [ ] Confirm new version appears in [PyPi: ora2](https://pypi.org/project/ora2)

## Release to Production

After a new version of ORA is published to PyPi, update [edx-platform](https://github.com/edx/edx-platform) to use new version:

- [ ] Update ORA version in [edx-platform](https://github.com/edx/edx-platform) requirements files: `requirements/edx/{github.in,base.txt,development.txt,testing.txt}`
- [ ] Open edx-platform PR and test with a sandbox or devstack.
- [ ] Get green build on the edx-platform PR, merge.
- [ ] Consider any feature flags that must be changed.
- [ ] Once your code has been released to production, try to test it there, too.
