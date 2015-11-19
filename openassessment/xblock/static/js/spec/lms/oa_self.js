/**
 Tests for OpenAssessment Self view.
 **/

describe("OpenAssessment.SelfView", function() {

    // Stub server
    var StubServer = function() {
        var successPromise = $.Deferred(
            function(defer) {
                defer.resolve();
            }
        ).promise();

        this.selfAssess = function(optionsSelected) {
            return $.Deferred(function(defer) { defer.resolve(); }).promise();
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
        this.loadAssessmentModules = function() {};
        this.scrollToTop = function() {};
    };

    // Stubs
    var baseView = null;
    var server = null;

    // View under test
    var view = null;

    beforeEach(function() {
        // Load the DOM fixture
        loadFixtures('oa_self_assessment.html');

        // Create a new stub server
        server = new StubServer();

        // Create the stub base view
        baseView = new StubBaseView();

        // Create the object under test
        var el = $("#openassessment").get(0);
        view = new OpenAssessment.SelfView(el, server, baseView);
        view.installHandlers();
    });

    it("Sends a self assessment to the server", function() {
        spyOn(server, 'selfAssess').and.callThrough();

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

        view.selfAssess();
        expect(server.selfAssess).toHaveBeenCalledWith(
            optionsSelected, criterionFeedback, overallFeedback
        );
    });

    it("Re-enables the self assess button on error", function() {
        // Simulate a server error
        spyOn(server, 'selfAssess').and.callFake(function() {
            expect(view.selfSubmitEnabled()).toBe(false);
            return $.Deferred(function(defer) {
                defer.rejectWith(this, ['ENOUNKNOWN', 'Error occurred!']);
            }).promise();
        });
        view.selfAssess();

        // Expect the submit button to have been re-enabled
        expect(view.selfSubmitEnabled()).toBe(true);
    });
});
