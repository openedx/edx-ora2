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
    OpenAssessment.BaseUI
**/
OpenAssessment.BaseUI = function(runtime, element, server) {
    this.runtime = runtime;
    this.element = element;
    this.server = server;
};


OpenAssessment.BaseUI.prototype = {
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
        this.renderSubmissionStep();
        this.renderPeerAssessmentStep();
        this.renderSelfAssessmentStep();
        this.renderGradeStep();
    },

    /**
    Render the submission step.
    **/
    renderSubmissionStep: function() {
        var ui = this;
        this.server.render('submission').done(
            function(html) {

                // Load the HTML
                $('#openassessment__response', ui.element).replaceWith(html);
                var sel = $('#openassessment__response', ui.element);

                // Install a click handler for collapse/expand
                ui.setUpCollapseExpand(sel);

                // If we have a saved submission, enable the submit button
                ui.responseChanged();

                // Install change handler for textarea (to enable submission button)
                sel.find('#submission__answer__value').keyup(
                    function(eventData) { ui.responseChanged(); }
                );

                // Install a click handler for submission
                sel.find('#step--response__submit').click(
                    function(eventObject) {
                        // Override default form submission
                        eventObject.preventDefault();

                        ui.submit();
                    }
                );

                // Install a click handler for the save button
                sel.find('#submission__save').click(
                    function(eventObject) {
                        // Override default form submission
                        eventObject.preventDefault();
                        ui.save();
                    }
                );
                
            }
        ).fail(function(errMsg) {
            ui.showLoadError('response');
        });
    },

    /**
    Enable/disable the submission and save buttons based on whether
    the user has entered a response.
    **/
    responseChanged: function() {
        var blankSubmission = ($('#submission__answer__value', this.element).val() === '');
        $('#step--response__submit', this.element).toggleClass('is--disabled', blankSubmission);
        $('#submission__save', this.element).toggleClass('is--disabled', blankSubmission);
    },

    /**
    Render the peer-assessment step.
    **/
    renderPeerAssessmentStep: function() {
        var ui = this;
        this.server.render('peer_assessment').done(
            function(html) {

                // Load the HTML
                $('#openassessment__peer-assessment', ui.element).replaceWith(html);
                var sel = $('#openassessment__peer-assessment', ui.element);

                // Install a click handler for collapse/expand
                ui.setUpCollapseExpand(sel, $.proxy(ui.renderContinuedPeerAssessmentStep, ui));

                // Install a change handler for rubric options to enable/disable the submit button
                sel.find("#peer-assessment--001__assessment").change(
                    function() {
                        var numChecked = $('input[type=radio]:checked', this).length;
                        var numAvailable = $('.field--radio.assessment__rubric__question', this).length;
                        $("#peer-assessment--001__assessment__submit", ui.element).toggleClass(
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
                        ui.peerAssess();
                    }
                );

            }
        ).fail(function(errMsg) {
            ui.showLoadError('peer-assessment');
        });
    },

    /**
     * Render the peer-assessment step for continued grading. Always renders as
     * expanded, since this should be called for an explicit continuation of the
     * peer grading process.
     */
    renderContinuedPeerAssessmentStep: function() {
        var ui = this;
        this.server.renderContinuedPeer().done(
            function(html) {

                // Load the HTML
                $('#openassessment__peer-assessment', ui.element).replaceWith(html);
                var sel = $('#openassessment__peer-assessment', ui.element);

                // Install a click handler for collapse/expand
                ui.setUpCollapseExpand(sel);

                // Install a click handler for assessment
                sel.find('#peer-assessment--001__assessment__submit').click(
                    function(eventObject) {
                        // Override default form submission
                        eventObject.preventDefault();

                        // Handle the click
                        ui.continuedPeerAssess();
                    }
                );

                // Install a change handler for rubric options to enable/disable the submit button
                sel.find("#peer-assessment--001__assessment").change(
                    function() {
                        var numChecked = $('input[type=radio]:checked', this).length;
                        var numAvailable = $('.field--radio.assessment__rubric__question', this).length;
                        $("#peer-assessment--001__assessment__submit", ui.element).toggleClass(
                            'is--disabled', numChecked != numAvailable
                        );
                    }
                );
            }
        ).fail(function(errMsg) {
            ui.showLoadError('peer-assessment');
        });
    },

    /**
    Render the self-assessment step.
    **/
    renderSelfAssessmentStep: function() {
        var ui = this;
        this.server.render('self_assessment').done(
            function(html) {

                // Load the HTML
                $('#openassessment__self-assessment', ui.element).replaceWith(html);
                var sel = $('#openassessment__self-assessment', ui.element);

                // Install a click handler for collapse/expand
                ui.setUpCollapseExpand(sel);

                // Install a change handler for rubric options to enable/disable the submit button
                $("#self-assessment--001__assessment", ui.element).change(
                    function() {
                        var numChecked = $('input[type=radio]:checked', this).length;
                        var numAvailable = $('.field--radio.assessment__rubric__question', this).length;
                        $("#self-assessment--001__assessment__submit", ui.element).toggleClass(
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
                        ui.selfAssess();
                    }
                );
            }
        ).fail(function(errMsg) {
            ui.showLoadError('self-assessment');
        });
    },

    /**
    Render the grade step.
    **/
    renderGradeStep: function() {
        var ui = this;
        this.server.render('grade').done(
            function(html) {
                // Load the HTML
                $('#openassessment__grade', ui.element).replaceWith(html);
                
                // Install a click handler for collapse/expand
                var sel = $('#openassessment__grade', ui.element);
                ui.setUpCollapseExpand(sel);

                // Install a click handler for assessment feedback
                sel.find('#feedback__submit').click(function(eventObject) {
                        eventObject.preventDefault();
                        ui.feedback_assess();
                });
            }
        ).fail(function(errMsg) {
            ui.showLoadError('grade', errMsg);
        });
        
    },

    /**
    Save a response without submitting it.
    **/
    save: function() {
        // Retrieve the student's response from the DOM
        var submission = $('#submission__answer__value', this.element).val();
        var ui = this;
        this.setSaveStatus('Saving...');
        this.toggleActionError('save', null);
        this.server.save(submission).done(function() {
            ui.setSaveStatus("Saved but not submitted");
        }).fail(function(errMsg) {
            ui.setSaveStatus('Error');
            ui.toggleActionError('save', errMsg);
        });
    },

    /**
    Display a save status message.

    Args:
        msg (str): The message to display.
    **/
    setSaveStatus: function(msg) {
        $('#response__save_status h3', this.element).html(msg);
    },

    /**
    Send a submission to the server and update the UI.
    **/
    submit: function() {
        // Send the submission to the server
        var submission = $('#submission__answer__value', this.element).val();
        var ui = this;
        this.toggleActionError('response', null);
        this.server.submit(submission).done(
            // When we have successfully sent the submission, expand the next step
            function(studentId, attemptNum) {
                ui.renderSubmissionStep();
                ui.renderPeerAssessmentStep();
            }
        ).fail(function(errCode, errMsg) {
            ui.toggleActionError('submit', errMsg);
        });
    },

    /**
    Send assessment feedback to the server and update the UI.
    **/
    feedback_assess: function() {
        // Send the submission to the server
        var feedback = $('#feedback__remarks__value', this.element).val();
        var ui = this;
        this.server.feedback_submit(feedback).done(
            // When we have successfully sent the submission, textarea no longer editable
            console.log("Feedback to the assessments submitted, thanks!")
        ).fail(function(errMsg) {
            // TODO: display to the user
            ui.toggleActionError('feedback_assess', errMsg);
        });
    },

    /**
    Send an assessment to the server and update the UI.
    **/
    peerAssess: function() {
        var ui = this;
        ui.peerAssessRequest(function() {
            ui.renderPeerAssessmentStep();
            ui.renderSelfAssessmentStep();
            ui.renderGradeStep();
        });
    },

    /**
     * Send an assessment to the server and update the UI, with the assumption
     * that we are continuing peer assessments beyond the required amount.
     */
    continuedPeerAssess: function() {
        var ui = this;
        ui.peerAssessRequest(function() {
            ui.renderContinuedPeerAssessmentStep();
            ui.renderGradeStep();
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
        var submissionId = $("span#peer_submission_uuid", this.element)[0].innerHTML.trim();
        var optionsSelected = {};
        $("#peer-assessment--001__assessment input[type=radio]:checked", this.element).each(
            function(index, sel) {
                optionsSelected[sel.name] = sel.value;
            }
        );
        var feedback = $('#assessment__rubric__question--feedback__value', this.element).val();

        // Send the assessment to the server
        var ui = this;
        this.toggleActionError('peer', null);
        this.server.peerAssess(submissionId, optionsSelected, feedback).done(
                successFunction
            ).fail(function(errMsg) {
                ui.toggleActionError('peer', errMsg);
            });
    },

    /**
    Send a self-assessment to the server and update the UI.
    **/
    selfAssess: function() {
        // Retrieve self-assessment info from the DOM
        var submissionId = $("span#self_submission_uuid", this.element)[0].innerHTML.trim();
        var optionsSelected = {};
        $("#self-assessment--001__assessment input[type=radio]:checked", this.element).each(
            function(index, sel) {
                optionsSelected[sel.name] = sel.value;
            }
        );

        // Send the assessment to the server
        var ui = this;
        this.toggleActionError('self', null);
        this.server.selfAssess(submissionId, optionsSelected).done(
            function() {
                ui.renderPeerAssessmentStep();
                ui.renderSelfAssessmentStep();
                ui.renderGradeStep();
            }
        ).fail(function(errMsg) {
            ui.toggleActionError('self', errMsg);
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
        else if (type == 'peer') { container = '.peer-assessment__actions'; }
        else if (type == 'self') { container = '.self-assessment__actions'; }

        // If we don't have anywhere to put the message, just log it to the console
        if (container === null) {
            if (msg !== null) { console.log(msg); }
        }

        else {
            // Insert the error message
            var msgHtml = (msg === null) ? "" : msg;
            $(container + " .message__content").html('<p>' + msg + '</p>');

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
        $(container + ' .step__status__value i').removeClass().addClass('icon-warning-sign');
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
        var ui = new OpenAssessment.BaseUI(runtime, element, server);
        ui.load();
    });
}
