/**
Interface for peer asssessment view.

Args:
    element (DOM element): The DOM element representing the XBlock.
    server (OpenAssessment.Server): The interface to the XBlock server.
    baseView (OpenAssessment.BaseView): Container view.

Returns:
    OpenAssessment.PeerView
**/
OpenAssessment.PeerView = function(element, server, baseView) {
    this.element = element;
    this.server = server;
    this.baseView = baseView;
    this.rubric = null;
};


OpenAssessment.PeerView.prototype = {

    /**
    Load the peer assessment view.
    **/
    load: function() {
        var view = this;
        this.server.render('peer_assessment').done(
            function(html) {
                // Load the HTML and install event handlers
                $('#openassessment__peer-assessment', view.element).replaceWith(html);
                view.installHandlers(false);
            }
        ).fail(function(errMsg) {
            view.baseView.showLoadError('peer-assessment');
        });
        // Called to update Messagview with info on whether or not it was able to grab a submission
        // See detailed explanation/Methodology in oa_base.loadAssessmentModules
        view.baseView.loadMessageView();
    },

    /**
    Load the continued grading version of the view.
    This is a version of the peer grading step that a student
    can use to continue assessing peers after they've completed
    their peer assessment requirements.
    **/
    loadContinuedAssessment: function() {
        var view = this;
        view.continueAssessmentEnabled(false);
        this.server.renderContinuedPeer().done(
            function(html) {
                // Load the HTML and install event handlers
                $('#openassessment__peer-assessment', view.element).replaceWith(html);
                view.installHandlers(true);
            }
        ).fail(function(errMsg) {
            view.baseView.showLoadError('peer-assessment');
            view.continueAssessmentEnabled(true);
        });
    },

    /**
    Enable and disable the continue assessment button.

    Args:
        enabled (bool): If specified, sets the button as enabled or disabled.
            if not specified, return the current value.

    Returns:
        A boolean. TRUE if the continue assessment button is enabled.

    **/
    continueAssessmentEnabled: function(enabled) {
        var button = $('#peer-assessment__continue__grading', this.element);
        if (typeof enabled === 'undefined') {
            return !button.hasClass('is--disabled');
        } else {
            button.toggleClass('is--disabled', !enabled);
        }
    },

    /**
    Install event handlers for the view.

    Args:
        isContinuedAssessment (boolean): If true, we are in "continued grading" mode,
            meaning that the user is continuing to grade even though she has met
            the requirements.
    **/
    installHandlers: function(isContinuedAssessment) {
        var sel = $('#openassessment__peer-assessment', this.element);
        var view = this;

        // Install a click handler for collapse/expand
        this.baseView.setUpCollapseExpand(sel);

        // Initialize the rubric
        var rubricSelector = $("#peer-assessment--001__assessment", this.element);
        if (rubricSelector.size() > 0) {
            var rubricElement = rubricSelector.get(0);
            this.rubric = new OpenAssessment.Rubric(rubricElement);
        }

        // Install a change handler for rubric options to enable/disable the submit button
        if (this.rubric !== null) {
            this.rubric.canSubmitCallback($.proxy(view.peerSubmitEnabled, view));
        }

        // Install a click handler for assessment
        sel.find('#peer-assessment--001__assessment__submit').click(
            function(eventObject) {
                // Override default form submission
                eventObject.preventDefault();

                // Handle the click
                if (!isContinuedAssessment) { view.peerAssess(); }
                else { view.continuedPeerAssess(); }
            }
        );

        // Install a click handler for continued assessment
        sel.find('#peer-assessment__continue__grading').click(
            function(eventObject) {
                eventObject.preventDefault();
                view.loadContinuedAssessment();
            }
        );
    },

    /**
     Enable/disable the peer assess button button.
     Check that whether the peer assess button is enabled.

     Args:
     enabled (bool): If specified, set the state of the button.

     Returns:
     bool: Whether the button is enabled.

     Examples:
     >> view.peerSubmitEnabled(true);  // enable the button
     >> view.peerSubmitEnabled();  // check whether the button is enabled
     >> true
     **/
    peerSubmitEnabled: function(enabled) {
        var button = $('#peer-assessment--001__assessment__submit', this.element);
        if (typeof enabled === 'undefined') {
            return !button.hasClass('is--disabled');
        } else {
            button.toggleClass('is--disabled', !enabled);
        }
    },

    /**
    Send an assessment to the server and update the view.
    **/
    peerAssess: function() {
        var view = this;
        var baseView = view.baseView;
        this.peerAssessRequest(function() {
            baseView.loadAssessmentModules();
            baseView.scrollToTop();
        });
    },

    /**
     * Send an assessment to the server and update the view, with the assumption
     * that we are continuing peer assessments beyond the required amount.
     */
    continuedPeerAssess: function() {
        var view = this;
        var gradeView = this.baseView.gradeView;
        var baseView = view.baseView;
        view.peerAssessRequest(function() {
            view.loadContinuedAssessment();
            gradeView.load();
            baseView.scrollToTop();
        });
    },

    /**
    Common peer assessment request building, used for all types of peer assessments.

    Args:
        successFunction (function): The function called if the request is
            successful. This varies based on the type of request to submit
            a peer assessment.

    **/
    peerAssessRequest: function(successFunction) {
        var view = this;
        view.baseView.toggleActionError('peer', null);
        view.peerSubmitEnabled(false);

        // Pull the assessment info from the DOM and send it to the server
        this.server.peerAssess(
            this.rubric.optionsSelected(),
            this.rubric.criterionFeedback(),
            this.rubric.overallFeedback()
        ).done(
            successFunction
        ).fail(function(errMsg) {
            view.baseView.toggleActionError('peer', errMsg);
            view.peerSubmitEnabled(true);
        });
    },


};
