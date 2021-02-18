/* eslint-disable */
import BaseView from 'lms/oa_base';
import ResponseView from 'lms/oa_response';

/**
Tests for OpenAssessment response (submission) view.
**/

describe("OpenAssessment.ResponseView", function() {

    var FAKE_URL = "http://www.example.com";
    var ALLOWED_IMAGE_MIME_TYPES = [
        'image/gif',
        'image/jpeg',
        'image/pjpeg',
        'image/png'
    ];

    var ALLOWED_FILE_MIME_TYPES = [
        'application/pdf',
        'image/gif',
        'image/jpeg',
        'image/pjpeg',
        'image/png'
    ];

    var FILE_TYPE_WHITE_LIST = ['pdf', 'doc', 'docx', 'html'];
    var FILE_EXT_BLACK_LIST = ['exe', 'msi', 'app', 'dmg'];
    var MAXIMUM_FILE_UPLOAD_COUNT = 20;
    var COURSE_ID = 'course_id';

    var BAD_FILETYPE_MESSAGE = 'File upload failed: unsupported file type. ' +
        'Only the supported file types can be uploaded. If you have questions, please reach out to the course team.';

    var StubServer = function() {

        var successPromise = $.Deferred(
            function(defer) { defer.resolve(); }
        ).promise();

        var successPromiseWithResult = function(result){
            return $.Deferred(
                function(defer) { defer.resolveWith(this, [result]); }
            ).promise();
        }

        var successPromiseWithUrl = successPromiseWithResult(FAKE_URL)

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

        this.removeFileError = false
        this.removeUploadedFile = function() {
            return this.removeFileError ? errorPromise : successPromise;;
        }

        this.teamListError = false
        this.listTeamsResult = {name: 'TeamName', id:'TeamId'}
        this.listTeams = function(username, courseId) {
            if (this.teamListError) {
                return errorPromise
            } else {
                return successPromiseWithResult(this.listTeamsResult)
            };
        }

        this.teamDetailError = false
        this.teamDetailResult = {
            id: 'TeamId',
            name: 'TeamName',
            course_id: 'CourseID',
            topic_id: 'TopicID',
            description: "A team!",
            membership: [{user: {username: 'user1'}}, {user: {username: 'user2'}}, {user: {username: 'user3'}}]
        }
        this.getTeamDetail = function(teamId) {
            if (this.teamDetailError) {
                return errorPromise
            } else {
                return successPromiseWithResult(this.teamDetailResult);
            }
        }

        this.getUsernameError = false
        this.getUsername = function() {
            return this.getUsernameError ? errorPromise : successPromiseWithResult('this-is-my-username')
        }
    };

    var StubFileUploader = function() {
        var successPromise = $.Deferred(function(defer) { defer.resolve(); }).promise();
        var errorPromise = $.Deferred(function(defer) { defer.rejectWith(this, ["ERROR"]); }).promise();

        this.uploadError = false;
        this.uploadArgs = [];

        this.upload = function(url, data) {
            // Store the args we were passed so we can verify them
            this.uploadArgs.push({
                url: url,
                data: data
            });

            // Return a promise indicating success or error
            return this.uploadError ? errorPromise : successPromise;
        };
    };

    // Stubs
    var server = null;
    var runtime = {};
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

    // Store window URL object for replacing after tests;
    const windowURL = window.URL;
    const mockURL = {
      createObjectURL: () => 'url',
    };

    beforeEach(function(done) {
        // Load the DOM fixture
        loadFixtures('oa_response.html');

        // Create stub objects
        server = new StubServer();
        server.renderLatex = jasmine.createSpy('renderLatex');
        fileUploader = new StubFileUploader();
        data = {
            "ALLOWED_IMAGE_MIME_TYPES": ALLOWED_IMAGE_MIME_TYPES,
            "ALLOWED_FILE_MIME_TYPES": ALLOWED_FILE_MIME_TYPES,
            "FILE_TYPE_WHITE_LIST": FILE_TYPE_WHITE_LIST,
            "FILE_EXT_BLACK_LIST": FILE_EXT_BLACK_LIST,
            "MAXIMUM_FILE_UPLOAD_COUNT": MAXIMUM_FILE_UPLOAD_COUNT,
            "COURSE_ID": COURSE_ID,
            "TEAM_ASSIGNMENT": true,
            "TEXT_RESPONSE_EDITOR": 'text',
            "AVAILABLE_EDITORS": {
                'text': {
                    'js': ['/base/js/src/lms/editors/oa_editor_textarea.js']
                }
            }
        };

        // Create and install the view
        var rootElement = $('.step--response').parent().get(0);
        var baseView = new BaseView(runtime, rootElement, server, data);
        view = new ResponseView(rootElement, server, fileUploader, baseView.responseEditorLoader, baseView, data);
        view.loadResponseEditor().then(editorCtrl => {
            view.responseEditorController = editorCtrl
            view.installHandlers()

            // Stub the confirmation step
            // By default, we simulate the user confirming the submission.
            // To instead simulate the user cancelling the submission,
            // set `stubConfirm` to false.
            setStubConfirm(true);
            const fakeConfirm = function() { return stubConfirm; }
            spyOn(view, 'confirmSubmission').and.callFake(fakeConfirm);
            spyOn(view, 'confirmRemoveUploadedFile').and.callFake(fakeConfirm);
            spyOn(view, 'saveFilesDescriptions').and.callFake(function() {
                for (var i=0; i < this.filesDescriptions.length; i++) {
                    this.fileNames.push(this.files[i].name);
                }
                return $.Deferred(function(defer) {
                    view.removeFilesDescriptions();
                    defer.resolve();
                });
            });
            window.URL = mockURL;

            done()
        })
    });

    afterEach(function() {
        // Disable autosave polling (if it was enabled)
        view.setAutoSaveEnabled(false);

        // Disable the unsaved page warning (if set)
        view.baseView.clearUnsavedChanges();

        window.URL = windowURL;
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

    it("updates submit/save buttons when response text is optional but file upload is required", function() {
        view.textResponse = 'optional';
        view.fileUploadResponse = 'required';

        expect(view.submitEnabled()).toBe(false);
        expect(view.saveEnabled()).toBe(false);

        var files = [{type: 'application/pdf', size: 1024, name: 'application.pdf', data: ''}];
        view.prepareUpload(files, 'pdf-and-image', ['test description']);
        view.uploadFiles();
        view.checkSubmissionAbility(true);

        expect(view.submitEnabled()).toBe(true);
    });

    it("updates save buttons when response text is optional and input is empty", function() {
        view.textResponse = 'optional';
        view.fileUploadResponse = 'required';

        expect(view.submitEnabled()).toBe(false);
        expect(view.saveEnabled()).toBe(false);

        view.response(['Test response 1', ' ']);
        view.handleResponseChanged();

        expect(view.saveEnabled()).toBe(true);
        view.save();

        expect(view.submitEnabled()).toBe(false);
        expect(view.saveEnabled()).toBe(false);

        view.response(['', '']);
        view.handleResponseChanged();
        expect(view.saveEnabled()).toBe(true);
    });

    it("doesn't allow to push submit button if response text and file upload are both optional and input fields are empty ", function() {
        view.textResponse = 'optional';
        view.fileUploadResponse = 'optional';

        view.response(['', '']);
        view.handleResponseChanged();

        expect(view.submitEnabled()).toBe(false);

        var files = [{type: 'application/pdf', size: 1024, name: 'application.pdf', data: ''}];
        view.prepareUpload(files, 'pdf-and-image', ['test description']);
        view.uploadFiles();
        view.checkSubmissionAbility(true);

        expect(view.submitEnabled()).toBe(true);
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
        spyOn(view.baseView, 'loadAssessmentModules');

        view.response(['Test response 1', 'Test response 2']);
        view.submit();

        // Expect the current and next step to have been reloaded
        expect(view.load).toHaveBeenCalled();
        expect(view.baseView.loadAssessmentModules).toHaveBeenCalled();
    });

    it("enables the unsaved work warning when the user changes the response text", function() {
        // Initially, the unsaved work warning should be disabled
        expect(view.baseView.unsavedWarningEnabled()).toBe(false);

        // Change the text, then expect the unsaved warning to be enabled.
        view.response(['Lorem ipsum 1', 'Lorem ipsum 2']);
        view.handleResponseChanged();

        // Expect the unsaved work warning to be enabled
        expect(view.baseView.unsavedWarningEnabled()).toBe(true);
    });

    it("disables the unsaved work warning when the user saves a response", function() {
        // Change the text, then expect the unsaved warning to be enabled.
        view.response(['Lorem ipsum 1', 'Lorem ipsum 2']);
        view.handleResponseChanged();
        expect(view.baseView.unsavedWarningEnabled()).toBe(true);

        // Save the response and expect the unsaved warning to be disabled
        view.save();
        expect(view.baseView.unsavedWarningEnabled()).toBe(false);
    });

    it("disables the unsaved work warning when the user submits a response", function() {
        // Change the text, then expect the unsaved warning to be enabled.
        view.response(['Lorem ipsum 1', 'Lorem ipsum 2']);
        view.handleResponseChanged();
        expect(view.baseView.unsavedWarningEnabled()).toBe(true);

        // Submit the response and expect the unsaved warning to be disabled
        view.submit();
        expect(view.baseView.unsavedWarningEnabled()).toBe(false);
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
            expect(view.baseView.unsavedWarningEnabled()).toBe(false);
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
        spyOn(view.baseView, 'toggleActionError').and.callThrough();
        var files = [{type: 'image/jpeg', size: 544288000, name: 'huge-picture.jpg', data: ''}];
        view.prepareUpload(files, 'image');
        expect(view.baseView.toggleActionError).toHaveBeenCalledWith('upload',
            'Individual file size must be 500MB or less.');
    });

    it("selects the wrong image file type", function() {
        spyOn(view.baseView, 'toggleActionError').and.callThrough();
        var files = [{type: 'image/jpg', size: 1024, name: 'picture.exe', data: ''}];
        view.prepareUpload(files, 'image');
        expect(view.baseView.toggleActionError).toHaveBeenCalledWith(
            'upload', BAD_FILETYPE_MESSAGE
        );
    });

    it("selects the wrong pdf or image file type", function() {
        spyOn(view.baseView, 'toggleActionError').and.callThrough();
        var files = [{type: 'application/exe', size: 1024, name: 'application.exe', data: ''}];
        view.prepareUpload(files, 'pdf-and-image');
        expect(view.baseView.toggleActionError).toHaveBeenCalledWith(
            'upload', BAD_FILETYPE_MESSAGE
        );
    });

    it("selects the wrong file extension", function() {
        spyOn(view.baseView, 'toggleActionError').and.callThrough();
        var files = [{type: 'application/exe', size: 1024, name: 'application.exe', data: ''}];
        view.prepareUpload(files, 'custom');
        expect(view.baseView.toggleActionError).toHaveBeenCalledWith(
            'upload', BAD_FILETYPE_MESSAGE
        );
    });

    it("submits a file with extension in the black list", function() {
        spyOn(view.baseView, 'toggleActionError').and.callThrough();
        view.data.FILE_TYPE_WHITE_LIST = ['exe'];
        var files = [{type: 'application/exe', size: 1024, name: 'application.exe', data: ''}];
        view.prepareUpload(files, 'custom');
        expect(view.baseView.toggleActionError).toHaveBeenCalledWith('upload',
            BAD_FILETYPE_MESSAGE);
    });

    it("selects one small and one large file", function() {
        spyOn(view.baseView, 'toggleActionError').and.callThrough();
        var files = [{type: 'image/jpeg', size: 1024, name: 'small-picture.jpg', data: ''},
                     {type: 'image/jpeg', size: 544288000, name: 'huge-picture.jpg', data: ''}];
        view.prepareUpload(files, 'image');
        expect(view.baseView.toggleActionError).toHaveBeenCalledWith('upload',
            'Individual file size must be 500MB or less.');
    });

    it("selects three files - one with invalid extension", function() {
        spyOn(view.baseView, 'toggleActionError').and.callThrough();
        var files = [{type: 'image/jpeg', size: 1024, name: 'small-picture-1.jpg', data: ''},
                     {type: 'application/exe', size: 1024, name: 'application.exe', data: ''},
                     {type: 'image/jpeg', size: 1024, name: 'small-picture-2.jpg', data: ''}];
        view.prepareUpload(files, 'image');
        expect(view.baseView.toggleActionError).toHaveBeenCalledWith('upload',
            BAD_FILETYPE_MESSAGE);
    });

    it("uploads an image using a one-time URL", function() {
        var files = [{type: 'image/jpeg', size: 1024, name: 'picture.jpg', data: ''}];
        view.prepareUpload(files, 'image');
        view.uploadFiles();
        expect(fileUploader.uploadArgs[0].url).toEqual(FAKE_URL);
        expect(fileUploader.uploadArgs[0].data).toEqual(files[0]);
    });

    it("uploads two images using a one-time URL", function() {
        var files = [{type: 'image/jpeg', size: 1024, name: 'picture1.jpg', data: ''},
                     {type: 'image/jpeg', size: 1024, name: 'picture2.jpg', data: ''}];
        view.prepareUpload(files, 'image', ['text1', 'text2']);
        view.uploadFiles();
        expect(fileUploader.uploadArgs[0].url).toEqual(FAKE_URL);
        expect(fileUploader.uploadArgs[0].data).toEqual(files[0]);
        expect(fileUploader.uploadArgs[1].url).toEqual(FAKE_URL);
        expect(fileUploader.uploadArgs[1].data).toEqual(files[1]);
    });

    it("tests that new file uploads are appended", function() {
        view.textResponse = 'optional';
        view.fileUploadResponse = 'required';

        expect(view.submitEnabled()).toBe(false);

        // Upload files
        var files = [{type: 'image/jpeg', size: 1024, name: 'picture1.jpg', data: ''},
                     {type: 'image/jpeg', size: 1024, name: 'picture2.jpg', data: ''}];
        view.prepareUpload(files, 'image', ['i1', 'i2']);
        view.uploadFiles()
        view.checkSubmissionAbility(true);
        expect(view.submitEnabled()).toBe(true);
        expect(view.files.length).toEqual(2);
        view.prepareUpload(files, 'image', ['i1', 'i2']);
        view.uploadFiles()
        view.checkSubmissionAbility(true);
        expect(view.files.length).toEqual(2);
    });

    it("tests that file upload number can't exceed maximum", function() {
        spyOn(view.baseView, 'toggleActionError').and.callThrough();
        spyOn(view, 'getSavedFileCount').and.returnValue(20);
        view.textResponse = 'optional';
        view.fileUploadResponse = 'required';
        expect(view.submitEnabled()).toBe(false);
        var files = [];
        for(var i=0; i<20;i++) {
            files.push({type: 'image/jpeg', size: 1024, name: 'picture1.jpg', data: ''});
        }

        view.prepareUpload(files, 'image', ['i1', 'i2','i1', 'i2','i1', 'i2','i1', 'i2','i1', 'i2','i1', 'i2',
        'i1', 'i2','i1', 'i2','i1', 'i2','i1', 'i2',]);
        view.checkSubmissionAbility(true);
        expect(view.submitEnabled()).toBe(true);
        expect(view.getSavedFileCount()).toEqual(20);
        var files2 = [];
        for(i=0; i<2;i++) {
            files2.push({type: 'image/jpeg', size: 1024, name: 'picture1.jpg', data: ''});
        }
        view.prepareUpload(files2, 'image', ['i1', 'i2']);
        expect(view.baseView.toggleActionError).toHaveBeenCalledWith(
            'upload', 'Only ' + view.data.MAXIMUM_FILE_UPLOAD_COUNT +' files can be saved.');
    });

    it("tests that file upload works after file delete", function() {
        view.textResponse = 'optional';
        view.fileUploadResponse = 'required';

        expect(view.submitEnabled()).toBe(false);

        // Upload files
        var files = [{type: 'image/jpeg', size: 1024, name: 'picture1.jpg', data: ''},
                     {type: 'image/jpeg', size: 1024, name: 'picture2.jpg', data: ''}];
        view.prepareUpload(files, 'image', ['i1', 'i2']);
        view.uploadFiles()
        view.checkSubmissionAbility(true);
        expect(view.submitEnabled()).toBe(true);
        // Delete the first file
        view.removeUploadedFile(0);
        view.checkSubmissionAbility(true);
        expect(view.submitEnabled()).toBe(true);
        var fileNameAfterDelete = 'picture3.jpg';
        files = [{type: 'image/jpeg', size: 1024, name: fileNameAfterDelete, data: ''}];
        view.prepareUpload(files, 'image', ['i3']);
        view.uploadFiles();
        view.checkSubmissionAbility(true);
        // Ensure that view.fileNames and view.fileDescriptions only contain data about the newest set
        // of files uploaded files.
        expect(view.fileNames).toEqual(['picture3.jpg']);
        expect(view.filesDescriptions).toEqual(['i3']);
    });

    it("uploads a PDF using a one-time URL", function() {
        var files = [{type: 'application/pdf', size: 1024, name: 'application.pdf', data: ''}];
        view.prepareUpload(files, 'pdf-and-image', ['text']);
        view.uploadFiles();
        expect(fileUploader.uploadArgs[0].url).toEqual(FAKE_URL);
        expect(fileUploader.uploadArgs[0].data).toEqual(files[0]);
    });

    it("uploads a arbitrary type file using a one-time URL", function() {
        var files = [{type: 'text/html', size: 1024, name: 'index.html', data: ''}];
        view.prepareUpload(files, 'custom', ['text']);
        view.uploadFiles();
        expect(fileUploader.uploadArgs[0].url).toEqual(FAKE_URL);
        expect(fileUploader.uploadArgs[0].data).toEqual(files[0]);
    });

    it("displays an error if a one-time file upload URL cannot be retrieved", function() {
        // Configure the server to fail when retrieving the one-time URL
        server.uploadUrlError = true;
        spyOn(view.baseView, 'toggleActionError').and.callThrough();

        // Attempt to upload a file
        var files = [{type: 'image/jpeg', size: 1024, name: 'picture.jpg', data: ''}];
        view.prepareUpload(files, 'image', ['text']);
        view.uploadFiles();

        // Expect an error to be displayed
        expect(view.baseView.toggleActionError).toHaveBeenCalledWith('upload', 'ERROR');
    });

    it("displays an error if a file could not be uploaded", function() {
        // Configure the file upload server to return an error
        fileUploader.uploadError = true;
        spyOn(view.baseView, 'toggleActionError').and.callThrough();

        // Attempt to upload a file
        var files = [{type: 'image/jpeg', size: 1024, name: 'picture.jpg', data: ''}];
        view.prepareUpload(files, 'image');
        view.uploadFiles();

        // Expect an error to be displayed
        expect(view.baseView.toggleActionError).toHaveBeenCalledWith('upload', 'ERROR');
    });

    it("disables the upload button if any file description is not set", function() {
        function getFileUploadField() {
            return $(view.element).find('.file__upload').first();
        }
        function expectFileUploadButton(disabled) {
            view.collectFilesDescriptions();
            expect(getFileUploadField().is(':disabled')).toEqual(disabled);
        }

        spyOn(view, 'updateFilesDescriptionsFields').and.callThrough();
        var files = [{type: 'image/jpeg', size: 1024, name: 'picture1.jpg', data: ''},
                     {type: 'image/jpeg', size: 1024, name: 'picture2.jpg', data: ''}];
        view.prepareUpload(files, 'image');

        expect(getFileUploadField().is(':disabled')).toEqual(true);
        expect(view.updateFilesDescriptionsFields).toHaveBeenCalledWith(files, undefined, 'image');
        var firstDescriptionField1 = $(view.element).find('.file__description__0').first();
        var firstDescriptionField2 = $(view.element).find('.file__description__1').first();

        // Only set the first description field and the second field remain empty.
        // and check that upload button is disabled
        $(firstDescriptionField1).val('test1');
        $(firstDescriptionField2).val('');
        expectFileUploadButton(true);

        // Set the second description field to be only spaces (given first description has value).
        // and check that upload button is disabled
        $(firstDescriptionField2).val('  ');
        expectFileUploadButton(true)

        // Set the both description fields to contain only spaces.
        // and check that upload button is disabled
        $(firstDescriptionField1).val(' ');
        $(firstDescriptionField2).val(' ');
        expectFileUploadButton(true)

        // set the both description field to contain non empty values.
        // and check that upload button is enabled
        $(firstDescriptionField1).val('test1');
        $(firstDescriptionField2).val('test2');
        expectFileUploadButton(false)

        // remove value in the first upload field
        // and check that upload button is disabled
        $(firstDescriptionField1).val('');
        expectFileUploadButton(true)
    });

    it("removes description fields after files upload", function() {
        var files = [{type: 'image/jpeg', size: 1024, name: 'picture1.jpg', data: ''},
                     {type: 'image/jpeg', size: 1024, name: 'picture2.jpg', data: ''}];
        view.prepareUpload(files, 'image', ['test1', 'test2']);
        expect($(view.element).find('.file__description').length).toEqual(2);

        view.uploadFiles();
        expect($(view.element).find('.file__description').length).toEqual(0);
    });

    it("prevents user from submitting response when files selection is cancelled", function() {
        // Set fileupload to be required.
        view.fileUploadResponse = 'required';

        // Change the response text
        view.response(['Lorem ipsum 1', 'Lorem ipsum 2']);
        view.handleResponseChanged();
        // Expect the unsaved warning to be enabled and save progress button is enabled.
        expect(view.saveEnabled()).toBe(true);
        expect(view.saveStatus()).toContain('This response has not been saved.');

        // Assume user has selected no files (cancelled the file select pop-up) the event will
        // trigger with no files selected. Expect Submit response button is disabled.
        view.prepareUpload([], 'image', []);

        expect(view.submitEnabled()).toBe(false);

        // Expect there are no pending upload files & file upload button is disabled.
        expect(view.hasPendingUploadFiles()).toEqual(false);
        expect(view.files).toEqual(null);
        expect($(view.element).find('.file__upload').first().is(':disabled')).toEqual(true);
    });

     it("prevents user from uploading files when file is moved or deleted", function() {

         spyOn(view.baseView, 'toggleActionError').and.callThrough();
         view.fileUploadResponse = 'optional';

         var file = [{type: 'image/jpeg', size: 0, name: 'picture.jpg', data: ''}];
         view.prepareUpload(file, 'image', ['test1']);
         view.uploadFiles();

         expect(view.hasAllUploadFiles()).toEqual(false);
         expect(view.baseView.toggleActionError).toHaveBeenCalledWith('upload',
            "Your file " + file[0].name + " has been deleted or path has been changed.");
     });

    it("prevents user from uploading or submitting responses when file descriptions are missing", function() {
        view.textResponse = 'optional';
        view.fileUploadResponse = 'required';

        // initially, user can't submit because file is missing
        expect(view.submitEnabled()).toBe(false);
        expect(view.uploadEnabled()).toBe(false);

        // user selects some files to upload
        var files = [{type: 'image/jpeg', size: 1024, name: 'picture1.jpg', data: ''},
                     {type: 'image/jpeg', size: 1024, name: 'picture2.jpg', data: ''}];
        view.prepareUpload(files, 'image');

        // user selected some files to upload but missing descriptions causes submit to be disabled
        view.checkSubmissionAbility(true);
        expect(view.submitEnabled()).toBe(false);
        expect(view.uploadEnabled()).toBe(false);

        var firstDescriptionField1 = $(view.element).find('.file__description__0').first();
        var firstDescriptionField2 = $(view.element).find('.file__description__1').first();
        $(firstDescriptionField1).val('test1');
        $(firstDescriptionField2).val('');

        // adding some, but not all, descriptions causes submit to be disabled
        view.checkSubmissionAbility(true);
        expect(view.submitEnabled()).toBe(false);
        expect(view.uploadEnabled()).toBe(false);

        $(firstDescriptionField1).val('test1');
        $(firstDescriptionField2).val('test2');

        // user finishes adding descriptions which enables the upload button
        view.checkSubmissionAbility(true);
        expect(view.uploadEnabled()).toBe(true);

        // the submit button remains disabled until files are uploaded
        expect(view.submitEnabled()).toBe(false);
    });

    it("deleting all uploaded files prevents user from submitting", function() {
        view.textResponse = 'optional';
        view.fileUploadResponse = 'required';

        expect(view.submitEnabled()).toBe(false);

        // Upload files
        var files = [{type: 'image/jpeg', size: 1024, name: 'picture1.jpg', data: ''},
                     {type: 'image/jpeg', size: 1024, name: 'picture2.jpg', data: ''}];
        view.prepareUpload(files, 'image', ['i1', 'i2']);
        view.uploadFiles()
        view.checkSubmissionAbility(true);
        expect(view.submitEnabled()).toBe(true);

        // Delete the first file
        view.removeUploadedFile(0);
        view.checkSubmissionAbility(true);
        expect(view.submitEnabled()).toBe(true);

        // Delete the remaining file
        view.removeUploadedFile(1);
        expect(view.submitEnabled()).toBe(false);
    });

    it("doesn't delete file if user clicks no", function() {
        view.textResponse = 'optional';
        view.fileUploadResponse = 'required';

        expect(view.submitEnabled()).toBe(false);

        // Upload file
        var files = [{type: 'image/jpeg', size: 1024, name: 'picture1.jpg', data: ''}];
        view.prepareUpload(files, 'image', ['i1']);
        view.uploadFiles()
        view.checkSubmissionAbility(true);
        expect(view.submitEnabled()).toBe(true);

        // "Click" the delete button twice, cancelling both times.
        // The file should not be deleted either time.
        setStubConfirm(false);

        view.removeUploadedFile(0);
        view.checkSubmissionAbility(true);
        expect(view.submitEnabled()).toBe(true);

        view.removeUploadedFile(0);
        view.checkSubmissionAbility(true);
        expect(view.submitEnabled()).toBe(true);
    });

    it("displays an error if there is an error deleting a file", function() {
        view.textResponse = 'optional';
        view.fileUploadResponse = 'required';
        server.removeFileError = true;
        spyOn(view.baseView, 'toggleActionError').and.callThrough();

        // Upload a file
        var files = [{type: 'image/jpeg', size: 1024, name: 'picture.jpg', data: ''}];
        view.prepareUpload(files, 'image', ['text']);
        view.uploadFiles();

        // Attempt to delete the file
        view.removeUploadedFile(0);

        // Expect an error to be displayed
        expect(view.baseView.toggleActionError).toHaveBeenCalledWith('delete', 'ERROR');
    });
});
