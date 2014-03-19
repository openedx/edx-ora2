/**
Tests for OA student-facing views.
**/

describe("OpenAssessment.BaseUI", function() {

    // Stub server that returns dummy data
    var StubServer = function() {

        // Dummy fragments to return from the render func
        this.fragments = {
            submission: "Test submission",
            self_assessment: readFixtures("self_assessment_frag.html"),
            peer_assessment: readFixtures("peer_assessment_frag.html"),
            grade: "Test fragment"
        };

        this.submit = function(submission) {
            return $.Deferred(function(defer) {
                 defer.resolveWith(this, ['student', 0]);
            }).promise();
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

        this.submitFeedbackOnAssessment = function(text, options) {
            // Store the args we receive so we can check them later
            this.feedbackText = text;
            this.feedbackOptions = options;

            // Return a promise that always resolves successfully
            return $.Deferred(function(defer) { defer.resolve() }).promise();
        };
    };

    // Stub runtime
    var runtime = {};

    var server = null;
    var ui = null;

    /**
    Wait for subviews to load before executing callback.

    Args:
        callback (function): Function that takes no arguments.
    **/
    var loadSubviews = function(callback) {
        runs(function() {
            ui.load();
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
        ui = new OpenAssessment.BaseUI(runtime, el, server);
    });

    it("Sends a submission to the server", function() {
        loadSubviews(function() {
            spyOn(server, 'submit').andCallThrough();
            ui.submit();
            expect(server.submit).toHaveBeenCalled();
        });
    });

    it("Sends a peer assessment to the server", function() {
        loadSubviews(function() {
            spyOn(server, 'peerAssess').andCallThrough();
            ui.peerAssess();
            expect(server.peerAssess).toHaveBeenCalled();
        });
    });

    it("Sends a self assessment to the server", function() {
        loadSubviews(function() {
            spyOn(server, 'selfAssess').andCallThrough();
            ui.selfAssess();
            expect(server.selfAssess).toHaveBeenCalled();
        });
    });

    it("Sends feedback on a submission to the server", function() {
        jasmine.getFixtures().fixturesPath = 'base/fixtures';
        loadFixtures('grade_complete.html');

        // Simulate user feedback
        $('#feedback__remarks__value').val('I disliked the feedback I received.');
        $('#feedback__overall__value--notuseful').attr('checked','checked');
        $('#feedback__overall__value--disagree').attr('checked','checked');

        // Create a new stub server
        server = new StubServer();

        // Create the object under test
        var el = $("#openassessment-base").get(0);
        ui = new OpenAssessment.BaseUI(runtime, el, server);

        // Submit feedback on an assessment
        ui.submitFeedbackOnAssessment();

        // Expect that the feedback was retrieved from the DOM and sent to the server
        expect(server.feedbackText).toEqual('I disliked the feedback I received.');
        expect(server.feedbackOptions).toEqual([
            'These assessments were not useful.',
            'I disagree with the ways that my peers assessed me.'
        ]);
    });
});
