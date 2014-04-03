/* JavaScript for response (submission) view */

/* Namespace for open assessment */
if (typeof OpenAssessment == "undefined" || !OpenAssessment) {
    OpenAssessment = {};
}


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
};


OpenAssessment.ResponseView.prototype = {
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
        var handleChange = function(eventData) { view.responseChanged(); };
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
            sel.toggleClass('is--disabled', !enabled)
        }
    },

    /**
    Enable/disable the save button.
    Check that whether the save button is enabled.

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
            sel.html('<span class="sr">Your Working Submission Status:</span>\n' + msg);
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
    Enable/disable the submission and save buttons based on whether
    the user has entered a response.
    **/
    responseChanged: function() {
        // Enable the save/submit button only for non-blank responses
        var currentResponse = $.trim(this.response());
        var isBlank = (currentResponse !== '');
        this.submitEnabled(isBlank);

        // Update the save button and status only if the response has changed
        if ($.trim(this.savedResponse) !== currentResponse) {
            this.saveEnabled(isBlank);
            this.saveStatus('Unsaved draft');
        }
    },

    /**
    Save a response without submitting it.
    **/
    save: function() {
        // Update the save status and error notifications
        this.saveStatus('Saving...');
        this.baseView.toggleActionError('save', null);

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
                view.saveStatus("Saved but not submitted");
            }
        }).fail(function(errMsg) {
            view.saveStatus('Error');
            view.baseView.toggleActionError('save', errMsg);
        });
    },

    /**
    Send a response submission to the server and update the view.
    **/
    submit: function() {
        // Immediately disable the submit button to prevent multiple submission
        this.submitEnabled(false);

        // Send the submission to the server
        var submission = $('#submission__answer__value', this.element).val();
        this.baseView.toggleActionError('response', null);

        var view = this;
        var baseView = this.baseView;
        var moveToNextStep = function() {
            view.load();
            baseView.renderPeerAssessmentStep();
        };
        this.server.submit(submission)
            .done(moveToNextStep)
            .fail(function(errCode, errMsg) {
                // If the error is "multiple submissions", then we should move to the next
                // step.  Otherwise, the user will be stuck on the current step with no
                // way to continue.
                if (errCode == 'ENOMULTI') {
                    moveToNextStep();
                }
                else {
                    // Display the error
                    baseView.toggleActionError('submit', errMsg);

                    // Re-enable the submit button to allow the user to retry
                    view.submitEnabled(true);
                }
            });
    }
};
