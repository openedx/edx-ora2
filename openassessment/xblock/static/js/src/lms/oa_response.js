/**
Interface for response (submission) view.

Args:
    element (DOM element): The DOM element representing the XBlock.
    server (OpenAssessment.Server): The interface to the XBlock server.
    baseView (OpenAssessment.BaseView): Container view.

Returns:
    OpenAssessment.ResponseView
**/
OpenAssessment.ResponseView = function(element, server, fileUploader, baseView) {
    this.element = element;
    this.server = server;
    this.fileUploader = fileUploader;
    this.baseView = baseView;
    this.savedResponse = [];
    this.files = null;
    this.imageType = null;
    this.lastChangeTime = Date.now();
    this.errorOnLastSave = false;
    this.autoSaveTimerId = null;
};


OpenAssessment.ResponseView.prototype = {

    // Milliseconds between checks for whether we should autosave.
    AUTO_SAVE_POLL_INTERVAL: 2000,

    // Required delay after the user changes a response or a save occurs
    // before we can autosave.
    AUTO_SAVE_WAIT: 30000,

    // Maximum file size (5 MB) for an attached file.
    MAX_FILE_SIZE: 5242880,

    /**
    Load the response (submission) view.
    **/
    load: function() {
        var view = this;
        this.server.render('submission').done(
            function(html) {
                // Load the HTML and install event handlers
                $('#openassessment__response', view.element).replaceWith(html);
                view.server.renderLatex($('#openassessment__response', view.element));
                view.installHandlers();
                view.setAutoSaveEnabled(true);
            }
        ).fail(function(errMsg) {
            view.baseView.showLoadError('response');
        });
    },

    /**
    Install event handlers for the view.
    **/
    installHandlers: function() {
        var sel = $('#openassessment__response', this.element);
        var view = this;

        // Install a click handler for collapse/expand
        this.baseView.setUpCollapseExpand(sel);

        // Install change handler for textarea (to enable submission button)
        this.savedResponse = this.response();
        var handleChange = function(eventData) { view.handleResponseChanged(); };
        sel.find('.submission__answer__part__text__value').on('change keyup drop paste', handleChange);

        var handlePrepareUpload = function(eventData) { view.prepareUpload(eventData.target.files); };
        sel.find('input[type=file]').on('change', handlePrepareUpload);
        // keep the preview as display none at first 
        sel.find('#submission__preview__item').hide();

        // Install a click handler for submission
        sel.find('#step--response__submit').click(
            function(eventObject) {
                // Override default form submission
                eventObject.preventDefault();
                view.submit();
            }
        );

        // Install a click handler for the save button
        sel.find('#submission__save').click(
            function(eventObject) {
                // Override default form submission
                eventObject.preventDefault();
                view.save();
            }
        );

        // Install click handler for the preview button
        sel.find('#submission__preview').click(
            function(eventObject) {
                eventObject.preventDefault();
                // extract typed-in response and replace newline with br
                var preview_text = sel.find('.submission__answer__part__text__value').val();
                var preview_container = sel.find('#preview_content');
                preview_container.html(preview_text.replace(/\r\n|\r|\n/g,"<br />"));

                // Render in mathjax
                sel.find('#submission__preview__item').show();
                MathJax.Hub.Queue(['Typeset', MathJax.Hub, preview_container[0]]);
            }
        );

        // Install a click handler for the save button
        sel.find('#file__upload').click(
            function(eventObject) {
                // Override default form submission
                eventObject.preventDefault();
                $('.submission__answer__display__image', view.element).removeClass('is--hidden');
                view.fileUpload();
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
        var sel = $('#step--response__submit', this.element);
        if (typeof enabled === 'undefined') {
            return !sel.hasClass('is--disabled');
        } else {
            sel.toggleClass('is--disabled', !enabled);
        }
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
        var sel = $('#submission__save', this.element);
        if (typeof enabled === 'undefined') {
            return !sel.hasClass('is--disabled');
        } else {
            sel.toggleClass('is--disabled', !enabled);
        }
    },

    /**
    Enable/disable the preview button.

    Works exactly the same way as saveEnabled method.
    **/
    previewEnabled: function(enabled) {
        var sel = $('#submission__preview', this.element);
        if (typeof enabled === 'undefined') {
            return !sel.hasClass('is--disabled');
        } else {
            sel.toggleClass('is--disabled', !enabled);
        }
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
        var sel = $('#response__save_status h3', this.element);
        if (typeof msg === 'undefined') {
            return sel.text();
        } else {
            // Setting the HTML will overwrite the screen reader tag,
            // so prepend it to the message.
            var label = gettext("Status of Your Response");
            sel.html('<span class="sr">' + label + ':' + '</span>\n' + msg);
        }
    },

    /**
    Enable/disable the "navigate away" warning to alert the user of unsaved changes.

    Args:
        enabled (bool): If specified, set whether the warning is enabled.

    Returns:
        bool: Whether the warning is enabled.

    Examples:
        >> view.unsavedWarningEnabled(true); // enable the "unsaved" warning
        >> view.unsavedWarningEnabled();
        >> true
    **/
    unsavedWarningEnabled: function(enabled) {
        if (typeof enabled === 'undefined') {
            return (window.onbeforeunload !== null);
        }
        else {
            if (enabled) {
                window.onbeforeunload = function() {
                    // Keep this on one big line to avoid gettext bug: http://stackoverflow.com/a/24579117
                    return gettext("If you leave this page without saving or submitting your response, you'll lose any work you've done on the response.");
                };
            }
            else {
                window.onbeforeunload = null;
            }
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
        var sel = $('.submission__answer__part__text__value', this.element);
        if (typeof texts === 'undefined') {
            return sel.map(function() {
                return $.trim($(this).val());
            }).get();
        } else {
            sel.map(function(index, element) {
                $(this).val(texts[index]);
            })
        }
    },

    /**
    Check whether the response texts have changed since the last save.

    Returns: boolean
    **/
    responseChanged: function() {
        var savedResponse = this.savedResponse;
        return this.response().some(function(element, index, array) {
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
        // Enable the save/submit button only for non-blank responses
        var isNotBlank = !this.response().every(function(element, index, array) {
                return $.trim(element) == '';
            });
        this.submitEnabled(isNotBlank);

        // Update the save button, save status, and "unsaved changes" warning
        // only if the response has changed
        if (this.responseChanged()) {
            this.saveEnabled(isNotBlank);
            this.previewEnabled(isNotBlank);
            this.saveStatus(gettext('This response has not been saved.'));
            this.unsavedWarningEnabled(true);
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
        this.unsavedWarningEnabled(false);

        var view = this;
        var savedResponse = this.response();
        this.server.save(savedResponse).done(function() {
            // Remember which response we saved, once the server confirms that it's been saved...
            view.savedResponse = savedResponse;

            // ... but update the UI based on what the user may have entered
            // since hitting the save button.
            var currentResponse = view.response();
            var currentResponseIsEmpty = currentResponse.every(function(element, index, array) {
                return element == '';
            });
            view.submitEnabled(!currentResponseIsEmpty);

            var currentResponseEqualsSaved = currentResponse.every(function(element, index, array) {
                return element === savedResponse[index];
            });
            if (currentResponseEqualsSaved) {
                view.saveEnabled(false);
                view.saveStatus(gettext("This response has been saved but not submitted."));
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

        this.confirmSubmission()
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
            })

            // If the submission was submitted successfully, move to the next step
            .done($.proxy(view.moveToNextStep, view))

            // Handle submission failure (either a server error or cancellation),
            .fail(function(errCode, errMsg) {
                // If the error is "multiple submissions", then we should move to the next
                // step.  Otherwise, the user will be stuck on the current step with no
                // way to continue.
                if (errCode == 'ENOMULTI') { view.moveToNextStep(); }
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
        this.load();
        this.baseView.loadAssessmentModules();

        // Disable the "unsaved changes" warning if the user
        // tries to navigate to another page.
        this.unsavedWarningEnabled(false);
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
        var msg = gettext("You're about to submit your response for this assignment. After you submit this response, you can't change it or submit a new response.");
        // TODO -- UI for confirmation dialog instead of JS confirm
        return $.Deferred(function(defer) {
            if (confirm(msg)) { defer.resolve(); }
            else { defer.reject(); }
        });
    },

    /**
     When selecting a file for upload, do some quick client-side validation
     to ensure that it is an image, and is not larger than the maximum file
     size.

     Args:
        files (list): A collection of files used for upload. This function assumes
            there is only one file being uploaded at any time. This file must
            be less than 5 MB and an image.

     **/
    prepareUpload: function(files) {
        this.files = null;
        this.imageType = files[0].type;
        if (files[0].size > this.MAX_FILE_SIZE) {
            this.baseView.toggleActionError(
                'upload', gettext("File size must be 5MB or less.")
            );
        } else if (this.imageType.substring(0,6) != 'image/') {
            this.baseView.toggleActionError(
                'upload', gettext("File must be an image.")
            );
        } else {
            this.baseView.toggleActionError('upload', null);
            this.files = files;
        }
        $("#file__upload").toggleClass("is--disabled", this.files === null);
    },


    /**
     Manages file uploads for submission attachments. Retrieves a one-time
     upload URL from the server, and uses it to upload images to a designated
     location.

     **/
    fileUpload: function() {
        var view = this;
        var fileUpload = $("#file__upload");
        fileUpload.addClass("is--disabled");

        var handleError = function(errMsg) {
            view.baseView.toggleActionError('upload', errMsg);
            fileUpload.removeClass("is--disabled");
        };

        // Call getUploadUrl to get the one-time upload URL for this file. Once
        // completed, execute a sequential AJAX call to upload to the returned
        // URL. This request requires appropriate CORS configuration for AJAX
        // PUT requests on the server.
        this.server.getUploadUrl(view.imageType).done(
            function(url) {
                var image = view.files[0];
                view.fileUploader.upload(url, image)
                    .done(function() {
                        view.imageUrl();
                        view.baseView.toggleActionError('upload', null);
                    })
                    .fail(handleError);
            }
        ).fail(handleError);
    },

    /**
     Set the image URL, or retrieve it.
     **/
    imageUrl: function() {
        var view = this;
        var image = $('#submission__answer__image', view.element);
        view.server.getDownloadUrl().done(function(url) {
            image.attr('src', url);
            return url;
        });
    }

};
