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
                view.installHandlers();
            }
        ).fail(function(errMsg) {
            view.showLoadError('peer-assessment');
        });
    },

    /**
    Load the continued grading version of the view.
    This is a version of the peer grading step that a student
    can use to continue assessing peers after they've completed
    their peer assessment requirements.
    **/
    loadContinuedAssessment: function() {
        var view = this;
        this.server.renderContinuedPeer().done(
            function(html) {
                // Load the HTML and install event handlers
                $('#openassessment__peer-assessment', view.element).replaceWith(html);
                view.installHandlersForContinuedAssessment();
            }
        ).fail(function(errMsg) {
            view.showLoadError('peer-assessment');
        });
    },

    /**
    Install event handlers for the view.
    **/
    installHandlers: function() {
        var sel = $('#openassessment__peer-assessment', this.element);
        var view = this;

        // Install a click handler for collapse/expand
        this.baseView.setUpCollapseExpand(sel, $.proxy(view.loadContinuedAssessment, view));

        // Install a change handler for rubric options to enable/disable the submit button
        sel.find("#peer-assessment--001__assessment").change(
            function() {
                var numChecked = $('input[type=radio]:checked', this).length;
                var numAvailable = $('.field--radio.assessment__rubric__question', this).length;
                view.peerSubmitEnabled(numChecked == numAvailable);
            }
        );

        // Install a click handler for assessment
        sel.find('#peer-assessment--001__assessment__submit').click(
            function(eventObject) {
                // Override default form submission
                eventObject.preventDefault();

                // Handle the click
                view.peerAssess();
            }
        );
    },

    /**
    Install event handlers for the continued grading version of the view.
    **/
    installHandlersForContinuedAssessment: function() {
        var sel = $('#openassessment__peer-assessment', this.element);
        var view = this;

        // Install a click handler for collapse/expand
        this.baseView.setUpCollapseExpand(sel);

        // Install a click handler for assessment
        sel.find('#peer-assessment--001__assessment__submit').click(
            function(eventObject) {
                // Override default form submission
                eventObject.preventDefault();

                // Handle the click
                view.continuedPeerAssess();
            }
        );

        // Install a change handler for rubric options to enable/disable the submit button
        sel.find("#peer-assessment--001__assessment").change(
            function() {
                var numChecked = $('input[type=radio]:checked', this).length;
                var numAvailable = $('.field--radio.assessment__rubric__question', this).length;
                view.peerSubmitEnabled(numChecked == numAvailable);
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
            view.load();
            baseView.renderSelfAssessmentStep();
            baseView.gradeView.load();
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
    Get or set overall feedback on the submission.

    Args:
        overallFeedback (string or undefined): The overall feedback text (optional).

    Returns:
        string or undefined

    Example usage:
        >>> view.overallFeedback('Good job!');  // Set the feedback text
        >>> view.overallFeedback();  // Retrieve the feedback text
        'Good job!'

    **/
    overallFeedback: function(overallFeedback) {
        var selector = '#assessment__rubric__question--feedback__value';
        if (typeof overallFeedback === 'undefined') {
            return $(selector, this.element).val();
        }
        else {
            $(selector, this.element).val(overallFeedback);
        }
    },

    /**
    Get or set per-criterion feedback.

    Args:
        criterionFeedback (object literal or undefined):
            Map of criterion names to feedback strings.

    Returns:
        object literal or undefined

    Example usage:
        >>> view.criterionFeedback({'ideas': 'Good ideas'});  // Set per-criterion feedback
        >>> view.criterionFeedback(); // Retrieve criterion feedback
        {'ideas': 'Good ideas'}

    **/
    criterionFeedback: function(criterionFeedback) {
        var selector = '#peer-assessment--001__assessment textarea.answer__value';
        var feedback = {};
        $(selector, this.element).each(
            function(index, sel) {
                if (typeof criterionFeedback !== 'undefined') {
                    $(sel).val(criterionFeedback[sel.name]);
                    feedback[sel.name] = criterionFeedback[sel.name];
                }
                else {
                    feedback[sel.name] = $(sel).val();
                }
            }
        );
        return feedback;
    },

    /**
    Get or set the options selected in the rubric.

    Args:
        optionsSelected (object literal or undefined):
            Map of criterion names to option values.

    Returns:
        object literal or undefined

    Example usage:
        >>> view.optionsSelected({'ideas': 'Good'});  // Set the criterion option
        >>> view.optionsSelected(); // Retrieve the options selected
        {'ideas': 'Good'}

    **/
    optionsSelected: function(optionsSelected) {
        var selector = "#peer-assessment--001__assessment input[type=radio]";
        if (typeof optionsSelected === 'undefined') {
            var options = {};
            $(selector + ":checked", this.element).each(
                function(index, sel) {
                    options[sel.name] = sel.value;
                }
            );
            return options;
        }
        else {
            // Uncheck all the options
            $(selector, this.element).prop('checked', false);

            // Check the selected options
            $(selector, this.element).each(function(index, sel) {
                if (optionsSelected.hasOwnProperty(sel.name)) {
                    if (sel.value == optionsSelected[sel.name]) {
                        $(sel).prop('checked', true);
                    }
                }
            });
        }
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
            this.optionsSelected(),
            this.criterionFeedback(),
            this.overallFeedback()
        ).done(
            successFunction
        ).fail(function(errMsg) {
            view.baseView.toggleActionError('peer', errMsg);
            view.peerSubmitEnabled(true);
        });
    },
};
