/**
Tests for OpenAssessment response (submission) view.
**/

describe("OpenAssessment.ResponseView", function() {

    var FAKE_URL = "http://www.example.com";
    var ALLOWED_IMAGE_MIME_TYPES = [
        'image/gif',
        'image/jpeg',
        'image/pjpeg',
        'image/png',
    ];

    var ALLOWED_FILE_MIME_TYPES = [
        'application/pdf',
        'image/gif',
        'image/jpeg',
        'image/pjpeg',
        'image/png',
    ];

    var FILE_TYPE_WHITE_LIST = ['pdf', 'doc', 'docx', 'html'];
    var FILE_EXT_BLACK_LIST = ['exe', 'msi', 'app', 'dmg'];

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

        this.save = function() {
            return successPromise;
        };

        this.submit = function() {
            return successPromise;
        };

        this.render = function() {
            return successPromise;
        };

        this.uploadUrlError = false;
        this.getUploadUrl = function() {
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
        this.showLoadError = function() {};
        this.toggleActionError = function() {};
        this.setUpCollapseExpand = function() {};
    };

    // Stubs
    var baseView = null;
    var server = null;
    var fileUploader = null;
    var data = null;

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
        server.renderLatex = jasmine.createSpy('renderLatex');
        fileUploader = new StubFileUploader();
        baseView = new StubBaseView();
        data = {
            "ALLOWED_IMAGE_MIME_TYPES": ALLOWED_IMAGE_MIME_TYPES,
            "ALLOWED_FILE_MIME_TYPES": ALLOWED_FILE_MIME_TYPES,
            "FILE_TYPE_WHITE_LIST": FILE_TYPE_WHITE_LIST,
            "FILE_EXT_BLACK_LIST": FILE_EXT_BLACK_LIST
        };

        // Create and install the view
        var el = $('#openassessment-base').get(0);
        view = new OpenAssessment.ResponseView(el, server, fileUploader, baseView, data);
        view.installHandlers();

        // Stub the confirmation step
        // By default, we simulate the user confirming the submission.
        // To instead simulate the user cancelling the submission,
        // set `stubConfirm` to false.
        setStubConfirm(true);
        spyOn(view, 'confirmSubmission').and.callFake(function() {
            return $.Deferred(function(defer) {
                if (stubConfirm) { defer.resolve(); }
                else { defer.reject(); }
            });
        });
    });

    afterEach(function() {
        // Disable autosave polling (if it was enabled)
        view.setAutoSaveEnabled(false);

        // Disable the unsaved page warning (if set)
        view.unsavedWarningEnabled(false);
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
        spyOn(server, 'save').and.callThrough();
        view.response(['Test response 1', 'Test response 2']);
        view.save();
        expect(server.save).toHaveBeenCalledWith(['Test response 1', 'Test response 2']);
    });

    it("submits a response to the server", function() {
        spyOn(server, 'submit').and.callThrough();
        view.response(['Test response 1', 'Test response 2']);
        view.submit();
        expect(server.submit).toHaveBeenCalledWith(['Test response 1', 'Test response 2']);
    });

    it("allows the user to cancel before submitting", function() {
        // Simulate the user cancelling the submission
        setStubConfirm(false);
        spyOn(server, 'submit').and.callThrough();

        // Start a submission
        view.response(['Test response 1', 'Test response 2']);
        view.submit();

        // Expect that the submission was not sent to the server
        expect(server.submit).not.toHaveBeenCalled();
    });

    it("disables the submit button on submission", function() {
        // Prevent the server's response from resolving,
        // so we can see what happens before view gets re-rendered.
        spyOn(server, 'submit').and.callFake(function() {
            return $.Deferred(function() {}).promise();
        });

        view.response(['Test response 1', 'Test response 2']);
        view.submit();
        expect(view.submitEnabled()).toBe(false);
    });

    it("re-enables the submit button on submission error", function() {
        // Simulate a server error
        spyOn(server, 'submit').and.callFake(function() {
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
        spyOn(server, 'submit').and.callThrough();

        // Start a submission
        view.response(['Test response 1', 'Test response 2']);
        view.submit();

        // Expect the submit button to be re-enabled
        expect(view.submitEnabled()).toBe(true);
    });

    it("moves to the next step on duplicate submission error", function() {
        // Simulate a "multiple submissions" server error
        spyOn(server, 'submit').and.callFake(function() {
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

    describe("auto save", function() {
       beforeEach(function() {
          jasmine.clock().install();
       });

        afterEach(function() {
            jasmine.clock().uninstall();
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
            // Spy on the autosave call
            spyOn(view, 'autoSave').and.callThrough();

            // Enable autosave with a short poll interval
            view.AUTO_SAVE_POLL_INTERVAL = 1;
            view.setAutoSaveEnabled(true);

            // Expect that auto save has happened after the poll interval
            jasmine.clock().tick(10);
            expect(view.autoSave.calls.count() > 0).toBeTruthy();
        });

        it("stops autosaving after a save error", function() {
            // Disable the autosave delay after changing/saving a response
            view.AUTO_SAVE_WAIT = -1;

            // Simulate a server error
            var errorPromise = $.Deferred(function(defer) {
                defer.rejectWith(this, ["This response could not be saved"]);
            }).promise();
            spyOn(server, 'save').and.callFake(function() { return errorPromise; });

            // Change the response and save it
            view.response(['Lorem ipsum 1', 'Lorem ipsum 2']);
            view.handleResponseChanged();
            view.save();

            // Expect that the save status shows an error
            expect(view.saveStatus()).toContain('Error');

            // Autosave (usually would be called by a timer, but we disable
            // that for testing purposes).
            view.autoSave();

            // The server save should have been called just once
            // (autosave didn't call it).
            expect(server.save.calls.count()).toEqual(1);
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

    });

    it("selects too large of a file", function() {
        spyOn(baseView, 'toggleActionError').and.callThrough();
        var files = [{type: 'image/jpeg', size: 6000000, name: 'huge-picture.jpg', data: ''}];
        view.prepareUpload(files, 'image');
        expect(baseView.toggleActionError).toHaveBeenCalledWith('upload', 'File size must be 5MB or less.');
    });

    it("selects the wrong image file type", function() {
        spyOn(baseView, 'toggleActionError').and.callThrough();
        var files = [{type: 'image/jpg', size: 1024, name: 'picture.exe', data: ''}];
        view.prepareUpload(files, 'image');
        expect(baseView.toggleActionError).toHaveBeenCalledWith('upload', 'You can upload files with these file types: JPG, PNG or GIF');
    });

    it("selects the wrong pdf or image file type", function() {
        spyOn(baseView, 'toggleActionError').and.callThrough();
        var files = [{type: 'application/exe', size: 1024, name: 'application.exe', data: ''}];
        view.prepareUpload(files, 'pdf-and-image');
        expect(baseView.toggleActionError).toHaveBeenCalledWith('upload', 'You can upload files with these file types: JPG, PNG, GIF or PDF');
    });

    it("selects the wrong file extension", function() {
        spyOn(baseView, 'toggleActionError').and.callThrough();
        var files = [{type: 'application/exe', size: 1024, name: 'application.exe', data: ''}];
        view.prepareUpload(files, 'custom');
        expect(baseView.toggleActionError).toHaveBeenCalledWith('upload', 'You can upload files with these file types: pdf, doc, docx, html');
    });

    it("submits a file with extension in the black list", function() {
        spyOn(baseView, 'toggleActionError').and.callThrough();
        view.data.FILE_TYPE_WHITE_LIST = ['exe'];
        var files = [{type: 'application/exe', size: 1024, name: 'application.exe', data: ''}];
        view.prepareUpload(files, 'custom');
        expect(baseView.toggleActionError).toHaveBeenCalledWith('upload', 'File type is not allowed.');
    });

    it("uploads an image using a one-time URL", function() {
        var files = [{type: 'image/jpeg', size: 1024, name: 'picture.jpg', data: ''}];
        view.prepareUpload(files, 'image');
        view.fileUpload();
        expect(fileUploader.uploadArgs.url).toEqual(FAKE_URL);
        expect(fileUploader.uploadArgs.data).toEqual(files[0]);
    });

    it("uploads a PDF using a one-time URL", function() {
        var files = [{type: 'application/pdf', size: 1024, name: 'application.pdf', data: ''}];
        view.prepareUpload(files, 'pdf-and-image');
        view.fileUpload();
        expect(fileUploader.uploadArgs.url).toEqual(FAKE_URL);
        expect(fileUploader.uploadArgs.data).toEqual(files[0]);
    });

    it("uploads a arbitrary type file using a one-time URL", function() {
        var files = [{type: 'text/html', size: 1024, name: 'index.html', data: ''}];
        view.prepareUpload(files, 'custom');
        view.fileUpload();
        expect(fileUploader.uploadArgs.url).toEqual(FAKE_URL);
        expect(fileUploader.uploadArgs.data).toEqual(files[0]);
    });

    it("displays an error if a one-time file upload URL cannot be retrieved", function() {
        // Configure the server to fail when retrieving the one-time URL
        server.uploadUrlError = true;
        spyOn(baseView, 'toggleActionError').and.callThrough();

        // Attempt to upload a file
        var files = [{type: 'image/jpeg', size: 1024, name: 'picture.jpg', data: ''}];
        view.prepareUpload(files, 'image');
        view.fileUpload();

        // Expect an error to be displayed
        expect(baseView.toggleActionError).toHaveBeenCalledWith('upload', 'ERROR');
    });

    it("displays an error if a file could not be uploaded", function() {
        // Configure the file upload server to return an error
        fileUploader.uploadError = true;
        spyOn(baseView, 'toggleActionError').and.callThrough();

        // Attempt to upload a file
        var files = [{type: 'image/jpeg', size: 1024, name: 'picture.jpg', data: ''}];
        view.prepareUpload(files, 'image');
        view.fileUpload();

        // Expect an error to be displayed
        expect(baseView.toggleActionError).toHaveBeenCalledWith('upload', 'ERROR');
    });
});
