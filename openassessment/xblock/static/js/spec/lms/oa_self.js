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

    // Stubs
    var runtime = {};
    var server = null;

    // View under test
    var view = null;

    beforeEach(function() {
        // Load the DOM fixture
        loadFixtures('oa_self_assessment.html');

        // Create a new stub server
        server = new StubServer();
        server.renderLatex = jasmine.createSpy('renderLatex');

        // Create the object under test
        var assessmentElement = $(".step--self-assessment").get(0);
        var baseView = new OpenAssessment.BaseView(runtime, assessmentElement, server, {});
        view = new OpenAssessment.SelfView(assessmentElement, server, baseView);
        view.installHandlers();
    });

    afterEach(function() {
        OpenAssessment.clearUnsavedChanges();
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

    it("warns of unsubmitted assessments", function() {

        expect(view.baseView.unsavedWarningEnabled()).toBe(false);

        // Click on radio buttons, to create unsubmitted changes.
        $('.question__answers', view.el).each(function() {
            $('input[type="radio"]', this).first().click();
        });

        expect(view.baseView.unsavedWarningEnabled()).toBe(true);

        // When selfAssess is executed, the views will all re-render. However,
        // as the test does not mock out the surrounding elements, the re-render
        // of the self assessment module will keep the original HTML intact (with selected
        // options), causing the unsavedWarnings callback to be triggered again (after it is properly
        // cleared during the submit operation). To avoid this, have the view re-render fail.
        server.render = function() {
            return $.Deferred(
                function(defer) {
                    defer.fail();
                }
            ).promise();
        };

        view.selfAssess();

        expect(view.baseView.unsavedWarningEnabled()).toBe(false);
    });
});
