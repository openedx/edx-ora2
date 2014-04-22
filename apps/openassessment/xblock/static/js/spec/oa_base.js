/**
Tests for OA student-facing views.
**/

describe("OpenAssessment.BaseView", function() {

    // Stub server that returns dummy data
    var StubServer = function() {

        // Dummy fragments to return from the render func
        this.fragments = {
            submission: readFixtures("oa_response.html"),
            self_assessment: readFixtures("oa_self_assessment.html"),
            peer_assessment: readFixtures("oa_peer_assessment.html"),
            grade: readFixtures("oa_grade_complete.html")
        };

        this.selfAssess = function(optionsSelected) {
            return $.Deferred(function(defer) { defer.resolve(); }).promise();
        };

        this.render = function(component) {
            var server = this;
            return $.Deferred(function(defer) {
                defer.resolveWith(this, [server.fragments[component]]);
            }).promise();
        };
    };

    // Stub runtime
    var runtime = {};

    var server = null;
    var view = null;

    /**
    Wait for subviews to load before executing callback.

    Args:
        callback (function): Function that takes no arguments.
    **/
    var loadSubviews = function(callback) {
        runs(function() {
            view.load();
        });

        waitsFor(function() {
            return !$(".openassessment__steps__step").hasClass('is--loading');
        });

        runs(function() {
            return callback();
        });
    };

    beforeEach(function() {
        // Load the DOM fixture
        jasmine.getFixtures().fixturesPath = 'base/fixtures';
        loadFixtures('oa_base.html');

        // Create a new stub server
        server = new StubServer();

        // Create the object under test
        var el = $("#openassessment").get(0);
        view = new OpenAssessment.BaseView(runtime, el, server);
    });

    it("Sends a self assessment to the server", function() {
        loadSubviews(function() {
            spyOn(server, 'selfAssess').andCallThrough();
            view.selfAssess();
            expect(server.selfAssess).toHaveBeenCalled();
        });
    });

    it("Displays error messages from self assessment to the user", function() {
        var testError = 'Test failure contacting server message';
        loadSubviews(function() {
            /* stub our selfAssess to fail */
            spyOn(server, 'selfAssess').andCallFake(function(optionsSelected) {
                return $.Deferred(function(defer) { defer.rejectWith(server, [testError]); }).promise();
            });
            view.selfAssess();
            expect(server.selfAssess).toHaveBeenCalled();
            expect(view.getStepActionsErrorMessage()).toContain(testError);
        });
    });

});
