/**
Interface for student-facing views.

Args:
    runtime (Runtime): an XBlock runtime instance.
    element (DOM element): The DOM element representing this XBlock.
    server (OpenAssessment.Server): The interface to the XBlock server.
    data (Object): The data object passed from XBlock backend.

Returns:
    OpenAssessment.BaseView
**/
OpenAssessment.BaseView = function(runtime, element, server, data) {
    this.runtime = runtime;
    this.element = element;
    this.server = server;
    this.fileUploader = new OpenAssessment.FileUploader();

    this.responseView = new OpenAssessment.ResponseView(this.element, this.server, this.fileUploader, this, data);
    this.trainingView = new OpenAssessment.StudentTrainingView(this.element, this.server, this);
    this.selfView = new OpenAssessment.SelfView(this.element, this.server, this);
    this.peerView = new OpenAssessment.PeerView(this.element, this.server, this);
    this.staffView = new OpenAssessment.StaffView(this.element, this.server, this);
    this.gradeView = new OpenAssessment.GradeView(this.element, this.server, this);
    this.leaderboardView = new OpenAssessment.LeaderboardView(this.element, this.server, this);
    this.messageView = new OpenAssessment.MessageView(this.element, this.server, this);
    // Staff-only area with information and tools for managing student submissions
    this.staffAreaView = new OpenAssessment.StaffAreaView(this.element, this.server, this);
    this.usageID = '';
};

if (typeof OpenAssessment.unsavedChanges === 'undefined' || !OpenAssessment.unsavedChanges) {
    OpenAssessment.unsavedChanges = {};
}

// This is used by unit tests to reset state.
OpenAssessment.clearUnsavedChanges = function() {
    OpenAssessment.unsavedChanges = {};
    window.onbeforeunload = null;
};

OpenAssessment.BaseView.prototype = {

    IS_SHOWING_CLASS: "is--showing",
    SLIDABLE_CLASS: "ui-slidable",
    SLIDABLE_CONTENT_CLASS: "ui-slidable__content",
    SLIDABLE_CONTROLS_CLASS: "ui-slidable__control",
    SLIDABLE_CONTAINER_CLASS: "ui-slidable__container",

    /**
     * Checks to see if the scrollTo function is available, then scrolls to the
     * top of the list of steps (or the specified selector) for this display.
     *
     * Ideally, we would not need to check if the function exists, and could
     * import scrollTo, or other dependencies, into workbench.
     *
     * @param {string} selector optional CSS selector to scroll to. If not supplied,
     *     the default value of ".openassessment__steps" is used.
     */
    scrollToTop: function(selector) {
        if (!selector) {
            selector = ".openassessment__steps";
        }
        if ($.scrollTo instanceof Function) {
            $(window).scrollTo($(selector, this.element), 800, {offset: -50});
            $(selector + " > header ." + this.SLIDABLE_CLASS, this.element).focus();
        }
    },

    /**
     * Install click handlers to expand/collapse a section.
     *
     * @param {element} parentElement JQuery selector for the container element.
     */
    setUpCollapseExpand: function(parentElement) {
        var view = this;

        $('.' + view.SLIDABLE_CONTROLS_CLASS, parentElement).each(function() {
            $(this).on("click", function(event) {
                event.preventDefault();

                var $slidableControl = $(event.target).closest('.' + view.SLIDABLE_CONTROLS_CLASS);

                var $container = $slidableControl.closest('.' + view.SLIDABLE_CONTAINER_CLASS);
                var $toggleButton = $slidableControl.find('.' + view.SLIDABLE_CLASS);
                var $panel = $slidableControl.next('.' + view.SLIDABLE_CONTENT_CLASS);

                if ($container.hasClass('is--showing')) {
                    $panel.slideUp();
                    $toggleButton.attr('aria-expanded', 'false');
                    $container.removeClass('is--showing');
                } else if (!$container.hasClass('has--error') &&
                    !$container.hasClass('is--empty') &&
                    !$container.hasClass('is--unavailable')) {
                    $panel.slideDown();
                    $toggleButton.attr('aria-expanded', 'true');
                    $container.addClass('is--showing');
                }

                $container.removeClass('is--initially--collapsed ');
            });
        });
    },

    /**
     * Get usage key of an XBlock.
     */
    getUsageID: function() {
        if (!this.usageID) {
            this.usageID = $(this.element).data('usage-id');
        }
        return this.usageID;
    },

    /**
     * Asynchronously load each sub-view into the DOM.
     */
    load: function() {
        this.responseView.load();
        this.loadAssessmentModules();
        this.staffAreaView.load();
    },

    /**
     * Refresh the Assessment Modules. This should be called any time an action is
     * performed by the user.
     */
    loadAssessmentModules: function(usageID) {
        this.trainingView.load(usageID);
        this.peerView.load(usageID);
        this.staffView.load(usageID);
        this.selfView.load(usageID);
        this.gradeView.load(usageID);
        this.leaderboardView.load(usageID);
        /**
        this.messageView.load() is intentionally omitted.
        Because of the asynchronous loading, there is no way to tell (from the perspective of the
        messageView) whether or not the peer view was able to grab an assessment to assess. Any
        asynchronous strategy would run into a race condition based around this problem at some
        point.  Instead, we created a field in the XBlock called no_peers, which is set by the
        Peer XBlock Handler, and which is examined by the Message XBlock Handler.

        To Avoid rendering the message more than one time per update/load (and avoiding all comp-
        lications that that would likely induce), we chose to load the method view only after
        the peer view has been loaded.  This is achieved by having the peer view  call to render
        the message view after rendering itself but before exiting its load method.
        */
    },

    /**
     * Refresh the message only (called by PeerView to update and avoid race condition)
     */
    loadMessageView: function() {
        this.messageView.load();
    },

    /**
     * Report an error to the user.
     *
     * @param {string} type The type of error. Options are "save", submit", "peer", and "self".
     * @param {string} message The error message to display, or if null hide the message.
     *     Note: loading errors are never hidden once displayed.
     */
    toggleActionError: function(type, message) {
        var element = this.element;
        var container = null;
        if (type === 'save') {
            container = '.response__submission__actions';
        }
        else if (type === 'submit' || type === 'peer' || type === 'self' || type === 'student-training') {
            container = '.step__actions';
        }
        else if (type === 'feedback_assess') {
            container = '.submission__feedback__actions';
        }
        else if (type === 'upload') {
            container = '.upload__error';
        }

        // If we don't have anywhere to put the message, just log it to the console
        if (container === null) {
            if (message !== null) { console.log(message); }
        }

        else {
            // Insert the error message
            $(container + " .message__content", element).html('<p>' + (message ? _.escape(message) : "") + '</p>');
            // Toggle the error class
            $(container, element).toggleClass('has--error', message !== null);
            // Send focus to the error message
            $(container + " > .message", element).focus();
        }
    },

    /**
     * Report an error loading a step.
     *
     * @param {string} stepName The step that could not be loaded.
     * @param {string} errorMessage An optional error message to use instead of the default.
     */
    showLoadError: function(stepName, errorMessage) {
        if (!errorMessage) {
            errorMessage = gettext('Unable to load');
        }
        var $container = $('.step--' + stepName);
        $container.toggleClass('has--error', true);
        $container.removeClass('is--showing');
        $container.find('.ui-slidable').attr('aria-expanded', 'false');
        $container.find('.step__status__value i').removeClass().addClass('icon fa fa-exclamation-triangle');
        $container.find('.step__status__value .copy').html(_.escape(errorMessage));
    },

    /**
     * Enable/disable the "navigate away" warning to alert the user of unsaved changes.
     *
     * @param {boolean} enabled If specified, set whether the warning is enabled.
     * @param {string} key A unique key related to the type of unsaved changes. Must be supplied
     * if "enabled" is also supplied.
     * @param {string} message The message to show if navigating away with unsaved changes. Only needed
     * if "enabled" is true.
     * @returns {boolean} Whether the warning is enabled (only if "enabled" argument is not supplied).
     */
    unsavedWarningEnabled: function(enabled, key, message) {
        if (typeof enabled === 'undefined') {
            return (window.onbeforeunload !== null);
        }
        else {
            // To support multiple ORA XBlocks on the same page, store state by XBlock usage-id.
            var usageID = $(this.element).data("usage-id");
            if (enabled) {
                if (typeof OpenAssessment.unsavedChanges[usageID] === 'undefined' ||
                    !OpenAssessment.unsavedChanges[usageID]) {
                    OpenAssessment.unsavedChanges[usageID] = {};
                }
                OpenAssessment.unsavedChanges[usageID][key] = message;
                window.onbeforeunload = function() {
                    for (var xblockUsageID in OpenAssessment.unsavedChanges) {
                        if (OpenAssessment.unsavedChanges.hasOwnProperty(xblockUsageID)) {
                            for (var key in OpenAssessment.unsavedChanges[xblockUsageID]) {
                                if (OpenAssessment.unsavedChanges[xblockUsageID].hasOwnProperty(key)) {
                                    return OpenAssessment.unsavedChanges[xblockUsageID][key];
                                }
                            }
                        }
                    }
                };
            }
            else {
                if (typeof OpenAssessment.unsavedChanges[usageID] !== 'undefined') {
                    delete OpenAssessment.unsavedChanges[usageID][key];
                    if ($.isEmptyObject(OpenAssessment.unsavedChanges[usageID])) {
                        delete OpenAssessment.unsavedChanges[usageID];
                    }
                    if ($.isEmptyObject(OpenAssessment.unsavedChanges)) {
                        window.onbeforeunload = null;
                    }
                }
            }
        }
    },

    /**
     * Enable/disable the button with the given class name.
     *
     * @param {string} className The css class to find the button
     * @param {boolean} enabled If specified enables or disables the button. If not specified,
     *     the state of the button is not changed, but the current enabled status is returned.
     * @returns {boolean} whether or not the button is enabled
     */
    buttonEnabled: function(className, enabled) {
        var $element = $(className, this.element);
        if (typeof enabled === 'undefined') {
            return !$element.prop('disabled');
        } else {
            $element.prop('disabled', !enabled);
            return enabled;
        }
    }
};

/* XBlock JavaScript entry point for OpenAssessmentXBlock. */
/* jshint unused:false */
function OpenAssessmentBlock(runtime, element, data) {
    /**
    Render views within the base view on page load.
    **/
    var server = new OpenAssessment.Server(runtime, element);
    var view = new OpenAssessment.BaseView(runtime, element, server, data);
    view.load();
}
