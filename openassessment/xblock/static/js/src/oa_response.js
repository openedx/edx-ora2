/**
Interface for response (submission) view.

Args:
    element (DOM element): The DOM element representing the XBlock.
    server (OpenAssessment.Server): The interface to the XBlock server.
    baseView (OpenAssessment.BaseView): Container view.

Returns:
    OpenAssessment.ResponseView
**/
OpenAssessment.ResponseView = function(element, server, baseView) {
    this.element = element;
    this.server = server;
    this.baseView = baseView;
    this.savedResponse = "";
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

    /**
    Load the response (submission) view.
    **/
    load: function() {
        var view = this;
        this.server.render('submission').done(
            function(html) {
                // Load the HTML and install event handlers
                $('#openassessment__response', view.element).replaceWith(html);
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
        sel.find('#submission__answer__value').on('change keyup drop paste', handleChange);

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
                    return gettext("If you leave this page without saving or submitting your response, you'll lose any work you've done on the response.");
                };
            }
            else {
                window.onbeforeunload = null;
            }
        }
    },

    /**
    Set the response text.
    Retrieve the response text.

    Args:
        text (string): If specified, the text to set for the response.

    Returns:
        string: The current response text.
    **/
    response: function(text) {
        var sel = $('#submission__answer__value', this.element);
        if (typeof text === 'undefined') {
            return sel.val();
        } else {
            sel.val(text);
        }
    },


    /**
    Check whether the response text has changed since the last save.

    Returns: boolean
    **/
    responseChanged: function() {
        var currentResponse = $.trim(this.response());
        var savedResponse = $.trim(this.savedResponse);
        return savedResponse !== currentResponse;
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
        var isBlank = ($.trim(this.response()) !== '');
        this.submitEnabled(isBlank);

        // Update the save button, save status, and "unsaved changes" warning
        // only if the response has changed
        if (this.responseChanged()) {
            this.saveEnabled(isBlank);
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
            view.submitEnabled(currentResponse !== '');
            if (currentResponse == savedResponse) {
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
                var submission = $('#submission__answer__value', view.element).val();
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
        var msg = (
            "You're about to submit your response for this assignment. " +
            "After you submit this response, you can't change it or submit a new response."
        );
        // TODO -- UI for confirmation dialog instead of JS confirm
        return $.Deferred(function(defer) {
            if (confirm(msg)) { defer.resolve(); }
            else { defer.reject(); }
        });
    }
};
