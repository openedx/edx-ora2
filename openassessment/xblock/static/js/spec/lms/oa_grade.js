/**
Tests for OpenAssessment grade view.
**/

describe("OpenAssessment.GradeView", function() {

    // Stub server
    var StubServer = function() {
        var successPromise = $.Deferred(
            function(defer) {
                defer.resolve();
            }
        ).promise();

        this.submitFeedbackOnAssessment = function(text, options) {
            // Store the args we receive so we can check them later
            this.feedbackText = text;
            this.feedbackOptions = options;

            // Return a promise that always resolves successfully
            return successPromise;
        };

        this.render = function(step) {
            return successPromise;
        };
    };

    // Stub base view
    var StubBaseView = function() {
        this.showLoadError = function(msg) {};
        this.toggleActionError = function(msg, step) {};
        this.setUpCollapseExpand = function(sel) {};
    };

    // Stubs
    var baseView = null;
    var server = null;

    // View under test
    var view = null;

    beforeEach(function() {
        // Load the DOM fixture
        loadFixtures('oa_grade_complete.html');

        // Create the stub server
        server = new StubServer();

        // Create the stub base view
        baseView = new StubBaseView();

        // Create and install the view
        var el = $('#openassessment-base').get(0);
        view = new OpenAssessment.GradeView(el, server, baseView);
        view.installHandlers();
    });

    it("sends feedback on a submission to the server", function() {
        // Simulate user feedback
        view.feedbackText('I disliked the feedback I received');
        view.feedbackOptions(['notuseful', 'disagree']);

        // Submit feedback on an assessment
        view.submitFeedbackOnAssessment();

        // Expect that the feedback was retrieved from the DOM and sent to the server
        expect(server.feedbackText).toEqual('I disliked the feedback I received');
        expect(server.feedbackOptions).toEqual([
            'These assessments were not useful.',
            'I disagree with one or more of the peer assessments of my response.'
        ]);
    });

    it("updates the feedback state when the user submits feedback", function() {
        // Set the initial feedback state to open
        view.feedbackState('open');
        expect(view.feedbackState()).toEqual('open');

        // Submit feedback on an assessment
        view.feedbackText('I liked the feedback I received');
        view.feedbackOptions(['useful']);
        view.submitFeedbackOnAssessment();

        // Expect that the feedback state to be submitted
        expect(view.feedbackState()).toEqual('submitted');
    });
});
