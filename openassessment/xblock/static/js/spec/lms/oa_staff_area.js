/**
 * Tests for OpenAssessment Student Training view.
 */
describe('OpenAssessment.StaffAreaView', function() {
    'use strict';

    // Stub server that returns dummy data for the staff info view
    var StubServer = function() {

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

        var successPromise = $.Deferred(
            function(defer) { defer.resolve(); }
        ).promise();

        this.cancelSubmission = function() {
            return successPromise;
        };

        this.data = {};

    };

    // Stub base view
    var StubBaseView = function() {
        this.showLoadError = function() {};
        this.toggleActionError = function() {};
        this.setUpCollapseExpand = function() {};
        this.scrollToTop = function() {};
        this.loadAssessmentModules = function() {};
        this.loadMessageView = function() {};
    };

    // Stubs
    var baseView = null;
    var server = null;

    /**
     * Create a staff area view.
     * @param serverResponse An optional fake response from the server.
     * @returns {OpenAssessment.StaffAreaView} The staff area view.
     */
    var createStaffArea = function(serverResponse) {
        if (serverResponse) {
            server.data = serverResponse;
        }
        var el = $('#openassessment').get(0);
        var view = new OpenAssessment.StaffAreaView(el, server, baseView);
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
        // Create the stub base view
        baseView = new StubBaseView();
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

    describe('Submission Management', function() {
        it('updates submission cancellation button when comments changes', function() {
            // Prevent the server's response from resolving,
            // so we can see what happens before view gets re-rendered.
            spyOn(server, 'cancelSubmission').and.callFake(function() {
                return $.Deferred(function() {}).promise();
            });

            // Load the fixture
            loadFixtures('oa_student_info.html');

            var view = createStaffArea();

            // comments is blank --> cancel submission button disabled
            view.comment('');
            view.handleCommentChanged();
            expect(view.cancelSubmissionEnabled()).toBe(false);

            // Response is whitespace --> cancel submission button disabled
            view.comment('               \n      \n      ');
            view.handleCommentChanged();
            expect(view.cancelSubmissionEnabled()).toBe(false);

            // Response is not blank --> cancel submission button enabled
            view.comment('Cancellation reason.');
            view.handleCommentChanged();
            expect(view.cancelSubmissionEnabled()).toBe(true);
        });

        it('submits the cancel submission comments to the server', function() {
            spyOn(server, 'cancelSubmission').and.callThrough();

            // Load the fixture
            loadFixtures('oa_student_info.html');
            var view = createStaffArea();

            view.comment('Cancellation reason.');
            view.cancelSubmission('Bob');

            expect(server.cancelSubmission).toHaveBeenCalledWith('Bob', 'Cancellation reason.');
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
