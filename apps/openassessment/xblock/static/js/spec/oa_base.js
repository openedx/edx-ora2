/**
Tests for OA student-facing views.
**/

describe("OpenAssessment.BaseView", function() {

    // Stub server that returns dummy data
    var StubServer = function() {

        // Dummy fragments to return from the render func
        this.fragments = {
            submission: "Test submission",
            self_assessment: readFixtures("self_assessment_frag.html"),
            peer_assessment: readFixtures("peer_assessment_frag.html"),
            grade: "Test fragment"
        };

        this.peerAssess = function(submissionId, optionsSelected, feedback) {
            return $.Deferred(function(defer) { defer.resolve(); }).promise();
        };

        this.selfAssess = function(submissionId, optionsSelected) {
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
            var subviewHasHtml = $("#openassessment-base").children().map(
                function(index, el) { return el.innerHTML !== ''; }
            );
            return Array(subviewHasHtml).every(function(hasHtml) { return hasHtml; });
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
        var el = $("#openassessment-base").get(0);
        view = new OpenAssessment.BaseView(runtime, el, server);
    });

    it("Sends a peer assessment to the server", function() {
        loadSubviews(function() {
            spyOn(server, 'peerAssess').andCallThrough();
            view.peerAssess();
            expect(server.peerAssess).toHaveBeenCalled();
        });
    });

    it("Sends a self assessment to the server", function() {
        loadSubviews(function() {
            spyOn(server, 'selfAssess').andCallThrough();
            view.selfAssess();
            expect(server.selfAssess).toHaveBeenCalled();
        });
    });

});
