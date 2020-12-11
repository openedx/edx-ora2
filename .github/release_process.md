# Change Review and Release Process

Before Merging a pull request:

- [ ] If any user-facing text has changed, run `make check_translations_up_to_date` to recompile translation files
- [ ] If your changes include JS/CSS changes, run `make javascript sass` to rebuild static assets
- [ ] Get a green Travis build for this PR
- [ ] Address PR comments
- [ ] Get approving review from code owner
- [ ] Bump version number in [setup.py](../setup.py) and [package.json](../package.json) following [semantic versioning](https://semver.org/) conventionss

## Publish to PyPi

When a PR is ready to release, do the following to publish a new version of ORA:

- [ ] Merge to `master`
- [ ] Create a [release tag on GitHub](https://github.com/edx/edx-ora2/releases) matching version number in setup.py/package.json
- [ ] Grab a coffee while our automated process submits the build to PyPi
- [ ] Confirm new version appears in [PyPi: ora2](https://pypi.org/project/ora2)

## Release to Production

For non time-critical changes:

- [x] Dependencies in [edx-platform](https://github.com/edx/edx-platform) are routinely updated every few days as part of a dependency update job
- [ ] Communicate/coordinate updated feature flags/configuration changes to stakeholders
- [ ] After the next update task run, monitor the updated functionality in sandboxes/production

To expedite the release process:

- [ ] Create a new PR in [edx-platform](https://github.com/edx/edx-platform), changing ORA version in requirements files: `requirements/edx/{github.in,base.txt,development.txt,testing.txt}`
- [ ] Communicate/coordinate updated feature flags/configuration changes to stakeholders
- [ ] Follow the testing/release process for [edx-platform](https://github.com/edx/edx-platform)
- [ ] After merging, monitor the updated functionality in sandboxes/production
