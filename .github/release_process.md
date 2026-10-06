# Change Review and Release Process

Before Merging a pull request:

- [ ] If any user-facing text has changed, run `make check_translations_up_to_date` to recompile translation files
- [ ] If your changes include JS/CSS changes, run `make static` to rebuild static assets
- [ ] Get a green CI build for this PR
- [ ] Address PR comments
- [ ] Get approving review from code owner
- [ ] Use a [Conventional Commits](https://www.conventionalcommits.org/) commit message (checked by the `commitlint` workflow) so [python-semantic-release](https://python-semantic-release.readthedocs.io/) can determine the next version automatically — there is no version number to bump by hand

## Publish to PyPi

Publishing happens automatically; there's nothing to do by hand:

- [ ] Merge to `master`
- [ ] The [Semantic Release workflow](workflows/release.yml) re-runs CI, and if it passes, python-semantic-release inspects the commit messages since the last release to compute the next version, creates the git tag and GitHub release, and builds the distributions
- [ ] The workflow's `publish_to_pypi` job uploads those distributions to PyPI
- [ ] Confirm the new version appears in [PyPi: ora2](https://pypi.org/project/ora2)

## Release to Production

For non time-critical changes:

- [x] Dependencies in [edx-platform](https://github.com/openedx/edx-platform) are routinely updated every few days as part of a dependency update job
- [ ] Communicate/coordinate updated feature flags/configuration changes to stakeholders
- [ ] After the next update task run, monitor the updated functionality in sandboxes/production

To expedite the release process:

- [ ] Create a new PR in [edx-platform](https://github.com/openedx/edx-platform), changing ORA version in requirements files: `requirements/edx/{github.in,base.txt,development.txt,testing.txt}`
- [ ] Communicate/coordinate updated feature flags/configuration changes to stakeholders
- [ ] Follow the testing/release process for [edx-platform](https://github.com/openedx/edx-platform)
- [ ] After merging, monitor the updated functionality in sandboxes/production
