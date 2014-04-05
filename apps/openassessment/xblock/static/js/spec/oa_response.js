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
});
