# Change Review and Release Process

Before Merging a pull request:

- [ ] If any user-facing text has changed, run `make check_translations_up_to_date` to recompile translation files
- [ ] If your changes include JS/CSS changes, run `make static` to rebuild static assets
- [ ] Get a green Travis build for this PR
- [ ] Address PR comments
- [ ] Get approving review from code owner
- [ ] Add a description of the change in the Unreleased section of the Changelog. Group changes by type - Added, Changed, Fixed, Removed, Deprecated, and Security.

If the pull request is being released immediately:

- [ ] Bump version number in [setup.py](../setup.py) and [package.json](../package.json) following [semantic versioning](https://semver.org/) conventions
- [ ] Move all changes from the Unreleased section of the Changelog into a new section directly beneath Unreleased, with the new version number and the current date.  

## Publish to PyPi

To create a new release, do the following to publish a new version of ORA:

- [ ] Merge the PR which bumps the version number and updates the Changelog to `master`
- [ ] Create a [release tag on GitHub](https://github.com/edx/edx-ora2/releases) matching version number in setup.py/package.json. Copy the contents of the release's changelog section into the body of the release.
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
