# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html),

## [Unreleased]
### Added
- Added CHANGELOG.rst with backpopulated data pulled from github releases, starting from version 1.0.0
### Changed
- Changed PR Template to include CHANGELOG updates and instructions.

## [3.6.17] - 2021-08-04
### Fixed 
- fixed a bug around rubric reuse placeholder text

## [3.6.16] - 2021-08-03
### Added
- warn icon to invalid editor tabs on save
### Changed
- re-styled studio validation banner close icon
- For better matching fields to tabs, moved assessment step schedule validation to the schedule tab.

## [3.6.15] - 2021-08-03
### Added
- UI for the Rubric Reuse feature. Found in the ORA Edit Modal, Rubric Tab. Gated behind a `openresponseassessment.rubric_reuse` waffle flag

## [3.6.14] - 2021-08-02
### Fixed 
- add sourceMap build fail for stage/prod. create helper for joining path on load static
- update unit testing

## [3.6.11] - 2021-07-23
###  Fixed
- fixed a bug with the submission zip download where we were not correctly filtering users

## [3.6.10] - 2021-07-12
### Added
- added additional logging around the ORA Submissions ZIP export

## [3.6.8] - 2021-06-25
### Fixed
- Pylint has been silently failing. Fixed that, and address missed quality errors.

## [3.6.7] - 2021-06-23
### Added
- Added js functions to clone rubrics. Given a block ID, replace current rubric with data from another rubric and clear learner training examples

## [3.6.6] - 2021-06-22
###  Fixed
- Fixed a bug where the waiting details tool would filter out valid students

## [3.6.5] - 2021-06-16
### Fixed
- Fixed a bug where the submission button takes too long to show up

## [3.6.4] - 2021-06-15
### Changed
- Changed message on alert that pops when you attempt to edit a released ORA

## [3.6.3] - 2021-06-14
### Changed
- Make submission feedback full-width

## [3.6.2] - 2021-06-08
### Fixed
- Fixed a bug where putting html within textarea made the xblock re-render escape html on another div. The change was reference to the introduction of tinymce

## [3.6.1] - 2021-06-02
### Added
- Added backend xblock functions to enable rubric reuse.
- Added get_rubric xblock json handler which returns a json representation of a given block's rubric. 
- When the rubric reuse flag is on, include a list of ORA block locations in the course to potentially pull rubrics from
- Add opaque_keys as a requirement

## [3.6.0] - 2021-06-02
### Added
- Add a new button to edit an ORA in Studio

## [3.5.5] - 2021-05-27
### Changed
- replaced javascript/scss targets with static. sass make target was removed a while ago without supporting doc updates.
This renames the javascript target (uses webpack to build both js/scss)
to make static and updates docs accordingly.

## [3.5.4] - 2021-05-26
### Fixed
- Fixed a bug where flexible peer grading would allow 0 peer grades to be considered complete

## [3.5.3] - 2021-05-26
### Added
- added openresponseassessment.enable_rubric_reuse waffle flag for rubric reuse

## [3.5.2] - 2021-05-21
### Changed
- Increased character limit for Instructor feedback on ORAs to 1k chars

## [3.5.1] - 2021-05-14
### Changed
- [BD-05][TNL-7915][BB-3611] Improve ZIP File content structure

## [3.5.0] - 2021-05-12
### Changed
- [BD-05][TNL-7946]: Waiting step details

## [3.4.2] - 2021-05-11
### Fixed
- fixed the unhandled case for archiving ghost files (files that are recorded but not found in storage) 
### Added
- Added file_found column to the csv as an indication of error files.
- Log warning on archiving invalid files

## [3.4.1] - 2021-04-07
### Changed
- Minor update to rubric styles and dependency updates

## [3.4.0] - 2021-03-10
### Changed
- [BD-05] [EDUCATOR-5478] [BB-3613] Use webpack to compile sass assets as well

## [3.3.2] - 2021-03-05
### Fixed
- [BD-05]: Add missing occurrences of pluggable editor (#1604)

## [3.3.1] - 2021-03-02
### Removed
- 3.3.1
- [BD-05][EDUCATOR-5596] Remove tinymcev5 and use the existing one from the platform 
### Added
- Add content style for tinymce.
### Fixed
- Fix multiple ora block issue.
- Fix linebreak issue

## [3.2.0] - 2021-02-25
### Added
- Added show_rubric_during_response field which, when enabled, adds a collapsable version of the rubric to the top of the Your Response section 

## [3.1.6] - 2021-02-24
### Changed
- Update filename encoding to handle more characters 

## [3.1.5] - 2021-02-24
### Fixed
- fixes ORA pluggable submission editor issues in the staff area.
JIRA tickets: https://openedx.atlassian.net/browse/EDUCATOR-5590, 5594

## [3.1.4] - 2021-02-22
### Changed
- Disallow combined upload and submit step when staging files for upload
- Update a lot of JS code to remove deprecated jQuery functions
- Remove some unnecessary JS variable bindings

## [3.1.3] - 2021-02-17
### Added
- [BD-05] [TNL-7310] [BB-3388] Pluggable ORA Submission Editor - TinyMCE
- Add Pluggable submission editor for ORA
- Add tinymce v5 for response editor

## [3.1.1] - 2021-02-05
### Fixed
- Fixed file upload to support non-ASCII file names

## [3.1.0] - 2021-02-04
### Added
- Add api for graded submissions
- API to get number of times a submission has been graded (`api/peer.py` and `workflow/models.py`)
### Changed
- Modify waffle flag (`config_mixin.py`)
- openedx.yml updates.
- edx-toggles dependency update

## [3.0.0] - 2021-01-22
### Removed
- Dropped Python 3.5 Support
### Changed
- Upgraded code to Python 3.8

## [2.13.9] - 2021-01-20
### Added
- add additional backend validation to prevent users from somehow accidentally submitting empty submissions
- add tracking log event for ORA file deletion
## Removed
- remove axios as a dependency
- remove some test data that assumed 2021 was the future

## [2.13.7] - 2020-12-17
### Added
- Add Internal API layer for Ora Submission raw_answer
- Added classes to data.py to facilitate parsing different versions of the raw_answer sent to and returned by the submissions api

## [2.13.6] - 2020-12-15
### Added 
- Add missing expand/collapse indicators to assessment steps

## [2.13.5] - 2020-12-14
### Changed
- "Log more helpful error messages for file uploads

## [2.13.3] - 2020-12-02
### Added
- TNL-7282 - Support Flexible Peer Grading Averaging for Learners delayed / in Peer Grading step

## [2.13.2] - 2020-12-02
### Fixed
- TNL-7578 - Fix bug on grade explanation

## [2.13.1] - 2020-12-01
### Changed
- TNL-7337 - Make peer dependent steps skipable

## [2.13.0] - 2020-12-01
### Added
- TNL-7577 - Studio ORA Block Selector

## [2.12.2] - 2020-12-01
### Fixed
- ORA Assessment Settings toggle controls in studio now work reliably.

## [2.12.1] - 2020-11-30
### Fixed
- Downloaded files should retain their filenames. Modified the way files were uploaded so that they retain their filenames rather than using whatever default/key the backend provides

## [2.12.0] - 2020-11-19
### Changed
- Make use of new-style waffle switch objects
- WaffleSwitch is not imported from edx-platform's `waffle_utils` (which is deprecated), but from edx-toggles, which is thus added to the base requirements. Note that CourseWaffleFlag objects remain in edx-platform.

## [2.11.6] - 2020-11-12
### Changed
- Bump cryptography from 3.1.1 to 3.2 in /requirements

## [2.11.5] - 2020-11-10
### Fixed
- Do not use waffle for activation of mobile support due to it prevents us from collecting the static assets while building docker images

## [2.11.4] - 2020-11-03
### Fixed
- Fixed webpack Upgrade
- This release includes changes from the previous yanked releases (2.11.3, 2.11.2, 2.11.1, 2.11.0) which were broken due to webpack issues

## [2.11.3] - 2020-10-29 [YANKED]
### Fixed
- The deployment to PyPi has been broken since 2.11.0 because the manifest was not updated to reflect new js files.

## [2.11.2] - 2020-10-27 [YANKED]
### Changed
- Previously, when a course's grades were frozen or when viewing a submission that had been cancelled, the staff grade override section of the staff area would be hidden, as an override could not be performed. This led to some confusion, so now rather than hiding the section, we display a message explaining why the override cannot be performed.

## [2.11.1] - 2020-10-23 [YANKED]
###Fixed
 - Fixed typo in the default point config for new ORAs. Excellent is 5 points, not 3.

## [2.11.0] - 2020-10-22
### Changed
 - Convert ORA build to Webpack

## [2.10.3] - 2020-10-22
### Fixed
- Fix a bug where the "Generate Submission Files Archive" button on the instructor dashboard wouldn't work for courses with older ORA submissions.

## [2.10.2] - 2020-10-19
### Added
- Added option to restrict learners to a single file upload

## [2.10.1] - 2020-10-16
### Added
- - Add configuration to allow mobile support to be toggled on/off
### Fixed
- Fix a bug where the "Generate Submission Files Archive" button on the instructor dashboard wouldn't work for courses with older ORA submissions.

## [2.9.18] - 2020-10-06
### Added
- Show allowed file extensions for file uploads in ORA upload section
### Ccanged
- Update error messaging for bad file type uploads

## [2.9.17] - 2020-10-06
### Added
- Show file extensions for preset upload types in ORA settings
- Show, but disable, allowed extensions for presets
- Add note about custom extensions
- Show when non-custom upload type is selected
- Populate extension lists with preset values

## [2.9.16] - 2020-10-01
### Changed
- Explicitly Set File Upload Extensions

## [2.9.15] - 2020-09-28
### Changed
- Replaced boto with boto3

## [2.9.14] - 2020-09-23
### Changed
- Requirements upgrade
- Hid a paragraph about team uploads in individual assignments
- filenames should now appear in leaderboards

## [2.9.12] - 2020-09-17
### Added
- Display team submission note for team assignments
- Remove submission tip section for team assignments

## [2.9.11] - 2020-09-15
### Changed
- JS/Python Requirements updates

## [2.9.10] - 2020-09-15
### Added
- Add message for cancelled assignment status

## [2.9.9] - 2020-09-08
### Changed
- Allow a student to see their submission even if they are not on a team
- Don't block assignment for teamless learner
- Render unavailable assignment for teamless learner
- Hide teamless message when learner has submission

## [2.9.5] - 2020-08-26
### Changed
- added a message for teammates with external submissions

## [2.9.4] - 2020-08-26
### Added
- Warn learner of submission from prev team.

## [2.9.3] - 2020-08-21
###  Changed
- Surface file upload data as dicts instead of tuples

## [2.9.2] - 2020-08-19
### Added
- Adds `collect_ora2_attachments` method, which collects all submission attachments and represents them in a way useful to create an attachments zip archive.

## [2.9.1] - 2020-08-11
### Changed
- Delete team files when resetting student state
- Remove an individual's files from submissions when clearing state

## [2.9.0] - 2020-08-11
### Added
- Two new tabs added: Schedule and Assessments Steps.
### Changed
- Assessments settings moved to Assessments Steps tab from Settings tab.
- All scheduling settings from Settings and Assessments Steps moved to Schedule tab.
- Assessment settings now have a new interface.

## [2.8.14] - 2020-08-07
### Fixed 
- Fix bug where staff area would not correctly show cancellation info
### Changed
- Change wording in ORA "Manage Teams" Instructor view under "Team's Final Grade" when Team Submission is Cancelled

## [2.8.12] - 2020-08-07
### Fixed
- Fixed bug where resetting state for a team does not allow resubmission

## [2.8.9] - 2020-07-24
### Deprecated
- Django 3.x deprecation warnings  

## [2.8.8] - 2020-07-15
### Changed 
- ORA xblock is indexable by the search engine
- Added learner messaging explaining how the grade is determined

## [2.8.6] - 2020-06-29
### Changed
- Change ORA Report to Include Problem Name and Location

## [2.8.5] - 2020-06-18
### Changed
- Update text on regrade dialog to refer to teams.
- Update text on regrade dialog to refer to use the word teams instead of learners for team based ORAs.

## [2.8.4] - 2020-06-18
### Changed
- Upgrade submissions to 3.1.11

## [2.8.3] - 2020-06-17
### Changed
- Moved xblock-sdk from base.in to test.in 

## [2.8.2] - 2020-06-15
### Changed
- Installing xblock-sdk from PyPI now

## [v2.8.1] - 2020-06-12
## Added
- Grading of Team Assignments. grade team assignments, and the grade is applied to all users on the team.
## Fixed
- fix broken clear_team_state

## [2.8.0] - 2020-06-11
### Added
- Username ORA Report Download (optionally) includes Usernames

## [v2.7.11] - 2020-06-10
### Added
- Add the ability for course staff to remove team submissions from grading

## [v2.7.10] - 2020-06-02
### Changed
- Update manage learners panel w/ team wording

## [v2.7.9] - 2020-06-02
### Added 
- Add reset_team_state in staff_mixin that is called when reset_student_state is called for a team

## [v2.7.8] - 2020-05-29
### Fixed 
- fix how sumbission uuids are looked up

## [2.7.7] - 2020-05-27
### Fixed
- A few minor fixes to the submission logic.

## [2.7.6] - 2020-05-20
### Changed
- Team management updates

## [v2.7.3] - 2020-05-13
### Added
- Added Python3.8 support

## [v2.7.2] - 2020-05-12
### Changed
- Team assessment wording

## [v2.6.30] - 2020-04-29
### Added
- Added Team Assessment API

## [v2.6.29] - 2020-04-10
### Added
- Add Team Workflow Deletions to Teams API

## [v2.6.26] - 2020-04-09
### Added 
- Create Team Assessment Workflow API

## [2.6.25] - 2020-04-01
### Changed
- Django2: upgrade django-model-utils

## [2.6.24] - 2020-04-01
### Changed
- bump submissions to 3.0.6

## [2.6.23] - 2020-03-31
### Fixed
- Error loading peer reviews in ORA
- Address DeprecationWarning of xblock.fragment

## [2.6.22] - 2020-03-30
### Added
- Added TeamStaffWorkflow and TeamAssessmentWorkflow models
- Added TeamStaffWorkflow and TeamAssessmentWorkflow models to support instructor grading experience.
- Jira for reference: https://openedx.atlassian.net/browse/EDUCATOR-4979

## [2.6.21] - 2020-03-23
### Changed
- Implements #1376 - reverts a CSS change from release 2.6.19

## [v2.6.20] - 2020-03-23
### Changed
- Store correct assessment type for team assignments
- Hide invalid assessments on load in ORA settings
- Only save assessment types that are visible
- Automatically select Staff Assessment for Team ORA

## [2.6.19] - 2020-03-12
### Changed 
- Update ORA xBlock with WCAG 2.1 compliance color contrast for radio buttons.

## [2.6.18] - 2020-03-09
### Changed
- Change WaffleMixin -> ConfigMixin

## [2.6.17] - 2020-03-04
### Changed
- `logger.exception()` -> `logger.warning()` when there isn't actually an exception.

## [2.6.16] - 2020-03-03
### Changed
- Implements https://openedx.atlassian.net/browse/OSPR-2534

## [2.6.15] - 2020-02-28
### Changed
- ORA xBlock color contrast update (WCAG 2.1)

## [2.6.12] - 2020-02-19
### Fixed
- Fixed a bug where get_download_urls_from_submission would break after finding one missing uploaded file. It should continue and download all available files.

## [2.6.11] - 2020-02-19
### Fixed
- The oa_response_submitted template should include team file URLs in its context

## [2.6.10] - 2020-02-18
### Fixed
- Fixed a bug where submitting a team assignment wouldn't submit files uplaoded by the learner clicking the submit button

## [2.6.9] - 2020-02-10
### Changed
- Replaced jsonfield with jsonfield2

## [2.6.8] - 2020-02-04
### Added
- Display file owner username on shared team uploads

## [2.6.7] - 2020-01-31
### Fixed
- Fixes root cause of https://openedx.atlassian.net/browse/EDUCATOR-4896
- Implements https://openedx.atlassian.net/browse/EDUCATOR-4810

## [2.6.5] - 2020-01-28
### Changed
 - Update some of the workaround submission methods

## [2.6.4] - 2020-01-28
### Changed 
- Control when learners can delete files as members of a team

## [2.6.2] - 2020-01-16
### Changed
- Use teamset id rather than name in most places as a reference
- Lookup team by teamset rather than just assuming the user is on one team
### Fixed
- Fixed bug where deleted files weren't included in template so indexing was off

## [2.6.0] - 2020-01-13
### Added
- Staff only workaround to display all uploaded files by a learner
- Adding a staff-only workaround to see all the uploaded files by a learner in an ORA block, except for the deleted files. See https://github.com/edx/edx-ora2/pull/1337 for more context

## [2.5.9] - 2020-01-12
### Fixed
- Fixes https://openedx.atlassian.net/browse/EDUCATOR-4864

## [2.5.8] - 2020-01-06
### Added
- Display teamset names, allowing a user to choose from configured teamset names.

## [2.5.6] - 2020-01-03
### Fixed
- Fixed Filename rendering issue in student info

## [2.5.4] - 2019-12-31
### Added
- add logs for diagnostic

## [2.5.3] - 2019-12-18
### Fixed
- Fix studio view bug in python 3.

## [2.5.2] - 2019-12-18
### Added
- Pulls teams information from an XBlock Teams services. 
- Aims to make publishing PyPI releases via travis a reality.

## [2.5.0] - 2019-12-13
### Added
- File upload from user state alternative
- There have been various instances in ora submissions where the learner uploaded the file but it wasn't visible to peers or staff members while grading. The upload information wasn't present in submission, but it was present in the user state. This release is bringing in the data from the user state to show the file upload information to **staff members** to help assess the user's response. The workaround is behind a waffle switch/course override.

## [2.4.7] - 2019-12-03
### Changed
- ran make upgrade on repo
- Changed install_requires to requirements/base.in
- Adding .in requirement files to Manifiest.in
- Added Django req to dependencies in tox js environment

## [2.4.6] - 2019-12-03
### Changed
- Logs Update
- Some FileUploadError logs have been updated/added to get proper information for the cases where the file information is missing in the user submission.

## [2.4.5] - 2019-12-02
### Changed
- Switch to using Pytest instead of nose to run unit tests.

## [2.4.4] - 2019-11-26
### Changed
- Bump version for prep for PyPI package

## [2.4.3] - 2019-11-25
### Changed
- Refactor python-side handling of file uploads: https://github.com/edx/edx-ora2/pull/1293

## [2.4.2] - 2019-11-22
### Fixed
- This release focuses on dumping the student's answer in ORA data collection to ensure special/Unicode characters are rendered perfectly in the CSV.

## [2.4.1] - 2019-11-21
### Changed
- bump edx-submissions requirement version

## [2.4.0] - 2019-11-15
### Changed
- Generally improves file management from a learner's perspective:
- Existing files are no longer deleted before uploading a new batch of files.
- Allow for the deletion of individual files.
- Allow for much larger (<= 500MB) files to be uploaded.

Related PRs:
- https://github.com/edx/edx-ora2/pull/1290
- https://github.com/edx/edx-ora2/pull/1289
- https://github.com/edx/edx-ora2/pull/1286
- https://github.com/edx/edx-ora2/pull/1282
- https://github.com/edx/edx-ora2/pull/1279
- https://github.com/edx/edx-ora2/pull/1294

## [2.3.8] - 2019-11-05
### Changed
- Allow for `teams_enabled` key when updating editing context.

## [2.3.7] - 2019-11-01
### Changed
- More loosely depend on lxml.

## [2.3.6] - 2019-11-01
### Changed
- Minor changes to migration files to make them compatible with python 3

## [2.3.5] - 2019-10-31
### Added
- Adds a `WaffleMixin` class to the `OpenAssessmentBlock`.
- Add setting to enable teams in ORA XBlock, gated by a course-specific waffle flag.

## [2.3.3] - 2019-10-29
### Added
- In learner responses, displays the original file name (from the learner's system) along with uploaded file descriptions.
### Fixed
- Fixes edge-cases that allow for the upload/submission of files/responses before all requirements are met.

## [2.3.2] - 2019-10-13
### Changed
- Fixed python3 compatibility issues.
- Fixed python3 compatibility issues.

## [2.3.1] - 2019-09-10
### Fixed
- Fixes previous release, which did not regenerate the required minified JavaScript files.

## [2.3.0] - 2019-09-09
### Changed
- Increases assignment upload limit in JavaScript from 10MB to 20MB.

## [2.2.7] - 2019-08-22
### Changed
- Updated Requirements to use latest version of edx-submissions

## [2.2.6] - 2019-07-24
### Changed
- Python 3 Support
- Python 3 Support

## [2.2.5] - 2019-07-08
### Changed
- File upload failure information logs added
- A few instances have been observed where the ORA uploads' were missing file submissions and the evidence suggesting the file upload has taken place was not substantial. Some logs have been added that provide some useful information if such a case happens in the future.

## [2.2.3] - 2019-04-10
### Fixed
- Fix staff override

## [2.2.1] - 2019-01-10
### Changed
- "Merge pull request #1218 from edx/diana/update-version

## [2.1.18] - 2018-07-04
### Changed
- Updated i18n-tools version

## [2.1.17] - 2018-06-06
### Changed
- i18n update
- Addresses [EDUCATOR-2685](https://openedx.atlassian.net/browse/EDUCATOR-2685) in particular

## [2.1.16] - 2018-05-01
### Changed
- Bump version of edx-i18n-tools to 0.4.5.

## [2.1.15] - 2018-04-12
### Fixed
- Fix issue with Rich Text Prompt (Educator-2634)

## [2.1.14] - 2018-04-05
### Fixed
- Fix issues with linkifiying submissions: EDUCATOR-2634

## [2.1.13] - 2018-03-27
### Added
- Add support for wysiwyg prompt editing and style cleanup

## [2.1.11] - 2018-01-30
### Fixed
- Fixes an issue with missing minified js changes

## [2.1.10] - 2018-01-25
### Changed
- Merge pull request #1073 from edx/efischer/group_access_export

## [2.1.9] - 2018-01-23
### Changed
- Fix allow_file_upload default value

## [2.1.8] - 2017-12-11
### Changed
- Shore up the previous release.

## [2.1.7] - 2017-12-08
### Changed
- Be defensive about serializing training examples.

## [2.1.6] - 2017-12-06
### Changed
- a11y and button changes related to https://openedx.atlassian.net/browse/EDUCATOR-1547

## [2.1.5] - 2017-12-05
### Fixed
- Fix: https://github.com/edx/edx-ora2/pull/1061

## [2.1.2] - 2017-10-02
### Changed
- version 2.1.2

## [2.1.0] - 2017-09-05
### Changed 
- Follow up to 2.0.6, with proper translation updates.

## [2.0.6] - 2017-09-05
### Changed
 - internal version 2.0.6

## [2.0.5] - 2017-09-05
### Changed 
- Patch release, to be immediately followed by 2.0.6 (which will include i18n updates)

## [2.0.2] - 2017-08-15
### Changed
- Update edx-submissions, allow django-model-utils 3.0+

## [2.0.1] - 2017-08-11
### Changed
- Finishes the 2.0.0 upgrade work, and restores edx-submissions to a stable state after the uuid events of EDUCATOR-1090

## [1.4.11] - 2017-08-05
###  Changed
- 1.4.11 patch release

## [1.4.10] - 2017-08-04
### Changed
- Patch release for EDUCATOR-1090

## [2.0.0] - 2017-08-03
### Removed
- AI grading has been removed
### Changed
- the entire package has been updated to be used in a more modern way than before
- Dependencies have also been updated to make this repo more future-proof.

## [1.4.9] - 2017-08-02
### Changed
- Minor release to bump edx-submissions version

## [1.4.7] - 2017-07-20
### Changed
- Patch release to assist with LEARNER-1977

## [1.4.6] - 2017-07-14
### Changed
- Ginkgo release

## [1.4.4] - 2017-07-06
### Changed
- Merge pull request #1020 from edx/rc/1.4.4

## [1.4.3] - 2017-06-21
### Changed
- Merge pull request #1013 from edx/rc/1.4.3

## [1.4.2] - 2017-06-12
### Changed
- Merge pull request #1011 from edx/efischer/rc

## [1.4.1] - 2017-06-02
### Fixed
- Contains fixes for file extension casing, several instructor dashboard improvements, and a breaking acceptance test change.

## [1.4.0] - 2017-04-28
### Changed
- Bumping minor version for addition of multiple file uploads functionality

## [1.3.3] - 2017-04-03
### Changed
- Merge pull request #998 from edx/rc/1.3.3

## [1.3.2] - 2017-03-30
### 
- Merge pull request #995 from edx/rc/1.3.2

## [1.3.1] - 2017-03-23
### Changed
- docstring updates
- devstack installation updates for Ficus

## [1.3.0] - 2017-03-21
### Added
- New OraAggregateData.collect_ora2_responses method
- New auxiliary view "grade_available_responses_view
- support for Swift file upload backend
### Changed
- pylint threshold lowered

## [1.2.2] - 2017-02-24
### Changed
- Criterion Names are poorly defined

## [1.2.1] - 2017-02-14
### Fixed
- Fix naive datetime strings bug related to dateutils. Fix broken acceptance tests and edx-platform version matching for requirements.

## [1.2.0] - 2017-01-27
### Added
- Implement edx-ui toolkit dateutils. 
### Changed
- Accessibility screen reader feedback improvements. Dependency upgrades.


## [1.1.13] - 2016-12-19
### Changed
- Updates for accessibility including header structure and bug fix for peer review grades.


## [1.1.12] - 2016-12-07
### Changed
- Release candidate 1.1.12

## [1.1.10] - 2016-11-15
### Changed
- This release primarily contains changes to ORA colors for accessibility (ensuring that text meets color contrast requirements).

## [1.1.9] - 2016-10-11
### Changed 
- Updating with a slight feature change as requested by product, and your regularly scheduled translation updates.

## [1.1.8] - 2016-08-25
### Changed
- Pushing out a transifex update

## [1.1.7] - 2016-08-09
### Fixed
- Accessibility fixes

## [1.1.6] - 2016-07-20
### Fixed
- Fixes a breaking bug in requirements, and includes time zone updates.

## [1.1.5] - 2016-06-06
### Fixed
- Fixes static asset handling for running in devstack.

## [1.1.4] - 2016-04-21
### Fixed
- Includes a bugfixes for TNL-4155, TNL-4352, tests and cleanup for TNL-4351.

## [1.1.3] - 2016-04-07
### Fixed
- Includes a bugfix for TNL-4351

## [1.1.2] - 2016-04-06
### Fixed
- Fix a bug in ORA transaction management.

## [1.1.1] - 2016-03-22
### Fixed
- Fixes release state of an ORA component

## [1.1.0] - 2016-03-10
### Added
- Adding data download functionality

## [1.0.1] - 2016-03-07
### Fixed
- CSS fixes to patch edx-platform RC

## [1.0.0] - 2016-02-26
### 
- 1.0.0 Release
- After some discussion amongst the team, we've realized that ora2 is quite stable, has been in production for some time, and should really be at version 1.0.0, instead of pre-release 0.2.X versions.

This point in time is being declared as an arbitrary "released version" state.