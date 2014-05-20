/**
 Tests for OpenAssessment Student Training view.
 **/

describe("OpenAssessment.StaffInfoView", function() {

    // Stub server
    var StubServer = function() {
        var successPromise = $.Deferred(
            function(defer) { defer.resolve(); }
        ).promise();

        this.render = function(step) {
            return successPromise;
        };

        this.scheduleTraining = function() {
            var server = this;
            return $.Deferred(function(defer) {
                defer.resolveWith(server, [server.data]);
            }).promise();
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
    };

    // Stubs
    var baseView = null;
    var server = null;

    // View under test
    var view = null;

    beforeEach(function() {
        // Load the DOM fixture
        jasmine.getFixtures().fixturesPath = 'base/fixtures';
        loadFixtures('staff_debug.html');

        // Create a new stub server
        server = new StubServer();

        // Create the stub base view
        baseView = new StubBaseView();

        // Create the object under test
        var el = $("#openassessment-base").get(0);
        view = new OpenAssessment.StaffInfoView(el, server, baseView);
        view.installHandlers();
    });

    it("schedules training of AI classifiers", function() {
        server.data = {
            "success": true,
            "workflow_uuid": "abc123",
            "msg": "Great success."
        };
        spyOn(server, 'scheduleTraining').andCallThrough();

        // Submit the assessment
        view.scheduleTraining();

        // Expect that the assessment was sent to the server
        expect(server.scheduleTraining).toHaveBeenCalled();
    });
});
