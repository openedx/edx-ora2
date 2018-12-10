/**
 * Tests for OpenAssessment Student Training view.
 */
describe('OpenAssessment.StaffAreaView', function() {
    'use strict';

    var successPromise = $.Deferred(
        function(defer) { defer.resolve(); }
    ).promise();

    var failWith = function(owner, result) {
        return function() {
            return $.Deferred(function(defer) {
                defer.rejectWith(owner, [result]);
            }).promise();
        };
    };

    // Stub server that returns dummy data for the staff info view
    var StubServer = function() {
        this.studentTemplate = 'oa_student_info.html';
        this.staffAreaTemplate = 'oa_staff_area.html';
        this.staffGradeFormTemplate = 'oa_staff_grade_learners_assessment.html';
        this.staffGradeCountsTemplate = 'oa_staff_grade_learners_count_1.html';

        // Remember which fragments have been loaded
        this.fragmentsLoaded = [];

        this.mockLoadTemplate = function(template) {
            var server = this;
            return $.Deferred(function(defer) {
                var fragment = readFixtures(template);
                defer.resolveWith(server, [fragment]);
            });
        };

        // Render the template for the staff info view
        this.render = function(component) {
            var server = this;
            this.fragmentsLoaded.push(component);
            return this.mockLoadTemplate(server.staffAreaTemplate);
        };

        this.studentInfo = function() {
            return this.mockLoadTemplate(server.studentTemplate);
        };

        this.scheduleTraining = function() {
            var server = this;
            return $.Deferred(function(defer) {
                defer.resolveWith(server, [server.data]);
            }).promise();
        };

        this.rescheduleUnfinishedTasks = function() {
            var server = this;
            return $.Deferred(function(defer) {
                defer.resolveWith(server, [server.data]);
            }).promise();
        };

        this.cancelSubmission = function() {
            return successPromise;
        };

        this.staffAssess = function() {
            return successPromise;
        };

        this.staffGradeForm = function() {
            return this.mockLoadTemplate(server.staffGradeFormTemplate);
        };

        this.staffGradeCounts = function() {
            return this.mockLoadTemplate(server.staffGradeCountsTemplate);
        };

        this.data = {};
    };

    // Stubs
    var server = null;
    var runtime = {};

    /**
     * Create a staff area view.
     *
     * @param {dict} serverResponse An optional fake response from the server.
     * @param {string} staffAreaTemplate - An optional template to use.
     * @returns {OpenAssessment.StaffAreaView} The staff area view.
     */
    var createStaffArea = function(serverResponse, staffAreaTemplate) {
        if (serverResponse) {
            server.data = serverResponse;
        }
        if (staffAreaTemplate) {
            server.staffAreaTemplate = staffAreaTemplate;
        }
        var assessmentElement = $('.openassessment').get(0);
        var baseView = new OpenAssessment.BaseView(runtime, assessmentElement, server, {});
        var view = new OpenAssessment.StaffAreaView(assessmentElement, server, baseView);
        view.load();
        return view;
    };

    var createGradeAvailableResponsesView = function() {
        var assessmentElement = $('.openassessment').get(0);
        var view = new OpenAssessment.BaseView(runtime, assessmentElement, server, {});
        view.staffAreaView.installHandlers();
        return view;
    };

    /**
     * Initialize the staff area view, then check whether it makes
     * an AJAX call to populate itself.
     *
     * @param {bool} shouldCall - True if an AJAX call should be made.
     */
    var assertStaffAreaAjaxCall = function(shouldCall) {
        createStaffArea();

        // Check whether it tried to load staff area from the server
        var expectedFragments = [];
        if (shouldCall) { expectedFragments = ['staff_area']; }
        expect(server.fragmentsLoaded).toEqual(expectedFragments);
    };

    var chooseStudent = function(view, studentName) {
        var studentNameField = $('.openassessment__student_username', view.element),
            submitButton = $('.action--submit-username', view.element);
        studentNameField.val(studentName);
        submitButton.click();
    };

    var showInstructorAssessmentForm = function(staffArea) {
        $('.staff__grade__show-form', staffArea.element).click();
    };

    var fillAssessment = function($assessment, type) {
        $('#staff-'+ type+ '__assessment__rubric__question--2__feedback__', $assessment).val('Text response');
        $('.question__answers', $assessment).each(function() {
            $('input[type="radio"]', this).first().click();
        });
    };

    var getAssessment = function(staffArea, tab) {
        return $('.openassessment__' + tab + ' .wrapper--staff-assessment', staffArea.element);
    };

    var submitAssessment = function(staffArea, tab) {
        spyOn(staffArea, 'callStaffAssess').and.callThrough();
        var $submitButton = $('.action--submit', getAssessment(staffArea, tab));
        $submitButton.click();
    };

    var verifyAssessType = function(staffArea, assessType) {
        expect(staffArea.callStaffAssess).toHaveBeenCalledWith(
                jasmine.any(String), jasmine.any(Object), jasmine.any(Object), jasmine.any(Function), jasmine.any(String), assessType
        );
    };

    var verifyFocused = function (element) {
        expect(element).toEqual(element.ownerDocument.activeElement);
    };

    beforeEach(function() {
        // Create a new stub server
        server = new StubServer();
        server.renderLatex = jasmine.createSpy('renderLatex');

        // Disable animations for slideUp and slideDown.
        jQuery.fx.off = true;
    });

    describe('Initial rendering', function() {
        it('loads staff info if the page contains a course staff section', function() {
            // Load the fixture for the container page that DOES include a course staff section
            loadFixtures('oa_base_course_staff.html');
            assertStaffAreaAjaxCall(true);
        });

        it('does NOT load staff info if the page does NOT contain a course staff section', function() {
            // Load the fixture for the container page that does NOT include a course staff section
            loadFixtures('oa_base.html');
            assertStaffAreaAjaxCall(false);
        });
    });

    describe('Detects unsaved changes', function () {

        beforeEach(function() {
            loadFixtures('oa_base_course_staff.html');
        });

        afterEach(function() {
            // Disable the unsaved page warnings (if set).
            OpenAssessment.clearUnsavedChanges();
        });

        it('tracks unsubmitted assessments in multiple views', function() {
            var fullGradeStaffArea = createStaffArea({}, 'oa_staff_area_full_grading.html'),
                staffOverrideStaffArea = createStaffArea(),
                fullGradeTab = "staff-grading",
                staffOverrideTab = "staff-tools",
                $assessment;

            expect(fullGradeStaffArea.baseView.unsavedWarningEnabled()).toBe(false);
            expect(staffOverrideStaffArea.baseView.unsavedWarningEnabled()).toBe(false);

            // Create unsubmitted changes in the "full grade" form.
            showInstructorAssessmentForm(fullGradeStaffArea);
            $assessment = getAssessment(fullGradeStaffArea, fullGradeTab);
            fillAssessment($assessment, 'full-grade');

            expect(fullGradeStaffArea.baseView.unsavedWarningEnabled()).toBe(true);
            expect(staffOverrideStaffArea.baseView.unsavedWarningEnabled()).toBe(true);

            // Create unsubmitted changes in the "staff grade override" form.
            chooseStudent(staffOverrideStaffArea, 'testStudent');
            $assessment = getAssessment(staffOverrideStaffArea, staffOverrideTab);
            fillAssessment($assessment, 'override');

            expect(fullGradeStaffArea.baseView.unsavedWarningEnabled()).toBe(true);
            expect(staffOverrideStaffArea.baseView.unsavedWarningEnabled()).toBe(true);

            // Submit the full grade form.
            submitAssessment(fullGradeStaffArea, fullGradeTab);

            expect(fullGradeStaffArea.baseView.unsavedWarningEnabled()).toBe(true);
            expect(staffOverrideStaffArea.baseView.unsavedWarningEnabled()).toBe(true);

            // Submit the staff grade override form.
            submitAssessment(staffOverrideStaffArea, staffOverrideTab);

            expect(fullGradeStaffArea.baseView.unsavedWarningEnabled()).toBe(false);
            expect(staffOverrideStaffArea.baseView.unsavedWarningEnabled()).toBe(false);
        });
    });

    describe('AI training', function() {
        it('schedules training of AI classifiers', function() {
            spyOn(server, 'scheduleTraining').and.callThrough();

            // Load the fixture
            loadFixtures('oa_base.html');

            // Load the view
            var view = createStaffArea({
                'success': true,
                'workflow_uuid': 'abc123',
                'msg': 'Great success.'
            });

            // Submit the assessment
            view.scheduleTraining();

            // Expect that the assessment was sent to the server
            expect(server.scheduleTraining).toHaveBeenCalled();
        });

        it('reschedules training of AI tasks', function() {
            var view = createStaffArea({
                success: true,
                workflow_uuid: 'abc123',
                msg: 'Great success.'
            });

            spyOn(server, 'rescheduleUnfinishedTasks').and.callThrough();

            // Test the Rescheduling
            view.rescheduleUnfinishedTasks();

            // Expect that the server was instructed to reschedule Unifinished Taks
            expect(server.rescheduleUnfinishedTasks).toHaveBeenCalled();
        });

        it('reschedules training of AI tasks', function() {
            var view = createStaffArea({
                'success': false,
                'workflow_uuid': 'abc123',
                'errMsg': 'Stupendous Failure.'
            });

            spyOn(server, 'rescheduleUnfinishedTasks').and.callThrough();

            // Test the Rescheduling
            view.rescheduleUnfinishedTasks();

            // Expect that the server was instructed to reschedule Unifinished Taks
            expect(server.rescheduleUnfinishedTasks).toHaveBeenCalled();
        });
    });

    describe('Staff Toolbar', function() {
        beforeEach(function() {
            loadFixtures('oa_base_course_staff.html');
        });

        var getStaffButton = function(view, buttonName) {
            var $staffButton = $('.button-' + buttonName, view.element);
            expect($staffButton.length).toBe(1);
            return $staffButton;
        };

        var getVisibleStaffPanels = function(view) {
            return $('.wrapper--ui-staff:visible, view.element');
        };

        var verifyStaffButtonBehavior = function(view, buttonName) {
            var $staffInfoButton = getStaffButton(view, buttonName),
                $visiblePanels;
            expect($staffInfoButton).not.toHaveClass('is--active');
            expect($staffInfoButton).toHaveAttr('aria-expanded', 'false');
            $staffInfoButton[0].click();
            expect($staffInfoButton).toHaveClass('is--active');
            expect($staffInfoButton).toHaveAttr('aria-expanded', 'true');
            $visiblePanels = getVisibleStaffPanels(view);
            expect($visiblePanels.length).toBe(1);
            expect($visiblePanels.first()).toHaveClass('wrapper--' + buttonName);

            var closeButton = $('.ui-staff_close_button', $visiblePanels.first())[0];
            verifyFocused(closeButton);
        };

        it('shows the correct buttons when full grading is not enabled', function() {
            var view = createStaffArea(),
                $buttons = $('.ui-staff__button', view.element);
            expect($buttons.length).toBe(2);
            expect($buttons).toHaveAttr('aria-expanded', 'false');
            expect($($buttons[0]).text().trim()).toEqual('Manage Individual Learners');
            expect($($buttons[1]).text().trim()).toEqual('View Assignment Statistics');
        });

        it('shows the correct buttons for full grading', function() {
            var view = createStaffArea({}, 'oa_staff_area_full_grading.html'),
                $buttons = $('.ui-staff__button', view.element);
            expect($buttons.length).toBe(3);
            expect($buttons).toHaveAttr('aria-expanded', 'false');
            expect($($buttons[0]).text().trim()).toEqual('Manage Individual Learners');
            expect($($buttons[1]).text().trim()).toEqual('View Assignment Statistics');
            expect($($buttons[2]).text().trim()).toEqual('Grade Available Responses');
        });

        it('shows the "Manage Individual Learners" panel when the button is clicked', function() {
            var view = createStaffArea();
            verifyStaffButtonBehavior(view, 'staff-tools');
        });

        it('shows the "View Assignment Statistics" panel when the button is clicked', function() {
            var view = createStaffArea();
            verifyStaffButtonBehavior(view, 'staff-info');
        });

        it('hides the "Manage Individual Learners" panel when the button is clicked twice', function() {
            var view = createStaffArea(),
                $staffToolsButton = getStaffButton(view, 'staff-tools');
            expect($staffToolsButton).not.toHaveClass('is--active');
            $staffToolsButton[0].click();
            expect($staffToolsButton).toHaveClass('is--active');
            $staffToolsButton[0].click();
            expect($staffToolsButton).not.toHaveClass('is--active');
            expect(getVisibleStaffPanels(view).length).toBe(0);
        });
    });

    describe('Manage Individual Learners', function() {

        beforeEach(function() {
            loadFixtures('oa_base_course_staff.html');
        });

        it('hides the "Manage Individual Learners" panel when the close button is clicked', function() {
            var view = createStaffArea(),
                $staffToolsButton = $('.button-staff-tools', view.element),
                $staffToolsPanel = $('.wrapper--staff-tools', view.element),
                closeButton;
            expect($staffToolsButton.length).toBe(1);
            $staffToolsButton[0].click();
            expect($staffToolsButton).toHaveClass('is--active');
            expect($staffToolsPanel).toBeVisible();
            closeButton = $('.ui-staff_close_button', $staffToolsPanel)[0];
            verifyFocused(closeButton);

            // Now click the close button.
            closeButton.click();
            expect($staffToolsButton).not.toHaveClass('is--active');
            expect($staffToolsPanel).toBeHidden();
            verifyFocused($staffToolsButton[0]);
        });

        it('shows an error when clicking "Submit" with no student name chosen', function() {
            var staffArea = createStaffArea(), $error;
            chooseStudent(staffArea, '');
            $error = $('.openassessment_student_info_form .form--error', staffArea.element);
            expect($error.text().trim()).toBe('You must provide a learner name.');
            verifyFocused($error[0]);
        });

        it('shows an error message when failing to load the student info', function() {
            var staffArea = createStaffArea(), $error;
            server.studentInfo = failWith(server);
            chooseStudent(staffArea, 'testStudent');
            $error = $('.openassessment_student_info_form .form--error', staffArea.element);
            expect($error.text().trim()).toBe('Unexpected server error.');
            verifyFocused($error[0]);
        });

        it('moves focus to learner report when successfully loading the student info', function() {
            var staffArea = createStaffArea(), $reportHeader;
            chooseStudent(staffArea, 'testStudent');
            $reportHeader = $('.staff-info__student__report__summary', staffArea.element);
            expect($reportHeader.text().trim()).toContain('Viewing learner:');
            verifyFocused($reportHeader[0]);
        });

        it('updates aria-expanded when toggling slidable sections', function() {
            var staffArea = createStaffArea(), $slidableControls;
            chooseStudent(staffArea, 'testStudent');
            $slidableControls = $('.ui-staff.ui-slidable', staffArea.element);
            expect($slidableControls.length).toBe(5);
            expect($slidableControls).toHaveAttr('aria-expanded', 'false');
            $slidableControls[0].click();
            expect($slidableControls).toHaveAttr('aria-expanded', 'true');
        });

        it('links slidable controls with content', function() {
            var staffArea = createStaffArea();
            chooseStudent(staffArea, 'testStudent');
            $('.ui-slidable__control', staffArea.element).each(function(index, control) {
                var content = $(control).next('.ui-slidable__content');
                var button = $(control).find('.ui-slidable');
                expect(content).toHaveAttr('aria-labelledby', button.id);
                expect(button).toHaveAttr('aria-controls', content.id);
            });
        });

        describe('Submission Management', function() {
            it('updates submission cancellation button when comments changes', function() {
                // Prevent the server's response from resolving,
                // so we can see what happens before view gets re-rendered.
                spyOn(server, 'cancelSubmission').and.callFake(function() {
                    return $.Deferred(function() {}).promise();
                });

                var staffArea = createStaffArea();
                chooseStudent(staffArea, 'testStudent');

                // comments is blank --> cancel submission button disabled
                staffArea.comment('');
                staffArea.handleCommentChanged();
                expect(staffArea.cancelSubmissionEnabled()).toBe(false);

                // Response is whitespace --> cancel submission button disabled
                staffArea.comment('               \n      \n      ');
                staffArea.handleCommentChanged();
                expect(staffArea.cancelSubmissionEnabled()).toBe(false);

                // Response is not blank --> cancel submission button enabled
                staffArea.comment('Cancellation reason.');
                staffArea.handleCommentChanged();
                expect(staffArea.cancelSubmissionEnabled()).toBe(true);
            });

            it('submits the cancel submission comments to the server', function() {
                // Show the staff area for the test student
                var staffArea = createStaffArea();
                chooseStudent(staffArea, 'testStudent');

                // Cancel the student's submission
                staffArea.comment('Cancellation reason.');
                server.studentTemplate = 'oa_staff_cancelled_submission.html';
                staffArea.cancelSubmission('Bob');

                // Verify that the student view reflects the cancellation
                expect($($('.staff-info__student__response p', staffArea.element)[0]).text().trim()).toBe(
                    'Learner submission removed by staff on 2015-10-01 04:53 UTC'
                );
                expect($($('.staff-info__student__response p', staffArea.element)[1]).text().trim()).toBe(
                    'Comments: Cancelled!'
                );
            });

            it('shows an error message when a cancel submission request fails', function() {
                // Show the staff area for the test student
                var staffArea = createStaffArea(),
                    serverErrorMessage = 'Mock server error';
                chooseStudent(staffArea, 'testStudent');

                // Cancel the student's submission but return a server error
                staffArea.comment('Cancellation reason.');
                server.cancelSubmission = failWith(server, serverErrorMessage);
                staffArea.cancelSubmission('Bob');

                // Verify that the error message is shown
                expect($('.cancel-submission-error', staffArea.element).first().text().trim()).toBe(serverErrorMessage);
            });
        });

        describe('Staff Grade Override', function() {
            var staffAreaTab = "staff-tools";
            var gradingType = "override";

            afterEach(function() {
                // Disable the unsaved page warning (if set)
                OpenAssessment.clearUnsavedChanges();
            });

            it('enables the submit button when all required fields are specified', function() {
                var staffArea = createStaffArea(),
                    $assessment, $submitButton;
                chooseStudent(staffArea, 'testStudent');
                $assessment = getAssessment(staffArea, staffAreaTab);
                $submitButton = $('.action--submit', $assessment);
                expect(staffArea.staffSubmitEnabled()).toBe(false);
                fillAssessment($assessment, gradingType);
                expect(staffArea.staffSubmitEnabled()).toBe(true);
            });

            it('can submit a staff grade override', function() {
                var staffArea = createStaffArea(),
                    $assessment, $gradeSection, $gradeSectionButton;
                chooseStudent(staffArea, 'testStudent');

                // Verify that the student info section is hidden but shows the original score
                $gradeSection = $('.staff-info__student__grade', staffArea.element);
                expect($('.ui-slidable', $gradeSection)).not.toHaveClass('is--showing');
                expect($('.staff-info__final__grade__score').text().trim()).toBe(
                    'The problem has not been started.'
                );

                // Fill in and submit the assessment
                $assessment = getAssessment(staffArea, staffAreaTab);
                fillAssessment($assessment, gradingType);
                server.studentTemplate = 'oa_staff_graded_submission.html';
                submitAssessment(staffArea, staffAreaTab);

                verifyAssessType(staffArea, 'regrade');

                // Verify that the student info is visible and shows the correct score
                $gradeSection = $('.staff-info__student__grade', staffArea.element);
                $gradeSectionButton = $('.ui-slidable', $gradeSection);
                expect($gradeSectionButton).toHaveClass('is--showing');
                expect($gradeSectionButton).toHaveAttr('aria-expanded', 'true');
                verifyFocused($gradeSectionButton[0]);
                expect($('.ui-slidable__content', $gradeSection)).toBeVisible();
                expect($('.staff-info__final__grade__score').text().trim()).toBe(
                    'Final grade: 1 out of 2'
                );
            });

            it('shows an error message when a grade override request fails', function() {
                var staffArea = createStaffArea(),
                    serverErrorMessage = 'Mock server error',
                    $assessment;
                chooseStudent(staffArea, 'testStudent');
                $assessment = getAssessment(staffArea, staffAreaTab);
                fillAssessment($assessment, gradingType);

                // Submit the assessment but return a server error message
                server.staffAssess = failWith(server, serverErrorMessage);
                submitAssessment(staffArea, staffAreaTab);

                // Verify that the error message is shown
                expect($('.staff-override-error', staffArea.element).first().text().trim()).toBe(serverErrorMessage);
            });

            it('warns of unsubmitted assessments', function() {
                var staffArea = createStaffArea(),
                    $assessment;

                chooseStudent(staffArea, 'testStudent');

                expect(staffArea.baseView.unsavedWarningEnabled()).toBe(false);

                // Fill in and submit the assessment
                $assessment = getAssessment(staffArea, staffAreaTab);
                fillAssessment($assessment, gradingType);

                expect(staffArea.baseView.unsavedWarningEnabled()).toBe(true);

                server.studentTemplate = 'oa_staff_graded_submission.html';
                submitAssessment(staffArea, staffAreaTab);

                expect(staffArea.baseView.unsavedWarningEnabled()).toBe(false);
            });
        });
    });

    describe('View Assignment Statistics', function() {
        beforeEach(function() {
            loadFixtures('oa_base_course_staff.html');
        });

        it('hides the "View Assignment Statistics" panel when the close button is clicked', function() {
            var view = createStaffArea(),
                $staffInfoButton = $('.button-staff-info', view.element),
                $staffInfoPanel = $('.wrapper--staff-info', view.element),
                closeButton;
            expect($staffInfoButton.length).toBe(1);
            $staffInfoButton[0].click();
            expect($staffInfoButton).toHaveClass('is--active');
            expect($staffInfoPanel).toBeVisible();
            closeButton = $('.ui-staff_close_button', $staffInfoPanel)[0];
            verifyFocused(closeButton);

            // Now click the close button.
            closeButton.click();
            expect($staffInfoButton).not.toHaveClass('is--active');
            expect($staffInfoPanel).toBeHidden();
            verifyFocused($staffInfoButton[0]);
        });
    });

    describe('Grade Available Responses', function() {
        var staffAreaTab = "staff-grading";
        var gradingType = "full-grade";

        beforeEach(function() {
            loadFixtures('oa_base_course_staff.html');
        });

        afterEach(function() {
            // Disable the unsaved page warnings (if set).
            OpenAssessment.clearUnsavedChanges();
        });

        it('hides the "Grade Available Responses" panel when the close button is clicked', function() {
            var view = createStaffArea({}, 'oa_staff_area_full_grading.html'),
                $staffGradingButton = $('.button-staff-grading', view.element),
                $staffGradingPanel = $('.wrapper--staff-grading', view.element),
                closeButton;
            expect($staffGradingButton.length).toBe(1);
            $staffGradingButton[0].click();
            expect($staffGradingButton).toHaveClass('is--active');
            expect($staffGradingPanel).toBeVisible();
            closeButton = $('.ui-staff_close_button', $staffGradingPanel)[0];
            verifyFocused(closeButton);

            // Now click the close button.
            closeButton.click();
            expect($staffGradingButton).not.toHaveClass('is--active');
            expect($staffGradingPanel).toBeHidden();
            verifyFocused($staffGradingButton[0]);
        });

        it('enables both submit buttons when all required fields are specified', function() {
            var staffArea = createStaffArea({}, 'oa_staff_area_full_grading.html'),
                $assessment, $submitButtons;
            showInstructorAssessmentForm(staffArea);
            $assessment = getAssessment(staffArea, staffAreaTab);
            $submitButtons = $('.action--submit', $assessment);
            expect($submitButtons.length).toBe(2);
            expect($submitButtons).toHaveAttr('disabled');
            fillAssessment($assessment, gradingType);
            expect($submitButtons).not.toHaveAttr('disabled');
        });

        it('can submit a staff grade', function() {
            var staffArea = createStaffArea({}, 'oa_staff_area_full_grading.html'),
                $assessment, $staffGradeButton;
            $staffGradeButton = $('.staff__grade__show-form', staffArea.element);
            expect($staffGradeButton).toHaveAttr('aria-expanded', 'false');
            showInstructorAssessmentForm(staffArea);
            expect($staffGradeButton).toHaveAttr('aria-expanded', 'true');
            $assessment = getAssessment(staffArea, staffAreaTab);

            // Verify that the submission is shown for the first user
            expect($('.staff-assessment__display__title', $assessment).text().trim()).toBe(
                'Response for: mock_user'
            );

            // Fill in and submit the assessment
            fillAssessment($assessment, gradingType);
            server.staffGradeFormTemplate = 'oa_staff_grade_learners_assessment_2.html';
            submitAssessment(staffArea, staffAreaTab);
            verifyAssessType(staffArea, 'full-grade');

            // Verify that the assessment form has been removed
            expect($('.staff__grade__form', staffArea.element).html().trim()).toBe('');
            expect($staffGradeButton).toHaveAttr('aria-expanded', 'false');
            verifyFocused($staffGradeButton[0]);
        });

        it('can submit a staff grade and receive another submission', function() {
            var staffArea = createStaffArea({}, 'oa_staff_area_full_grading.html'),
                $assessment, $staffGradeButton;
            showInstructorAssessmentForm(staffArea);
            $staffGradeButton = $('.staff__grade__show-form', staffArea.element);

            // Verify that the submission is shown for the first user
            expect($('.staff-assessment__display__title', staffArea.element).text().trim()).toBe(
                'Response for: mock_user'
            );

            // Fill in and click the button to submit and request another submission
            $assessment = getAssessment(staffArea, staffAreaTab);
            fillAssessment($assessment, gradingType);
            server.staffGradeFormTemplate = 'oa_staff_grade_learners_assessment_2.html';
            $('.continue_grading--action', $assessment).click();

            // Verify that the submission is shown for the second learner
            expect($('.staff-assessment__display__title', staffArea.element).text().trim()).toBe(
                'Response for: mock_user_2'
            );
            verifyFocused($staffGradeButton[0]);
        });

        it('shows an error message when failing to load the staff grade form', function() {
            var staffArea = createStaffArea({}, 'oa_staff_area_full_grading.html'), $error;
            server.staffGradeForm = failWith(server);
            showInstructorAssessmentForm(staffArea);
            $error = $('.staff__grade__form--error', staffArea.element);
            expect($error.text().trim()).toBe('Unexpected server error.');
            verifyFocused($error[0]);
        });

        it('shows an error message when a staff grade request fails', function() {
            var staffArea = createStaffArea({}, 'oa_staff_area_full_grading.html'),
                serverErrorMessage = 'Mock server error',
                $assessment;
            showInstructorAssessmentForm(staffArea);
            $assessment = getAssessment(staffArea, staffAreaTab);
            fillAssessment($assessment, gradingType);

            // Submit the assessment but return a server error message
            server.staffAssess = failWith(server, serverErrorMessage);
            submitAssessment(staffArea, staffAreaTab);

            // Verify that the error message is shown
            expect($('.staff-grade-error', staffArea.element).first().text().trim()).toBe(serverErrorMessage);
        });

        it('shows the number of ungraded and checked out submissions', function() {
            var staffArea = createStaffArea({}, 'oa_staff_area_full_grading.html'),
                $assessment;

            expect($('.staff__grade__value').text().trim()).toBe("10 Available and 2 Checked Out");

            // Rendering the staff grading form will cause the counts to re-render as well.
            // This will use the staffGradeCountsTemplate template, which mimics the count changes.
            server.staffGradeCountsTemplate = 'oa_staff_grade_learners_count_1.html';
            showInstructorAssessmentForm(staffArea);

            expect($('.staff__grade__value').text().trim()).toBe("9 Available and 3 Checked Out");

            // Fill in assessment and make sure the code re-renders the count form.
            $assessment = getAssessment(staffArea, staffAreaTab);
            fillAssessment($assessment, gradingType);
            // Return a different counts template to mimic the counts changing again.
            server.staffGradeCountsTemplate = 'oa_staff_grade_learners_count_2.html';
            submitAssessment(staffArea, staffAreaTab);

            expect($('.staff__grade__value').text().trim()).toBe("9 Available and 2 Checked Out");
        });

        it('warns of unsubmitted assessments', function() {
            var staffArea = createStaffArea({}, 'oa_staff_area_full_grading.html'),
                $assessment;

            showInstructorAssessmentForm(staffArea);

            expect(staffArea.baseView.unsavedWarningEnabled()).toBe(false);

            // Fill in assessment and make sure the code re-renders the count form.
            $assessment = getAssessment(staffArea, staffAreaTab);
            fillAssessment($assessment, gradingType);
            expect(staffArea.baseView.unsavedWarningEnabled()).toBe(true);

            submitAssessment(staffArea, staffAreaTab);
            expect(staffArea.baseView.unsavedWarningEnabled()).toBe(false);
        });
    });

    describe('Grade Available Responses as the separate view', function() {
        var staffAreaTab = "staff-grading";
        var gradingType = "full-grade";

        beforeEach(function() {
            loadFixtures('oa_grade_available_responses_separate_view.html');
        });

        it('exists without any additional buttons', function() {
            var view = createGradeAvailableResponsesView(),
                staffArea = $('.openassessment__staff-area', view.element),
                staffGradingButton = $('.button-staff-grading', view.element),
                problemHeader = $('.problem__header', view.element),
                gradeValue = $('.staff__grade__value', view.element);
            expect(staffArea.length).toBe(1);
            expect(staffGradingButton.length).toBe(0);
            expect(problemHeader.text()).toBe('Test ABC');
            expect(gradeValue.text().trim()).toBe("9 Available and 2 Checked Out");
        });

        it('can submit a staff grade', function() {
            var view = createGradeAvailableResponsesView(),
                $assessment, $staffGradeButton;
            $staffGradeButton = $('.staff__grade__show-form', view.element);
            expect($staffGradeButton).toHaveAttr('aria-expanded', 'false');
            showInstructorAssessmentForm(view);
            expect($staffGradeButton).toHaveAttr('aria-expanded', 'true');
            $assessment = getAssessment(view, staffAreaTab);

            // Verify that the submission is shown
            expect($('.staff-assessment__display__title', view.element).text().trim()).toBe(
                'Response for: mock_user'
            );

            // Fill in and submit the assessment
            fillAssessment($assessment, gradingType);
            server.staffGradeFormTemplate = 'oa_staff_grade_learners_assessment_2.html';
            submitAssessment(view.staffAreaView, staffAreaTab);
            verifyAssessType(view.staffAreaView, 'full-grade');

            // Verify that the assessment form has been removed
            expect($('.staff__grade__form', view.element).html().trim()).toBe('');
            expect($staffGradeButton).toHaveAttr('aria-expanded', 'false');
            verifyFocused($staffGradeButton[0]);
        });
    });
});
