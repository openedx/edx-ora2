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

        // Remember which fragments have been loaded
        this.fragmentsLoaded = [];

        // Render the template for the staff info view
        this.render = function(component) {
            var server = this;
            this.fragmentsLoaded.push(component);
            return $.Deferred(function(defer) {
                var fragment = readFixtures('oa_staff_area.html');
                defer.resolveWith(server, [fragment]);
            });
        };

        this.studentInfo = function() {
            var server = this;
            return $.Deferred(function(defer) {
                var fragment = readFixtures(server.studentTemplate);
                defer.resolveWith(server, [fragment]);
            });
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

        this.data = {};

    };

    // Stubs
    var server = null;
    var runtime = {};

    /**
     * Create a staff area view.
     * @param serverResponse An optional fake response from the server.
     * @returns {OpenAssessment.StaffAreaView} The staff area view.
     */
    var createStaffArea = function(serverResponse) {
        if (serverResponse) {
            server.data = serverResponse;
        }
        var assessmentElement = $('#openassessment').get(0);
        var baseView = new OpenAssessment.BaseView(runtime, assessmentElement, server, {});
        var view = new OpenAssessment.StaffAreaView(assessmentElement, server, baseView);
        view.load();
        return view;
    };

    /**
     * Initialize the staff area view, then check whether it makes
     * an AJAX call to populate itself.
     * @param shouldCall True if an AJAX call should be made.
     */
    var assertStaffAreaAjaxCall = function(shouldCall) {
        createStaffArea();

        // Check whether it tried to load staff area from the server
        var expectedFragments = [];
        if (shouldCall) { expectedFragments = ['staff_area']; }
        expect(server.fragmentsLoaded).toEqual(expectedFragments);
    };

    beforeEach(function() {
        // Create a new stub server
        server = new StubServer();
        server.renderLatex = jasmine.createSpy('renderLatex');
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
            return $('.wrapper--ui-staff', view.element).not('.is--hidden');
        };

        var verifyStaffButtonBehavior = function(view, buttonName) {
            var $staffInfoButton = getStaffButton(view, buttonName),
                $visiblePanels;
            expect($staffInfoButton).not.toHaveClass('is--active');
            $staffInfoButton[0].click();
            expect($staffInfoButton).toHaveClass('is--active');
            $visiblePanels = getVisibleStaffPanels(view);
            expect($visiblePanels.length).toBe(1);
            expect($visiblePanels.first()).toHaveClass('wrapper--' + buttonName);
        };

        it('shows the correct buttons with no panels initially', function() {
            var view = createStaffArea(),
                $buttons = $('.ui-staff__button', view.element);
            expect($buttons.length).toBe(2);
            expect($($buttons[0]).text().trim()).toEqual('Staff Tools');
            expect($($buttons[1]).text().trim()).toEqual('Staff Info');
            expect(getVisibleStaffPanels(view).length).toBe(0);
        });

        it('shows the "Staff Tools" panel when the button is clicked', function() {
            var view = createStaffArea();
            verifyStaffButtonBehavior(view, 'staff-tools');
        });

        it('shows the "Staff Info" panel when the button is clicked', function() {
            var view = createStaffArea();
            verifyStaffButtonBehavior(view, 'staff-info');
        });

        it('hides the "Staff Tools" panel when the button is clicked twice', function() {
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

    describe('Staff Tools', function() {
        var chooseStudent = function(view, studentName) {
            var studentNameField = $('.openassessment__student_username', view.element),
                submitButton = $('.action--submit-username', view.element);
            studentNameField.val(studentName);
            submitButton.click();
        };

        beforeEach(function() {
            loadFixtures('oa_base_course_staff.html');
        });

        it('hides the "Staff Tools" panel when the close button is clicked', function() {
            var view = createStaffArea(),
                $staffToolsButton = $('.button-staff-tools', view.element),
                $staffToolsPanel = $('.wrapper--staff-tools', view.element);
            expect($staffToolsButton.length).toBe(1);
            $staffToolsButton[0].click();
            expect($staffToolsButton).toHaveClass('is--active');
            $('.ui-staff_close_button', $staffToolsPanel).first().click();
            expect($staffToolsButton).not.toHaveClass('is--active');
            expect($staffToolsPanel).toHaveClass('is--hidden');
        });

        it('shows an error when clicking "Submit" with no student name chosen', function() {
            var staffArea = createStaffArea();
            chooseStudent(staffArea, '');
            expect($('.openassessment_student_info_form .form--error', staffArea.element).text().trim())
                .toBe('A learner name must be provided.');
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
                    'Learner submission removed by staff on October 1, 2015 04:53 UTC'
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
            var fillAssessment = function($assessment) {
                $('#staff__assessment__rubric__question--2__feedback', $assessment).val('Text response');
                $('.question__answers', $assessment).each(function() {
                    $('input[type="radio"]', this).first().click();
                });
            };

            var submitAssessment = function(staffArea) {
                var $assessment = $('.wrapper--staff-assessment', staffArea.element),
                    $submitButton = $('.action--submit', $assessment);
                $submitButton.click();
            };

            it('enables the submit button when all required fields are specified', function() {
                var staffArea = createStaffArea(),
                    $assessment, $submitButton;
                chooseStudent(staffArea, 'testStudent');
                $assessment = $('.wrapper--staff-assessment', staffArea.element);
                $submitButton = $('.action--submit', $assessment);
                expect($submitButton).toHaveClass('is--disabled');
                fillAssessment($assessment);
                expect($submitButton).not.toHaveClass('is--disabled');
            });

            it('can submit a staff grade override', function() {
                var staffArea = createStaffArea(),
                    $assessment, $gradeSection;
                chooseStudent(staffArea, 'testStudent');

                // Verify that the student info section is hidden but shows the original score
                $gradeSection = $('.staff-info__student__grade', staffArea.element);
                expect($('.ui-toggle-visibility', $gradeSection)).toHaveClass('is--collapsed');
                expect($('p', $gradeSection).first().text().trim()).toBe(
                    'The problem has not been started.'
                );

                // Fill in and submit the assessment
                $assessment = $('.wrapper--staff-assessment', staffArea.element);
                fillAssessment($assessment);
                server.studentTemplate = 'oa_staff_graded_submission.html';
                submitAssessment(staffArea);

                // Verify that the student info is visible and shows the correct score
                $gradeSection = $('.staff-info__student__grade', staffArea.element);
                expect($('.ui-toggle-visibility', $gradeSection)).not.toHaveClass('is--collapsed');
                expect($('p', $gradeSection).first().text().trim()).toBe(
                    'Final grade: 1 out of 2'
                );
            });

            it('shows an error message when a grade override request fails', function() {
                var staffArea = createStaffArea(),
                    serverErrorMessage = 'Mock server error',
                    $assessment;
                chooseStudent(staffArea, 'testStudent');
                $assessment = $('.wrapper--staff-assessment', staffArea.element);
                fillAssessment($assessment);

                // Submit the assessment but return a server error message
                staffArea.comment('Cancellation reason.');
                server.staffAssess = failWith(server, serverErrorMessage);
                submitAssessment(staffArea);

                // Verify that the error message is shown
                expect($('.staff-override-error', staffArea.element).first().text().trim()).toBe(serverErrorMessage);
            });
        });
    });

    describe('Staff Info', function() {
        beforeEach(function() {
            loadFixtures('oa_base_course_staff.html');
        });

        it('hides the "Staff Info" panel when the close button is clicked', function() {
            var view = createStaffArea(),
                $staffInfoButton = $('.button-staff-info', view.element),
                $staffInfoPanel = $('.wrapper--staff-info', view.element);
            expect($staffInfoButton.length).toBe(1);
            $staffInfoButton[0].click();
            expect($staffInfoButton).toHaveClass('is--active');
            $('.ui-staff_close_button', $staffInfoPanel).first().click();
            expect($staffInfoButton).not.toHaveClass('is--active');
            expect($staffInfoPanel).toHaveClass('is--hidden');
        });
    });
});
