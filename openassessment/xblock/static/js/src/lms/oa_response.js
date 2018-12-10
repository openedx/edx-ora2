/**
 Interface for response (submission) view.

 Args:
 element (DOM element): The DOM element representing the XBlock.
 server (OpenAssessment.Server): The interface to the XBlock server.
 fileUploader (OpenAssessment.FileUploader): File uploader instance.
 baseView (OpenAssessment.BaseView): Container view.
 data (Object): The data object passed from XBlock backend.

 Returns:
 OpenAssessment.ResponseView
 **/
OpenAssessment.ResponseView = function(element, server, fileUploader, baseView, data) {
    this.element = element;
    this.server = server;
    this.fileUploader = fileUploader;
    this.baseView = baseView;
    this.savedResponse = [];
    this.textResponse = 'required';
    this.fileUploadResponse = '';
    this.files = null;
    this.filesDescriptions = [];
    this.filesType = null;
    this.lastChangeTime = Date.now();
    this.errorOnLastSave = false;
    this.autoSaveTimerId = null;
    this.data = data;
    this.filesUploaded = false;
    this.announceStatus = false;
    this.isRendering = false;
    this.dateFactory = new OpenAssessment.DateTimeFactory(this.element);
};

OpenAssessment.ResponseView.prototype = {

    // Milliseconds between checks for whether we should autosave.
    AUTO_SAVE_POLL_INTERVAL: 2000,

    // Required delay after the user changes a response or a save occurs
    // before we can autosave.
    AUTO_SAVE_WAIT: 30000,

    // Maximum size (10 MB) for all attached files.
    MAX_FILES_SIZE: 10485760,

    UNSAVED_WARNING_KEY: "learner-response",

    /**
     Load the response (submission) view.
     **/
    load: function(usageID) {
        var view = this;
        var stepID = '.step--response';
        var focusID = "[id='oa_response_" + usageID + "']";

        view.isRendering = true;
        this.server.render('submission').done(
            function(html) {
                // Load the HTML and install event handlers
                $(stepID, view.element).replaceWith(html);
                view.server.renderLatex($(stepID, view.element));
                view.installHandlers();
                view.setAutoSaveEnabled(true);
                view.isRendering = false;
                view.baseView.announceStatusChangeToSRandFocus(stepID, usageID, false, view, focusID);
                view.announceStatus = false;
                view.dateFactory.apply();
            }
        ).fail(function() {
            view.baseView.showLoadError('response');
        });
    },

    /**
     Install event handlers for the view.
     **/
    installHandlers: function() {
        var sel = $('.step--response', this.element);
        var view = this;
        var uploadType = '';
        if (sel.find('.submission__answer__display__file').length) {
            uploadType = sel.find('.submission__answer__display__file').data('upload-type');
        }
        // Install a click handler for collapse/expand
        this.baseView.setUpCollapseExpand(sel);

        // Install change handler for textarea (to enable submission button)
        this.savedResponse = this.response();
        var handleChange = function() { view.handleResponseChanged(); };
        sel.find('.submission__answer__part__text__value').on('change keyup drop paste', handleChange);

        var handlePrepareUpload = function(eventData) { view.prepareUpload(eventData.target.files, uploadType); };
        sel.find('input[type=file]').on('change', handlePrepareUpload);

        var submit = $('.step--response__submit', this.element);
        this.textResponse = $(submit).attr('text_response');
        this.fileUploadResponse = $(submit).attr('file_upload_response');

        // Install a click handler for submission
        sel.find('.step--response__submit').click(
            function(eventObject) {
                // Override default form submission
                eventObject.preventDefault();
                view.submit();
            }
        );

        // Install a click handler for the save button
        sel.find('.submission__save').click(
            function(eventObject) {
                // Override default form submission
                eventObject.preventDefault();
                view.save();
            }
        );

        // Install click handler for the preview button
        this.baseView.bindLatexPreview(sel);

        // Install a click handler for the save button
        sel.find('.file__upload').click(
            function(eventObject) {
                // Override default form submission
                eventObject.preventDefault();
                var previouslyUploadedFiles = sel.find('.submission__answer__file').length ? true : false;
                $('.submission__answer__display__file', view.element).removeClass('is--hidden');
                if (previouslyUploadedFiles) {
                    var msg = gettext('After you upload new files all your previously uploaded files will be overwritten. Continue?');  // jscs:ignore maximumLineLength
                    if (confirm(msg)) {
                        view.uploadFiles();
                    }
                } else {
                    view.uploadFiles();
                }
            }
        );
    },

    /**
     Enable or disable autosave polling.

     Args:
     enabled (boolean): If true, start polling for whether we need to autosave.
     Otherwise, stop polling.
     **/
    setAutoSaveEnabled: function(enabled) {
        if (enabled) {
            if (this.autoSaveTimerId === null) {
                this.autoSaveTimerId = setInterval(
                    $.proxy(this.autoSave, this),
                    this.AUTO_SAVE_POLL_INTERVAL
                );
            }
        }
        else {
            if (this.autoSaveTimerId !== null) {
                clearInterval(this.autoSaveTimerId);
            }
        }
    },

    /**
     * Check that "submit" button could be enabled (or disabled)
     *
     * Args:
     * filesFiledIsNotBlank (boolean): used to avoid race conditions situations
     * (if files were successfully uploaded and are not displayed yet but
     * after upload last file the submit button should be available to push)
     *
     */
    checkSubmissionAbility: function(filesFiledIsNotBlank) {
        var textFieldsIsNotBlank = !this.response().every(function(element) {
            return $.trim(element) === '';
        });

        filesFiledIsNotBlank = filesFiledIsNotBlank || false;
        $('.submission__answer__file', this.element).each(function() {
            if (($(this).prop("tagName") === 'IMG') && ($(this).attr('src') !== '')) {
                filesFiledIsNotBlank = true;
            }
            if (($(this).prop("tagName") === 'A') && ($(this).attr('href') !== '')) {
                filesFiledIsNotBlank = true;
            }
        });
        var readyToSubmit = true;

        if ((this.textResponse === 'required') && !textFieldsIsNotBlank) {
            readyToSubmit = false;
        }
        if ((this.fileUploadResponse === 'required') && !filesFiledIsNotBlank) {
            readyToSubmit = false;
        }
        if ((this.textResponse === 'optional') && (this.fileUploadResponse === 'optional') &&
            !textFieldsIsNotBlank && !filesFiledIsNotBlank) {
            readyToSubmit = false;
        }
        this.submitEnabled(readyToSubmit);
    },

    /**
     * Check that "save" button could be enabled (or disabled)
     *
     */
    checkSaveAbility: function() {
        var textFieldsIsNotBlank = !this.response().every(function(element) {
            return $.trim(element) === '';
        });

        return !((this.textResponse === 'required') && !textFieldsIsNotBlank);
    },

    /**
     Enable/disable the submit button.
     Check that whether the submit button is enabled.

     Args:
     enabled (bool): If specified, set the state of the button.

     Returns:
     bool: Whether the button is enabled.

     Examples:
     >> view.submitEnabled(true);  // enable the button
     >> view.submitEnabled();  // check whether the button is enabled
     >> true
     **/
    submitEnabled: function(enabled) {
        return this.baseView.buttonEnabled('.step--response__submit', enabled);
    },

    /**
     Enable/disable the save button.
     Check whether the save button is enabled.

     Also enables/disables a beforeunload handler to warn
     users about navigating away from the page with unsaved changes.

     Args:
     enabled (bool): If specified, set the state of the button.

     Returns:
     bool: Whether the button is enabled.

     Examples:
     >> view.submitEnabled(true);  // enable the button
     >> view.submitEnabled();  // check whether the button is enabled
     >> true
     **/
    saveEnabled: function(enabled) {
        return this.baseView.buttonEnabled('.submission__save', enabled);
    },

    /**
     Enable/disable the preview button.

     Works exactly the same way as saveEnabled method.
     **/
    previewEnabled: function(enabled) {
        return this.baseView.buttonEnabled('.submission__preview', enabled);
    },

    /**
     Set the save status message.
     Retrieve the save status message.

     Args:
     msg (string): If specified, the message to display.

     Returns:
     string: The current status message.
     **/
    saveStatus: function(msg) {
        var sel = $('.save__submission__label', this.element);
        if (typeof msg === 'undefined') {
            return sel.text();
        } else {
            // Setting the HTML will overwrite the screen reader tag,
            // so prepend it to the message.
            var label = gettext("Status of Your Response");
            sel.html('<span class="sr">' + _.escape(label) + ':' + '</span>\n' + msg);
        }
    },

    /**
     Set the response texts.
     Retrieve the response texts.

     Args:
     texts (array of strings): If specified, the texts to set for the response.

     Returns:
     array of strings: The current response texts.
     **/
    response: function(texts) {
        var sel = $('.response__submission .submission__answer__part__text__value', this.element);
        if (typeof texts === 'undefined') {
            return sel.map(function() {
                return $.trim($(this).val());
            }).get();
        } else {
            sel.map(function(index) {
                $(this).val(texts[index]);
            });
        }
    },

    /**
     Check whether the response texts have changed since the last save.

     Returns: boolean
     **/
    responseChanged: function() {
        var savedResponse = this.savedResponse;
        return this.response().some(function(element, index) {
            return element !== savedResponse[index];
        });

    },

    /**
     Automatically save the user's response if certain conditions are met.

     Usually, this would be called by a timer (see `setAutoSaveEnabled()`).
     For testing purposes, it's useful to disable the timer
     and call this function synchronously.
     **/
    autoSave: function() {
        var timeSinceLastChange = Date.now() - this.lastChangeTime;

        // We only autosave if the following conditions are met:
        // (1) The response has changed.  We don't need to keep saving the same response.
        // (2) Sufficient time has passed since the user last made a change to the response.
        //      We don't want to save a response while the user is in the middle of typing.
        // (3) No errors occurred on the last save.  We don't want to keep refreshing
        //      the error message in the UI.  (The user can still retry the save manually).
        if (this.responseChanged() && timeSinceLastChange > this.AUTO_SAVE_WAIT && !this.errorOnLastSave) {
            this.save();
        }
    },

    /**
     Enable/disable the submission and save buttons based on whether
     the user has entered a response.
     **/
    handleResponseChanged: function() {
        this.checkSubmissionAbility();

        // Update the save button, save status, and "unsaved changes" warning
        // only if the response has changed
        if (this.responseChanged()) {
            var saveAbility = this.checkSaveAbility();
            this.saveEnabled(saveAbility);
            this.previewEnabled(saveAbility);
            this.saveStatus(gettext('This response has not been saved.'));
            this.baseView.unsavedWarningEnabled(
                true,
                this.UNSAVED_WARNING_KEY,
                gettext("If you leave this page without saving or submitting your response, you will lose any work you have done on the response.") // jscs:ignore maximumLineLength
            );
        }

        // Record the current time (used for autosave)
        this.lastChangeTime = Date.now();
    },

    /**
     Save a response without submitting it.
     **/
    save: function() {
        // If there were errors on previous calls to save, forget
        // about them for now.  If an error occurs on *this* save,
        // we'll set this back to true in the error handler.
        this.errorOnLastSave = false;

        // Update the save status and error notifications
        this.saveStatus(gettext('Saving...'));
        this.baseView.toggleActionError('save', null);

        // Disable the "unsaved changes" warning
        this.baseView.unsavedWarningEnabled(false, this.UNSAVED_WARNING_KEY);

        var view = this;
        var savedResponse = this.response();
        this.server.save(savedResponse).done(function() {
            // Remember which response we saved, once the server confirms that it's been saved...
            view.savedResponse = savedResponse;

            // ... but update the UI based on what the user may have entered
            // since hitting the save button.
            view.checkSubmissionAbility();

            var currentResponse = view.response();
            var currentResponseEqualsSaved = currentResponse.every(function(element, index) {
                return element === savedResponse[index];
            });
            if (currentResponseEqualsSaved) {
                view.saveEnabled(false);
                var msg = gettext("This response has been saved but not submitted.");
                view.saveStatus(msg);
                view.baseView.srReadTexts([msg]);
            }
        }).fail(function(errMsg) {
            view.saveStatus(gettext('Error'));
            view.baseView.toggleActionError('save', errMsg);

            // Remember that an error occurred
            // so we can disable autosave
            //(avoids repeatedly refreshing the error message)
            view.errorOnLastSave = true;
        });
    },

    /**
     Send a response submission to the server and update the view.
     **/
    submit: function() {
        // Immediately disable the submit button to prevent multiple submission
        this.submitEnabled(false);

        var view = this;
        var baseView = this.baseView;
        var fileDefer = $.Deferred();

        // check if there is a file selected but not uploaded yet
        if (view.files !== null && !view.filesUploaded) {
            var msg = gettext('Do you want to upload your file before submitting?');
            if (confirm(msg)) {
                fileDefer = view.uploadFiles();
                if (fileDefer === false) {
                    return;
                }
            } else {
                view.submitEnabled(true);
                return;
            }
        } else {
            fileDefer.resolve();
        }

        fileDefer
            .pipe(function() {
                return view.confirmSubmission()
                    // On confirmation, send the submission to the server
                    // The callback returns a promise so we can attach
                    // additional callbacks after the confirmation.
                    // NOTE: in JQuery >=1.8, `pipe()` is deprecated in favor of `then()`,
                    // but we're using JQuery 1.7 in the LMS, so for now we're stuck with `pipe()`.
                    .pipe(function() {
                        var submission = view.response();
                        baseView.toggleActionError('response', null);

                        // Send the submission to the server, returning the promise.
                        return view.server.submit(submission);
                    });
            })

            // If the submission was submitted successfully, move to the next step
            .done($.proxy(view.moveToNextStep, view))

            // Handle submission failure (either a server error or cancellation),
            .fail(function(errCode, errMsg) {
                // If the error is "multiple submissions", then we should move to the next
                // step.  Otherwise, the user will be stuck on the current step with no
                // way to continue.
                if (errCode === 'ENOMULTI') { view.moveToNextStep(); }
                else {
                    // If there is an error message, display it
                    if (errMsg) { baseView.toggleActionError('submit', errMsg); }

                    // Re-enable the submit button so the user can retry
                    view.submitEnabled(true);
                }
            });
    },

    /**
     Transition the user to the next step in the workflow.
     **/
    moveToNextStep: function() {
        var baseView = this.baseView;
        var usageID = baseView.getUsageID();
        var view = this;

        this.load(usageID);
        baseView.loadAssessmentModules(usageID);

        view.announceStatus = true;

        // Disable the "unsaved changes" warning if the user
        // tries to navigate to another page.
        baseView.unsavedWarningEnabled(false, this.UNSAVED_WARNING_KEY);
    },

    /**
     Make the user confirm before submitting a response.

     Returns:
     JQuery deferred object, which is:
     * resolved if the user confirms the submission
     * rejected if the user cancels the submission
     **/
    confirmSubmission: function() {
        // Keep this on one big line to avoid gettext bug: http://stackoverflow.com/a/24579117
        var msg = gettext("You're about to submit your response for this assignment. After you submit this response, you can't change it or submit a new response.");  // jscs:ignore maximumLineLength
        // TODO -- UI for confirmation dialog instead of JS confirm
        return $.Deferred(function(defer) {
            if (confirm(msg)) { defer.resolve(); }
            else { defer.reject(); }
        });
    },

    /**
     When selecting a file for upload, do some quick client-side validation
     to ensure that it is an image, a PDF or other allowed types, and is not
     larger than the maximum file size.

     Args:
     files (list): A collection of files used for upload. This function assumes
     there is only one file being uploaded at any time. This file must
     be less than 5 MB and an image, PDF or other allowed types.
     uploadType (string): uploaded file type allowed, could be none, image,
     file or custom.

     **/
    prepareUpload: function(files, uploadType, descriptions) {
        this.files = null;
        this.filesType = uploadType;
        this.filesUploaded = false;

        var totalSize = 0;
        var ext = null;
        var fileType = null;
        var fileName = '';
        var errorCheckerTriggered = false;
        var sel = $('.step--response', this.element);

        for (var i = 0; i < files.length; i++) {
            totalSize += files[i].size;
            ext = files[i].name.split('.').pop().toLowerCase();
            fileType = files[i].type;
            fileName = files[i].name;

            if (totalSize > this.MAX_FILES_SIZE) {
                this.baseView.toggleActionError(
                    'upload',
                    gettext("File size must be 10MB or less.")
                );
                errorCheckerTriggered = true;
                break;
            } else if (uploadType === "image" && this.data.ALLOWED_IMAGE_MIME_TYPES.indexOf(fileType) === -1) {
                this.baseView.toggleActionError(
                    'upload',
                    gettext("You can upload files with these file types: ") + "JPG, PNG or GIF"
                );
                errorCheckerTriggered = true;
                break;
            } else if (uploadType === "pdf-and-image" && this.data.ALLOWED_FILE_MIME_TYPES.indexOf(fileType) === -1) {
                this.baseView.toggleActionError(
                    'upload',
                    gettext("You can upload files with these file types: ") + "JPG, PNG, GIF or PDF"
                );
                errorCheckerTriggered = true;
                break;
            } else if (uploadType === "custom" && this.data.FILE_TYPE_WHITE_LIST.indexOf(ext) === -1) {
                this.baseView.toggleActionError(
                    'upload',
                    gettext("You can upload files with these file types: ") +
                    this.data.FILE_TYPE_WHITE_LIST.join(", ")
                );
                errorCheckerTriggered = true;
                break;
            } else if (this.data.FILE_EXT_BLACK_LIST.indexOf(ext) !== -1) {
                this.baseView.toggleActionError(
                    'upload',
                    gettext("File type is not allowed.")
                );
                errorCheckerTriggered = true;
                break;
            }
        }

        if (!errorCheckerTriggered) {
            this.baseView.toggleActionError('upload', null);
            this.files = files;
            this.updateFilesDescriptionsFields(files, descriptions, uploadType);
        }

        if (this.files === null) {
            sel.find('.file__upload').prop('disabled', true);
        }
    },

    /**
     Render textarea fields to input description for each uploaded file.

     */
    /* jshint -W083 */
    updateFilesDescriptionsFields: function(files, descriptions, uploadType) {
        var filesDescriptions = $(this.element).find('.files__descriptions').first();
        var mainDiv = null;
        var divLabel = null;
        var divTextarea = null;
        var divImage = null;
        var img = null;
        var textarea = null;
        var descriptionsExists = true;

        this.filesDescriptions = descriptions || [];

        $(filesDescriptions).show().html('');

        for (var i = 0; i < files.length; i++) {
            mainDiv = $('<div/>');

            divLabel = $('<div/>');
            divLabel.addClass('submission__file__description__label');
            divLabel.text(gettext("Describe ") + files[i].name + ' ' + gettext("(required):"));
            divLabel.appendTo(mainDiv);

            divTextarea = $('<div/>');
            divTextarea.addClass('submission__file__description');
            textarea = $('<textarea />', {
                'aria-label': gettext("Describe ") + files[i].name
            });
            if ((this.filesDescriptions.indexOf(i) !== -1) && (this.filesDescriptions[i] !== '')) {
                textarea.val(this.filesDescriptions[i]);
            } else {
                descriptionsExists = false;
            }
            textarea.addClass('file__description file__description__' + i);
            textarea.appendTo(divTextarea);

            if (uploadType === "image") {
                img = $('<img/>', {
                    src: window.URL.createObjectURL(files[i]),
                    height: 80,
                    alt: gettext("Thumbnail view of ") + files[i].name
                });
                img.onload = function() {
                    window.URL.revokeObjectURL(this.src);
                };

                divImage = $('<div/>');
                divImage.addClass('submission__img__preview');
                img.appendTo(divImage);
                divImage.appendTo(mainDiv);
            }

            divTextarea.appendTo(mainDiv);

            mainDiv.appendTo(filesDescriptions);
            textarea.on("change keyup drop paste", $.proxy(this, "checkFilesDescriptions"));
        }

        $(this.element).find('.file__upload').prop('disabled', !descriptionsExists);
    },

    /**
     When user type something in some file description field this function check input
     and block/unblock "Upload" button

     */
    checkFilesDescriptions: function() {
        var isError = false;
        var filesDescriptions = [];

        $(this.element).find('.file__description').each(function() {
            var filesDescriptionVal = $(this).val();
            if (filesDescriptionVal) {
                filesDescriptions.push(filesDescriptionVal);
            } else {
                isError = true;
            }
        });

        $(this.element).find('.file__upload').prop('disabled', isError);
        if (!isError) {
            this.filesDescriptions = filesDescriptions;
        }
    },

    /**
     Clear field with files descriptions.

     */
    removeFilesDescriptions: function() {
        var filesDescriptions = $(this.element).find('.files__descriptions').first();
        $(filesDescriptions).hide().html('');
    },

    /**
     Remove previously uploaded files.

     */
    removeUploadedFiles: function() {
        var view = this;
        var sel = $('.step--response', this.element);

        return this.server.removeUploadedFiles().done(
            function() {
                var sel = $('.step--response', view.element);
                sel.find('.submission__answer__files').html('');
            }
        ).fail(function(errMsg) {
            view.baseView.toggleActionError('upload', errMsg);
            sel.find('.file__upload').prop('disabled', false);
        });
    },

    /**
     Sends request to server to save all file descriptions.

     */
    saveFilesDescriptions: function() {
        var view = this;
        var sel = $('.step--response', this.element);

        return this.server.saveFilesDescriptions(this.filesDescriptions).done(
            function() {
                view.removeFilesDescriptions();
            }
        ).fail(function(errMsg) {
            view.baseView.toggleActionError('upload', errMsg);
            sel.find('.file__upload').prop('disabled', false);
        });
    },

    /**
     Manages file uploads for submission attachments.

     **/
    uploadFiles: function() {
        var view = this;
        var promise = null;
        var fileCount = view.files.length;
        var sel = $('.step--response', this.element);

        sel.find('.file__upload').prop('disabled', true);

        promise = view.removeUploadedFiles();
        promise = promise.then(function() {
            return view.saveFilesDescriptions();
        });

        $.each(view.files, function(index, file) {
            promise = promise.then(function() {
                return view.fileUpload(view, file.type, file.name, index, file, fileCount === (index + 1));
            });
        });

        return promise;
    },

    /**
     Retrieves a one-time upload URL from the server, and uses it to upload images
     to a designated location.

     **/
    fileUpload: function(view, filetype, filename, filenum, file, finalUpload) {
        var sel = $('.step--response', this.element);
        var handleError = function(errMsg) {
            view.baseView.toggleActionError('upload', errMsg);
            sel.find('.file__upload').prop('disabled', false);
        };

        // Call getUploadUrl to get the one-time upload URL for this file. Once
        // completed, execute a sequential AJAX call to upload to the returned
        // URL. This request requires appropriate CORS configuration for AJAX
        // PUT requests on the server.
        return view.server.getUploadUrl(filetype, filename, filenum).done(
            function(url) {
                view.fileUploader.upload(url, file)
                    .done(function() {
                        view.fileUrl(filenum);
                        view.baseView.toggleActionError('upload', null);
                        if (finalUpload) {
                            sel.find('input[type=file]').val('');
                            view.filesUploaded = true;
                            view.checkSubmissionAbility(true);
                        }
                    })
                    .fail(handleError);
            }
        ).fail(handleError);
    },

    /**
     Set the file URL, or retrieve it.

     **/
    fileUrl: function(filenum) {
        var view = this;
        var sel = $('.step--response', this.element);
        view.server.getDownloadUrl(filenum).done(function(url) {
            var className = 'submission__answer__file__block__' + filenum;
            var file = null;
            var img = null;
            var fileBlock = null;
            var fileBlockExists = sel.find("." + className).length ? true : false;
            var div1 = null;
            var div2 = null;
            var ariaLabelledBy = null;

            if (!fileBlockExists) {
                fileBlock = $('<div/>');
                fileBlock.addClass('submission__answer__file__block ' + className);
                fileBlock.appendTo(sel.find('.submission__answer__files').first());
            }

            if (view.filesType === 'image') {
                ariaLabelledBy = 'file_description_' + Math.random().toString(36).substr(2, 9);

                div1 = $('<div/>', {
                    id: ariaLabelledBy
                });
                div1.addClass('submission__file__description__label');
                div1.text(view.filesDescriptions[filenum] + ':');
                div1.appendTo(fileBlock);

                img = $('<img />');
                img.addClass('submission__answer__file submission--image');
                img.attr('aria-labelledby', ariaLabelledBy);
                img.attr('src', url);

                div2 = $('<div/>');
                div2.html(img);
                div2.appendTo(fileBlock);
            } else {
                file = $('<a />', {
                    href: url,
                    text: view.filesDescriptions[filenum]
                });
                file.addClass('submission__answer__file submission--file');
                file.attr('target', '_blank');
                file.appendTo(fileBlock);
            }

            return url;
        });
    }
};
