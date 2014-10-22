/**
 Tests for OpenAssessment Peer view.
 **/

describe("OpenAssessment.PeerView", function() {

    // Stub server
    var StubServer = function() {
        var successPromise = $.Deferred(
            function(defer) {
                defer.resolve();
            }
        ).promise();

        this.peerAssess = function(optionsSelected, feedback) {
            return successPromise;
        };

        this.render = function(step) {
            return successPromise;
        };

        this.renderContinuedPeer = function() {
            return successPromise;
        };
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

    // View under test
    var view = null;

    beforeEach(function() {
        // Load the DOM fixture
        loadFixtures('oa_peer_assessment.html');

        // Create a new stub server
        server = new StubServer();

        // Create the stub base view
        baseView = new StubBaseView();

        // Create the object under test
        var el = $("#openassessment-base").get(0);
        view = new OpenAssessment.PeerView(el, server, baseView);
        view.installHandlers();
    });

    it("Sends a peer assessment to the server", function() {
        spyOn(server, 'peerAssess').andCallThrough();

        // Select options in the rubric
        var optionsSelected = {};
        optionsSelected['Criterion 1'] = 'Poor';
        optionsSelected['Criterion 2'] = 'Fair';
        optionsSelected['Criterion 3'] = 'Good';
        view.rubric.optionsSelected(optionsSelected);

        // Provide per-criterion feedback
        var criterionFeedback = {};
        criterionFeedback['Criterion 1'] = "You did a fair job";
        criterionFeedback['Criterion 3'] = "You did a good job";
        view.rubric.criterionFeedback(criterionFeedback);

        // Provide overall feedback
        var overallFeedback = "Good job!";
        view.rubric.overallFeedback(overallFeedback);

        // Submit the peer assessment
        view.peerAssess();

        // Expect that the peer assessment was sent to the server
        // with the options and feedback we selected
        expect(server.peerAssess).toHaveBeenCalledWith(
            optionsSelected, criterionFeedback, overallFeedback, ''
        );
    });

    it("Re-enables the peer assess button on error", function() {
        // Simulate a server error
        spyOn(server, 'peerAssess').andCallFake(function() {
            expect(view.peerSubmitEnabled()).toBe(false);
            return $.Deferred(function(defer) {
                defer.rejectWith(this, ['ENOUNKNOWN', 'Error occurred!']);
            }).promise();
        });
        view.peerAssess();

        // Expect the submit button to have been re-enabled
        expect(view.peerSubmitEnabled()).toBe(true);
    });

    it("Re-enables the continued grading button on error", function() {
        jasmine.getFixtures().fixturesPath = 'base/fixtures';
        loadFixtures('oa_peer_complete.html');
        // Simulate a server error
        spyOn(server, 'renderContinuedPeer').andCallFake(function() {
            expect(view.continueAssessmentEnabled()).toBe(false);
            return $.Deferred(function(defer) {
                defer.rejectWith(this, ['Error occurred!']);
            }).promise();
        });
        view.loadContinuedAssessment();

        // Expect the submit button to have been re-enabled
        expect(view.continueAssessmentEnabled()).toBe(true);
    });
});
