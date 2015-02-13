/**
 Tests for OpenAssessment Student Training view.
 **/

describe("OpenAssessment.StaffInfoView", function() {

    // Stub server that returns dummy data for the staff info view
    var StubServer = function() {

        // Remember which fragments have been loaded
        this.fragmentsLoaded = [];

        // Render the template for the staff info view
        this.render = function(component) {
            var server = this;
            this.fragmentsLoaded.push(component);
            return $.Deferred(function(defer) {
                fragment = readFixtures("oa_staff_info.html");
                defer.resolveWith(this, [fragment]);
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

        this.cancelSubmission = function(submissionUUID) {
            return successPromise;
        };

        this.data = {};

    };

    // Stub base view
    var StubBaseView = function() {
        this.showLoadError = function(msg) {};
        this.toggleActionError = function(msg, step) {};
        this.setUpCollapseExpand = function(sel) {};
        this.scrollToTop = function() {};
        this.loadAssessmentModules = function() {};
        this.loadMessageView = function() {};
    };

    // Stubs
    var baseView = null;
    var server = null;

    /**
    Initialize the staff info view, then check whether it makes
    an AJAX call to load the staff info section.
    **/
    var assertStaffInfoAjaxCall = function(shouldCall) {
        // Load the staff info view
        var el = $("#openassessment-base").get(0);
        var view = new OpenAssessment.StaffInfoView(el, server, baseView);
        view.load();

        // Check whether it tried to load staff info from the server
        var expectedFragments = [];
        if (shouldCall) { expectedFragments = ['staff_info']; }
        expect(server.fragmentsLoaded).toEqual(expectedFragments);
    };

    beforeEach(function() {
        // Create a new stub server
        server = new StubServer();
        server.renderLatex = jasmine.createSpy('renderLatex')
        // Create the stub base view
        baseView = new StubBaseView();
    });

    it("schedules training of AI classifiers", function() {
        server.data = {
            "success": true,
            "workflow_uuid": "abc123",
            "msg": "Great success."
        };
        spyOn(server, 'scheduleTraining').andCallThrough();

        // Load the fixture
        loadFixtures('oa_base.html');

        // Load the view
        var el = $("#openassessment-base").get(0);
        var view = new OpenAssessment.StaffInfoView(el, server, baseView);
        view.load();

        // Submit the assessment
        view.scheduleTraining();

        // Expect that the assessment was sent to the server
        expect(server.scheduleTraining).toHaveBeenCalled();
    });


    it("Loads staff info if the page contains a course staff section", function() {
        // Load the fixture for the container page that DOES include a course staff section
        loadFixtures('oa_base_course_staff.html');
        assertStaffInfoAjaxCall(true);
    });

    it("Does NOT load staff info if the page does NOT contain a course staff section", function() {
        // Load the fixture for the container page that does NOT include a course staff section
        loadFixtures('oa_base.html');
        assertStaffInfoAjaxCall(false);
    });

    it("reschedules training of AI tasks", function() {
        server.data = {
            "success": true,
            "workflow_uuid": "abc123",
            "msg": "Great success."
        };

        var el = $("#openassessment-base").get(0);
        var view = new OpenAssessment.StaffInfoView(el, server, baseView);
        view.load();

        spyOn(server, 'rescheduleUnfinishedTasks').andCallThrough();

        // Test the Rescheduling
        view.rescheduleUnfinishedTasks();

        // Expect that the server was instructed to reschedule Unifinished Taks
        expect(server.rescheduleUnfinishedTasks).toHaveBeenCalled();
    });

    it("reschedules training of AI tasks", function() {
        server.data = {
            "success": false,
            "workflow_uuid": "abc123",
            "errMsg": "Stupendous Failure."
        };

        var el = $("#openassessment-base").get(0);
        var view = new OpenAssessment.StaffInfoView(el, server, baseView);
        view.load();

        spyOn(server, 'rescheduleUnfinishedTasks').andCallThrough();

        // Test the Rescheduling
        view.rescheduleUnfinishedTasks();

        // Expect that the server was instructed to reschedule Unifinished Taks
        expect(server.rescheduleUnfinishedTasks).toHaveBeenCalled();
    });

    it("updates submission cancellation button when comments changes", function() {
        // Prevent the server's response from resolving,
        // so we can see what happens before view gets re-rendered.
        spyOn(server, 'cancelSubmission').andCallFake(function() {
            return $.Deferred(function(defer) {}).promise();
        });

        // Load the fixture
        loadFixtures('oa_student_info.html');

        var el = $("#openassessment-base").get(0);
        var view = new OpenAssessment.StaffInfoView(el, server, baseView);

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

    it("submits the cancel submission comments to the server", function() {
        spyOn(server, 'cancelSubmission').andCallThrough();

        // Load the fixture
        loadFixtures('oa_student_info.html');

        var el = $("#openassessment-base").get(0);
        var view = new OpenAssessment.StaffInfoView(el, server, baseView);

        view.comment('Cancellation reason.');
        view.cancelSubmission('Bob');

        expect(server.cancelSubmission).toHaveBeenCalledWith('Bob', 'Cancellation reason.');
    });


});
