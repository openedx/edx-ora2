/**
Interface for student-facing views.

Args:
    runtime (Runtime): an XBlock runtime instance.
    element (DOM element): The DOM element representing this XBlock.
    server (OpenAssessment.Server): The interface to the XBlock server.

Returns:
    OpenAssessment.BaseView
**/
OpenAssessment.BaseView = function(runtime, element, server) {
    this.runtime = runtime;
    this.element = element;
    this.server = server;
    this.fileUploader = new OpenAssessment.FileUploader();

    this.responseView = new OpenAssessment.ResponseView(this.element, this.server, this.fileUploader, this);
    this.trainingView = new OpenAssessment.StudentTrainingView(this.element, this.server, this);
    this.selfView = new OpenAssessment.SelfView(this.element, this.server, this);
    this.peerView = new OpenAssessment.PeerView(this.element, this.server, this);
    this.gradeView = new OpenAssessment.GradeView(this.element, this.server, this);
    this.leaderboardView = new OpenAssessment.LeaderboardView(this.element, this.server, this);
    this.messageView = new OpenAssessment.MessageView(this.element, this.server, this);
    this.trackChangesView = new OpenAssessment.TrackChangesView(this.element, this.server, this);
    // Staff only information about student progress.
    this.staffInfoView = new OpenAssessment.StaffInfoView(this.element, this.server, this);
};


OpenAssessment.BaseView.prototype = {

    /**
     * Checks to see if the scrollTo function is available, then scrolls to the
     * top of the list of steps for this display.
     *
     * Ideally, we would not need to check if the function exists, and could
     * import scrollTo, or other dependencies, into workbench.
     */
    scrollToTop: function() {
        if ($.scrollTo instanceof Function) {
            $(window).scrollTo($("#openassessment__steps"), 800, {offset:-50});
        }
    },

    /**
    Install click handlers to expand/collapse a section.

    Args:
        parentSel (JQuery selector): CSS selector for the container element.
    **/
    setUpCollapseExpand: function(parentSel) {
        parentSel.find('.ui-toggle-visibility__control').click(
            function(eventData) {
                var sel = $(eventData.target).closest('.ui-toggle-visibility');
                sel.toggleClass('is--collapsed');
            }
        );
    },

    /**
     Asynchronously load each sub-view into the DOM.
     **/
    load: function() {
        this.responseView.load();
        this.loadAssessmentModules();
        this.staffInfoView.load();
    },

    /**
     Refresh the Assessment Modules. This should be called any time an action is
     performed by the user.
     **/
    loadAssessmentModules: function() {
        this.trainingView.load();
        this.peerView.load();
        this.selfView.load();
        this.gradeView.load();
        this.leaderboardView.load();
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
    Refresh the message only (called by PeerView to update and avoid race condition)
    **/
    loadMessageView: function() {
        this.messageView.load();
    },

    /**
    Enable TrackChanges
    **/
    enableTrackChangesView: function () {
        this.trackChangesView.enableTrackChanges();
    },

    /**
    Display TrackChanges View
    **/
    displayTrackChangesView: function () {
        this.trackChangesView.displayTrackChanges();
    },

    /**
    Report an error to the user.

    Args:
        type (str): Which type of error.  Options are "save", submit", "peer", and "self".
        msg (str or null): The error message to display.
            If null, hide the error message (with one exception: loading errors are never hidden once displayed)
    **/
    toggleActionError: function(type, msg) {
        var element = this.element;
        var container = null;
        if (type == 'save') {
            container = '.response__submission__actions';
        }
        else if (type == 'submit' || type == 'peer' || type == 'self' || type == 'student-training') {
            container = '.step__actions';
        }
        else if (type == 'feedback_assess') {
            container = '.submission__feedback__actions';
        }
        else if (type == 'upload') {
            container = '#upload__error';
        }

        // If we don't have anywhere to put the message, just log it to the console
        if (container === null) {
            if (msg !== null) { console.log(msg); }
        }

        else {
            // Insert the error message
            var msgHtml = (msg === null) ? "" : msg;
            $(container + " .message__content", element).html('<p>' + msgHtml + '</p>');
            // Toggle the error class
            $(container, element).toggleClass('has--error', msg !== null);
        }
    },

    /**
    Report an error loading a step.

    Args:
        step (str): the step that could not be loaded.
    **/
    showLoadError: function(step) {
        var container = '#openassessment__' + step;
        $(container).toggleClass('has--error', true);
        $(container + ' .step__status__value i').removeClass().addClass('ico icon-warning-sign');
        $(container + ' .step__status__value .copy').html(gettext('Unable to Load'));
    }
};

/* XBlock JavaScript entry point for OpenAssessmentXBlock. */
function OpenAssessmentBlock(runtime, element) {
    /**
    Render views within the base view on page load.
    **/
    var server = new OpenAssessment.Server(runtime, element);
    var view = new OpenAssessment.BaseView(runtime, element, server);
    view.load();
}
