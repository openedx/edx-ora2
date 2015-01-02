/**
Tests for OpenAssessment response (submission) view.
**/

describe("OpenAssessment.ResponseView", function() {

    var FAKE_URL = "http://www.example.com";

    var StubServer = function() {

        var successPromise = $.Deferred(
            function(defer) { defer.resolve(); }
        ).promise();

        var successPromiseWithUrl = $.Deferred(
            function(defer) { defer.resolveWith(this, [FAKE_URL]); }
        ).promise();

        var errorPromise = $.Deferred(
            function(defer) { defer.rejectWith(this, ["ERROR"]); }
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

        this.uploadUrlError = false;
        this.getUploadUrl = function(contentType) {
            return this.uploadUrlError ? errorPromise : successPromiseWithUrl;
        };

        this.getDownloadUrl = function() {
            return successPromiseWithUrl;
        };

    };

    var StubFileUploader = function() {
        var successPromise = $.Deferred(function(defer) { defer.resolve(); }).promise();
        var errorPromise = $.Deferred(function(defer) { defer.rejectWith(this, ["ERROR"]); }).promise();

        this.uploadError = false;
        this.uploadArgs = null;

        this.upload = function(url, data) {
            // Store the args we were passed so we can verify them
            this.uploadArgs = {
                url: url,
                data: data,
            };

            // Return a promise indicating success or error
            return this.uploadError ? errorPromise : successPromise;
        };
    };

    var StubBaseView = function() {
        this.loadAssessmentModules = function() {};
        this.peerView = { load: function() {} };
        this.gradeView = { load: function() {} };
        this.showLoadError = function(msg) {};
        this.toggleActionError = function(msg, step) {};
        this.setUpCollapseExpand = function(sel) {};
    };

    // Stubs
    var baseView = null;
    var server = null;
    var fileUploader = null;

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
        loadFixtures('oa_response.html');

        // Create stub objects
        server = new StubServer();
        server.renderLatex = jasmine.createSpy('renderLatex')
        fileUploader = new StubFileUploader();
        baseView = new StubBaseView();

        // Create and install the view
        var el = $('#openassessment-base').get(0);
        view = new OpenAssessment.ResponseView(el, server, fileUploader, baseView);
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

    afterEach(function() {
        // Disable autosave polling (if it was enabled)
        view.setAutoSaveEnabled(false);
    });

    it("updates and retrieves response text correctly", function() {
        view.response(['Test response 1', 'Test response 2']);
        expect(view.response()[0]).toBe('Test response 1');
        expect(view.response()[1]).toBe('Test response 2');
    });

    it("updates submit/save buttons and save status when response text changes", function() {
        // Response is blank --> save/submit buttons disabled
        view.response(['', '']);
        view.handleResponseChanged();
        expect(view.submitEnabled()).toBe(false);
        expect(view.saveEnabled()).toBe(false);
        expect(view.saveStatus()).toContain('This response has not been saved.');

        // Response is whitespace --> save/submit buttons disabled
        view.response(['               \n      \n      ', ' ']);
        view.handleResponseChanged();
        expect(view.submitEnabled()).toBe(false);
        expect(view.saveEnabled()).toBe(false);
        expect(view.saveStatus()).toContain('This response has not been saved.');

        // Response is not blank --> submit button enabled
        view.response(['Test response 1', ' ']);
        view.handleResponseChanged();
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
        view.response(['Test response 1', 'Test response 2']);
        view.save();
        expect(view.submitEnabled()).toBe(true);
        expect(view.saveEnabled()).toBe(false);
        expect(view.saveStatus()).toContain('saved but not submitted');
    });

    it("shows unsaved draft only when response text has changed", function() {
        // Save the initial response
        view.response(['Test response 1', 'Test response 2']);
        view.save();
        expect(view.saveEnabled()).toBe(false);
        expect(view.saveStatus()).toContain('saved but not submitted');

        // Keep the text the same, but trigger an update
        // Should still be saved
        view.response(['Test response 1', 'Test response 2']);
        view.handleResponseChanged();
        expect(view.saveEnabled()).toBe(false);
        expect(view.saveStatus()).toContain('saved but not submitted');

        // Change the text
        // This should cause it to change to unsaved draft
        view.response(['Test response 1', 'Test response 3']);
        view.handleResponseChanged();
        expect(view.saveEnabled()).toBe(true);
        expect(view.saveStatus()).toContain('This response has not been saved.');
    });

    it("sends the saved submission to the server", function() {
        spyOn(server, 'save').andCallThrough();
        view.response(['Test response 1', 'Test response 2']);
        view.save();
        expect(server.save).toHaveBeenCalledWith(['Test response 1', 'Test response 2']);
    });

    it("submits a response to the server", function() {
        spyOn(server, 'submit').andCallThrough();
        view.response(['Test response 1', 'Test response 2']);
        view.submit();
        expect(server.submit).toHaveBeenCalledWith(['Test response 1', 'Test response 2']);
    });

    it("allows the user to cancel before submitting", function() {
        // Simulate the user cancelling the submission
        setStubConfirm(false);
        spyOn(server, 'submit').andCallThrough();

        // Start a submission
        view.response(['Test response 1', 'Test response 2']);
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

        view.response(['Test response 1', 'Test response 2']);
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

        view.response(['Test response 1', 'Test response 2']);
        view.submit();

        // Expect the submit button to have been re-enabled
        expect(view.submitEnabled()).toBe(true);
    });

    it("re-enables the submit button after cancelling", function() {
        // Simulate the user cancelling the submission
        setStubConfirm(false);
        spyOn(server, 'submit').andCallThrough();

        // Start a submission
        view.response(['Test response 1', 'Test response 2']);
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
        spyOn(baseView, 'loadAssessmentModules');

        view.response(['Test response 1', 'Test response 2']);
        view.submit();

        // Expect the current and next step to have been reloaded
        expect(view.load).toHaveBeenCalled();
        expect(baseView.loadAssessmentModules).toHaveBeenCalled();
    });

    it("enables the unsaved work warning when the user changes the response text", function() {
        // Initially, the unsaved work warning should be disabled
        expect(view.unsavedWarningEnabled()).toBe(false);

        // Change the text, then expect the unsaved warning to be enabled.
        view.response(['Lorem ipsum 1', 'Lorem ipsum 2']);
        view.handleResponseChanged();

        // Expect the unsaved work warning to be enabled
        expect(view.unsavedWarningEnabled()).toBe(true);
    });

    it("disables the unsaved work warning when the user saves a response", function() {
        // Change the text, then expect the unsaved warning to be enabled.
        view.response(['Lorem ipsum 1', 'Lorem ipsum 2']);
        view.handleResponseChanged();
        expect(view.unsavedWarningEnabled()).toBe(true);

        // Save the response and expect the unsaved warning to be disabled
        view.save();
        expect(view.unsavedWarningEnabled()).toBe(false);
    });

    it("disables the unsaved work warning when the user submits a response", function() {
        // Change the text, then expect the unsaved warning to be enabled.
        view.response(['Lorem ipsum 1', 'Lorem ipsum 2']);
        view.handleResponseChanged();
        expect(view.unsavedWarningEnabled()).toBe(true);

        // Submit the response and expect the unsaved warning to be disabled
        view.submit();
        expect(view.unsavedWarningEnabled()).toBe(false);
    });

    it("autosaves after a user changes a response", function() {
        // Disable the autosave delay after changing/saving a response
        view.AUTO_SAVE_WAIT = -1;

        // Check that the problem is initially unsaved
        expect(view.saveStatus()).toContain('not been saved');

        // Change the response
        view.response(['Lorem ipsum 1', 'Lorem ipsum 2']);
        view.handleResponseChanged();

        // Usually autosave would be called by a timer.
        // For testing purposes, we disable the timer
        // and trigger the autosave manually.
        view.autoSave();

        // Expect that the problem has been saved
        expect(view.saveStatus()).toContain('saved but not submitted');

        // Expect that the unsaved warning is disabled
        expect(view.unsavedWarningEnabled()).toBe(false);
    });

    it("schedules autosave polling", function() {
        runs(function() {
            // Spy on the autosave call
            spyOn(view, 'autoSave').andCallThrough();

            // Enable autosave with a short poll interval
            view.AUTO_SAVE_POLL_INTERVAL = 1;
            view.setAutoSaveEnabled(true);
        });

        // Wait for autosave to be called
        waitsFor(function() {
            return view.autoSave.callCount > 0;
        }, "AutoSave should have been called", 5000);
    });

    it("stops autosaving after a save error", function() {
        // Disable the autosave delay after changing/saving a response
        view.AUTO_SAVE_WAIT = -1;

        // Simulate a server error
        var errorPromise = $.Deferred(function(defer) {
            defer.rejectWith(this, ["This response could not be saved"]);
        }).promise();
        spyOn(server, 'save').andCallFake(function() { return errorPromise; });

        // Change the response and save it
        view.response(['Lorem ipsum 1', 'Lorem ipsum 2']);
        view.handleResponseChanged();
        view.save();

        // Expect that the save status shows an error
        expect(view.saveStatus()).toContain('Error');

        // Autosave (usually would be called by a timer, but we disable
        // that for testing purposes).
        view.autoSave();

        // The server save shoulde have been called just once
        // (autosave didn't call it).
        expect(server.save.callCount).toEqual(1);
    });

    it("waits after user changes a response to autosave", function() {
        // Set a long autosave delay
        view.AUTO_SAVE_WAIT = 900000;

        // Change the response
        view.response(['Lorem ipsum 1', 'Lorem ipsum 2']);
        view.handleResponseChanged();

        // Autosave
        view.autoSave();

        // Expect that the problem is still unsaved
        expect(view.saveStatus()).toContain('not been saved');
    });

    it("does not autosave if a user hasn't changed the response", function() {
        // Disable the autosave delay after changing/saving a response
        view.AUTO_SAVE_WAIT = -1;

        // Autosave (usually would be called by a timer, but we disable
        // that for testing purposes).
        view.autoSave();

        // Since we haven't made any changes, the response should still be unsaved.
        expect(view.saveStatus()).toContain('not been saved');
    });

    it("selects too large of a file", function() {
        spyOn(baseView, 'toggleActionError').andCallThrough();
        var files = [{type: 'image/jpg', size: 6000000, name: 'huge-picture.jpg', data: ''}];
        view.prepareUpload(files);
        expect(baseView.toggleActionError).toHaveBeenCalledWith('upload', 'File size must be 5MB or less.');
    });

    it("selects the wrong file type", function() {
        spyOn(baseView, 'toggleActionError').andCallThrough();
        var files = [{type: 'bogus/jpg', size: 1024, name: 'picture.exe', data: ''}];
        view.prepareUpload(files);
        expect(baseView.toggleActionError).toHaveBeenCalledWith('upload', 'File must be an image.');
    });

    it("uploads a file using a one-time URL", function() {
        var files = [{type: 'image/jpg', size: 1024, name: 'picture.jpg', data: ''}];
        view.prepareUpload(files);
        view.fileUpload();
        expect(fileUploader.uploadArgs.url).toEqual(FAKE_URL);
        expect(fileUploader.uploadArgs.data).toEqual(files[0]);
    });

    it("displays an error if a one-time file upload URL cannot be retrieved", function() {
        // Configure the server to fail when retrieving the one-time URL
        server.uploadUrlError = true;
        spyOn(baseView, 'toggleActionError').andCallThrough();

        // Attempt to upload a file
        var files = [{type: 'image/jpg', size: 1024, name: 'picture.jpg', data: ''}];
        view.prepareUpload(files);
        view.fileUpload();

        // Expect an error to be displayed
        expect(baseView.toggleActionError).toHaveBeenCalledWith('upload', 'ERROR');
    });

    it("displays an error if a file could not be uploaded", function() {
        // Configure the file upload server to return an error
        fileUploader.uploadError = true;
        spyOn(baseView, 'toggleActionError').andCallThrough();

        // Attempt to upload a file
        var files = [{type: 'image/jpg', size: 1024, name: 'picture.jpg', data: ''}];
        view.prepareUpload(files);
        view.fileUpload();

        // Expect an error to be displayed
        expect(baseView.toggleActionError).toHaveBeenCalledWith('upload', 'ERROR');
    });
});
