/**
Tests for OpenAssessment response (submission) view.
**/

describe("OpenAssessment.ResponseView", function() {

    // Stub server
    var StubServer = function() {
        var successPromise = $.Deferred(
            function(defer) {
                defer.resolve();
            }
        ).promise();

        this.save = function(submission) {
            return successPromise;
        };

        this.submit = function(submission) {
            return successPromise;
        };

        this.render = function(step) {
            return successPromise;
        };
    };

    // Stub base view
    var StubBaseView = function() {
        this.gradeView = {
            load: function(){}
        };
        this.showLoadError = function(msg) {};
        this.toggleActionError = function(msg, step) {};
        this.setUpCollapseExpand = function(sel) {};
        this.renderPeerAssessmentStep = function() {};
    };

    // Stubs
    var baseView = null;
    var server = null;

    // View under test
    var view = null;

    // Control whether the confirmation stub
    // simulates a user confirming the submission or cancelling it.
    var stubConfirm = true;

    /**
    Set whether the user confirms or cancels the submission.

    Args:
        didConfirm(bool): If true, simulate that the user confirmed the submission;
            otherwise, simulate that the user cancelled the submission.
    **/
    var setStubConfirm = function(didConfirm) {
        stubConfirm = didConfirm;
    };

    beforeEach(function() {
        // Load the DOM fixture
        jasmine.getFixtures().fixturesPath = 'base/fixtures';
        loadFixtures('oa_response.html');

        // Create the stub server
        server = new StubServer();

        // Create the stub base view
        baseView = new StubBaseView();

        // Create and install the view
        var el = $('#openassessment-base').get(0);
        view = new OpenAssessment.ResponseView(el, server, baseView);
        view.installHandlers();

        // Stub the confirmation step
        // By default, we simulate the user confirming the submission.
        // To instead simulate the user cancelling the submission,
        // set `stubConfirm` to false.
        setStubConfirm(true);
        spyOn(view, 'confirmSubmission').andCallFake(function() {
            return $.Deferred(function(defer) {
                if (stubConfirm) { defer.resolve(); }
                else { defer.reject(); }
            });
        });
    });

    it("updates submit/save buttons and save status when response text changes", function() {
        // Response is blank --> save/submit buttons disabled
        view.response('');
        view.responseChanged();
        expect(view.submitEnabled()).toBe(false);
        expect(view.saveEnabled()).toBe(false);
        expect(view.saveStatus()).toContain('This response has not been saved.');

        // Response is whitespace --> save/submit buttons disabled
        view.response('               \n      \n      ');
        view.responseChanged();
        expect(view.submitEnabled()).toBe(false);
        expect(view.saveEnabled()).toBe(false);
        expect(view.saveStatus()).toContain('This response has not been saved.');

        // Response is not blank --> submit button enabled
        view.response('Test response');
        view.responseChanged();
        expect(view.submitEnabled()).toBe(true);
        expect(view.saveEnabled()).toBe(true);
        expect(view.saveStatus()).toContain('This response has not been saved.');
    });

    it("updates submit/save buttons and save status when the user saves a response", function() {
        // Response is blank --> save/submit button is disabled
        view.response('');
        view.save();
        expect(view.submitEnabled()).toBe(false);
        expect(view.saveEnabled()).toBe(false);
        expect(view.saveStatus()).toContain('saved but not submitted');

        // Response is not blank --> submit button enabled
        view.response('Test response');
        view.save();
        expect(view.submitEnabled()).toBe(true);
        expect(view.saveEnabled()).toBe(false);
        expect(view.saveStatus()).toContain('saved but not submitted');
    });

    it("shows unsaved draft only when response text has changed", function() {
        // Save the initial response
        view.response('Lorem ipsum');
        view.save();
        expect(view.saveEnabled()).toBe(false);
        expect(view.saveStatus()).toContain('saved but not submitted');

        // Keep the text the same, but trigger an update
        // Should still be saved
        view.response('Lorem ipsum');
        view.responseChanged();
        expect(view.saveEnabled()).toBe(false);
        expect(view.saveStatus()).toContain('saved but not submitted');

        // Change the text
        // This should cause it to change to unsaved draft
        view.response('changed ');
        view.responseChanged();
        expect(view.saveEnabled()).toBe(true);
        expect(view.saveStatus()).toContain('This response has not been saved.');
    });

    it("sends the saved submission to the server", function() {
        spyOn(server, 'save').andCallThrough();
        view.response('Test response');
        view.save();
        expect(server.save).toHaveBeenCalledWith('Test response');
    });

    it("submits a response to the server", function() {
        spyOn(server, 'submit').andCallThrough();
        view.response('Test response');
        view.submit();
        expect(server.submit).toHaveBeenCalledWith('Test response');
    });

    it("allows the user to cancel before submitting", function() {
        // Simulate the user cancelling the submission
        setStubConfirm(false);
        spyOn(server, 'submit').andCallThrough();

        // Start a submission
        view.response('Test response');
        view.submit();

        // Expect that the submission was not sent to the server
        expect(server.submit).not.toHaveBeenCalled();
    });

    it("disables the submit button on submission", function() {
        // Prevent the server's response from resolving,
        // so we can see what happens before view gets re-rendered.
        spyOn(server, 'submit').andCallFake(function() {
            return $.Deferred(function(defer) {}).promise();
        });

        view.response('Test response');
        view.submit();
        expect(view.submitEnabled()).toBe(false);
    });

    it("re-enables the submit button on submission error", function() {
        // Simulate a server error
        spyOn(server, 'submit').andCallFake(function() {
            return $.Deferred(function(defer) {
                defer.rejectWith(this, ['ENOUNKNOWN', 'Error occurred!']);
            }).promise();
        });

        view.response('Test response');
        view.submit();

        // Expect the submit button to have been re-enabled
        expect(view.submitEnabled()).toBe(true);
    });

    it("re-enables the submit button after cancelling", function() {
        // Simulate the user cancelling the submission
        setStubConfirm(false);
        spyOn(server, 'submit').andCallThrough();

        // Start a submission
        view.response('Test response');
        view.submit();

        // Expect the submit button to be re-enabled
        expect(view.submitEnabled()).toBe(true);
    });

    it("moves to the next step on duplicate submission error", function() {
        // Simulate a "multiple submissions" server error
        spyOn(server, 'submit').andCallFake(function() {
            return $.Deferred(function(defer) {
                defer.rejectWith(this, ['ENOMULTI', 'Multiple submissions error']);
            }).promise();
        });
        spyOn(view, 'load');
        spyOn(baseView, 'renderPeerAssessmentStep');

        view.response('Test response');
        view.submit();

        // Expect the current and next step to have been reloaded
        expect(view.load).toHaveBeenCalled();
        expect(baseView.renderPeerAssessmentStep).toHaveBeenCalled();
    });

    it("enables the unsaved work warning when the user changes the response text", function() {
        // Initially, the unsaved work warning should be disabled
        expect(view.unsavedWarningEnabled()).toBe(false);

        // Change the text, then expect the unsaved warning to be enabled.
        view.response('Lorem ipsum');
        view.responseChanged();

        // Expect the unsaved work warning to be enabled
        expect(view.unsavedWarningEnabled()).toBe(true);
    });

    it("disables the unsaved work warning when the user saves a response", function() {
        // Change the text, then expect the unsaved warning to be enabled.
        view.response('Lorem ipsum');
        view.responseChanged();
        expect(view.unsavedWarningEnabled()).toBe(true);

        // Save the response and expect the unsaved warning to be disabled
        view.save();
        expect(view.unsavedWarningEnabled()).toBe(false);
    });

    it("disables the unsaved work warning when the user submits a response", function() {
        // Change the text, then expect the unsaved warning to be enabled.
        view.response('Lorem ipsum');
        view.responseChanged();
        expect(view.unsavedWarningEnabled()).toBe(true);

        // Submit the response and expect the unsaved warning to be disabled
        view.submit();
        expect(view.unsavedWarningEnabled()).toBe(false);
    });
});
