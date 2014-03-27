/* JavaScript for student-facing views of Open Assessment XBlock */

/* Namespace for open assessment */
if (typeof OpenAssessment == "undefined" || !OpenAssessment) {
    OpenAssessment = {};
}


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

    this.responseView = new OpenAssessment.ResponseView(this.element, this.server, this);
    this.gradeView = new OpenAssessment.GradeView(this.element, this.server, this);
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
        onExpand (function): Function to execute when expanding (if provided).  Accepts no args.
    **/
    setUpCollapseExpand: function(parentSel, onExpand) {
        parentSel.find('.ui-toggle-visibility__control').click(
            function(eventData) {
                var sel = $(eventData.target).closest('.ui-toggle-visibility');

                // If we're expanding and have an `onExpand` callback defined, execute it.
                if (sel.hasClass('is--collapsed') && onExpand !== undefined) {
                    onExpand();
                }

                sel.toggleClass('is--collapsed');
            }
        );
    },

    /**
     * Asynchronously load each sub-view into the DOM.
     */
    load: function() {
        this.responseView.load();
        this.renderPeerAssessmentStep();
        this.renderSelfAssessmentStep();
        this.gradeView.load();
    },

    /**
    Render the peer-assessment step.
    **/
    renderPeerAssessmentStep: function() {
        var view = this;
        this.server.render('peer_assessment').done(
            function(html) {

                // Load the HTML
                $('#openassessment__peer-assessment', view.element).replaceWith(html);
                var sel = $('#openassessment__peer-assessment', view.element);

                // Install a click handler for collapse/expand
                view.setUpCollapseExpand(sel, $.proxy(view.renderContinuedPeerAssessmentStep, view));

                // Install a change handler for rubric options to enable/disable the submit button
                sel.find("#peer-assessment--001__assessment").change(
                    function() {
                        var numChecked = $('input[type=radio]:checked', this).length;
                        var numAvailable = $('.field--radio.assessment__rubric__question', this).length;
                        $("#peer-assessment--001__assessment__submit", view.element).toggleClass(
                            'is--disabled', numChecked != numAvailable
                        );
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

            }
        ).fail(function(errMsg) {
            view.showLoadError('peer-assessment');
        });
    },

    /**
     * Render the peer-assessment step for continued grading. Always renders as
     * expanded, since this should be called for an explicit continuation of the
     * peer grading process.
     */
    renderContinuedPeerAssessmentStep: function() {
        var view = this;
        this.server.renderContinuedPeer().done(
            function(html) {

                // Load the HTML
                $('#openassessment__peer-assessment', view.element).replaceWith(html);
                var sel = $('#openassessment__peer-assessment', view.element);

                // Install a click handler for collapse/expand
                view.setUpCollapseExpand(sel);

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
                        $("#peer-assessment--001__assessment__submit", view.element).toggleClass(
                            'is--disabled', numChecked != numAvailable
                        );
                    }
                );
            }
        ).fail(function(errMsg) {
            view.showLoadError('peer-assessment');
        });
    },

    /**
    Render the self-assessment step.
    **/
    renderSelfAssessmentStep: function() {
        var view = this;
        this.server.render('self_assessment').done(
            function(html) {

                // Load the HTML
                $('#openassessment__self-assessment', view.element).replaceWith(html);
                var sel = $('#openassessment__self-assessment', view.element);

                // Install a click handler for collapse/expand
                view.setUpCollapseExpand(sel);

                // Install a change handler for rubric options to enable/disable the submit button
                $("#self-assessment--001__assessment", view.element).change(
                    function() {
                        var numChecked = $('input[type=radio]:checked', this).length;
                        var numAvailable = $('.field--radio.assessment__rubric__question', this).length;
                        $("#self-assessment--001__assessment__submit", view.element).toggleClass(
                            'is--disabled', numChecked != numAvailable
                        );
                    }
                );

                // Install a click handler for the submit button
                sel.find('#self-assessment--001__assessment__submit').click(
                    function(eventObject) {
                        // Override default form submission
                        eventObject.preventDefault();

                        // Handle the click
                        view.selfAssess();
                    }
                );
            }
        ).fail(function(errMsg) {
            view.showLoadError('self-assessment');
        });
    },

    /**
    Send an assessment to the server and update the view.
    **/
    peerAssess: function() {
        var view = this;
        this.peerAssessRequest(function() {
            view.renderPeerAssessmentStep();
            view.renderSelfAssessmentStep();
            view.gradeView.load();
            view.scrollToTop();
        });
    },

    /**
     * Send an assessment to the server and update the view, with the assumption
     * that we are continuing peer assessments beyond the required amount.
     */
    continuedPeerAssess: function() {
        var view = this;
        view.peerAssessRequest(function() {
            view.renderContinuedPeerAssessmentStep();
            view.gradeView.load();
        });
    },

    /**
     * Common peer assessment request building, used for all types of peer
     * assessments.
     *
     * Args:
     *      successFunction (function): The function called if the request is
     *          successful. This varies based on the type of request to submit
     *          a peer assessment.
     */
    peerAssessRequest: function(successFunction) {
        // Retrieve assessment info from the DOM
        var submissionId = $("#peer_submission_uuid", this.element)[0].innerHTML.trim();
        var optionsSelected = {};
        $("#peer-assessment--001__assessment input[type=radio]:checked", this.element).each(
            function(index, sel) {
                optionsSelected[sel.name] = sel.value;
            }
        );
        var feedback = $('#assessment__rubric__question--feedback__value', this.element).val();

        // Send the assessment to the server
        var view = this;
        this.toggleActionError('peer', null);
        this.server.peerAssess(submissionId, optionsSelected, feedback).done(
                successFunction
            ).fail(function(errMsg) {
                view.toggleActionError('peer', errMsg);
            });
    },

    /**
    Send a self-assessment to the server and update the view.
    **/
    selfAssess: function() {
        // Retrieve self-assessment info from the DOM
        var submissionId = $("#self_submission_uuid", this.element)[0].innerHTML.trim();
        var optionsSelected = {};
        $("#self-assessment--001__assessment input[type=radio]:checked", this.element).each(
            function(index, sel) {
                optionsSelected[sel.name] = sel.value;
            }
        );

        // Send the assessment to the server
        var view = this;
        this.toggleActionError('self', null);
        this.server.selfAssess(submissionId, optionsSelected).done(
            function() {
                view.renderPeerAssessmentStep();
                view.renderSelfAssessmentStep();
                view.gradeView.load();
                view.scrollToTop();
            }
        ).fail(function(errMsg) {
            view.toggleActionError('self', errMsg);
        });
    },


    /**
    Report an error to the user.

    Args:
        type (str): Which type of error.  Options are "save", submit", "peer", and "self".
        msg (str or null): The error message to display.
            If null, hide the error message (with one exception: loading errors are never hidden once displayed)
    **/
    toggleActionError: function(type, msg) {
        var container = null;
        if (type == 'save') { container = '.response__submission__actions'; }
        else if (type == 'submit') { container = '.step__actions'; }
        else if (type == 'peer') { container = '.step__actions'; }
        else if (type == 'self') { container = '.self-assessment__actions'; }
        else if (type == 'feedback_assess') { container = '.submission__feedback__actions'; }

        // If we don't have anywhere to put the message, just log it to the console
        if (container === null) {
            if (msg !== null) { console.log(msg); }
        }

        else {
            // Insert the error message
            var msgHtml = (msg === null) ? "" : msg;
            $(container + " .message__content").html('<p>' + msgHtml + '</p>');

            // Toggle the error class
            $(container).toggleClass('has--error', msg !== null);
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
        $(container + ' .step__status__value .copy').html('Unable to Load');
    }
};

/* XBlock JavaScript entry point for OpenAssessmentXBlock. */
function OpenAssessmentBlock(runtime, element) {
    /**
    Render views within the base view on page load.
    **/
    $(function($) {
        var server = new OpenAssessment.Server(runtime, element);
        var view = new OpenAssessment.BaseView(runtime, element, server);
        view.load();
    });
}
