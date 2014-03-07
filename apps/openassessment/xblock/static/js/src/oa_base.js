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
    Collapse one of the steps in the workflow.

    Args:
        stepName (string): The name of the step to expand/collapse.
        expanded (bool): If true, expand the step; otherwise, collapse it.
    **/
    setExpanded: function(stepName, expanded) {
        var el = $("#openassessment__" + stepName, this.element);

        if (expanded) {
            el.removeClass('is--collapsed');
        }
        else {
            el.addClass('is--collapsed');
        }
    },

    /**
    Asynchronously load each sub-view into the DOM.
    **/
    load: function() {
        this.renderSubmissionStep(true);
        this.renderPeerAssessmentStep(false);
        this.renderSelfAssessmentStep(false);
        this.renderGradeStep(false);
    },

    /**
    Render the submission step.

    Args:
        expanded (bool): If true, expand the step.
    **/
    renderSubmissionStep: function(expand) {
        var ui = this;
        this.server.render('submission').done(
            function(html) {
                // Load the HTML
                var sel = $('#openassessment__response', ui.element);
                sel.replaceWith(html);
                ui.setExpanded('response', expand);

                // Install a click handler for submission
                $('#step--response__submit', ui.element).click(
                    function(eventObject) { ui.submit(); }
                );

                // Install a click handler for the save button
                $('#submission__save', ui.element).click(
                    function(eventObject) {
                        // Override default form submission
                        eventObject.preventDefault();
                        ui.save();
                    }
                );
            }
        ).fail(function(errMsg) {
            // TODO: display to the user
            console.log(errMsg);
        });
    },

    /**
    Render the peer-assessment step.

    Args:
        expand (bool): If true, expand the step.
    **/
    renderPeerAssessmentStep: function(expand) {
        var ui = this;
        this.server.render('peer_assessment').done(
            function(html) {
                // Load the HTML
                var sel = $('#openassessment__peer-assessment', ui.element);
                sel.replaceWith(html);
                ui.setExpanded('peer-assessment', expand);

                // Install a click handler for assessment
                $('#peer-assessment--001__assessment__submit', ui.element).click(
                    function(eventObject) {
                        // Override default form submission
                        eventObject.preventDefault();

                        // Handle the click
                        ui.assess();
                    }
                );
            }
        ).fail(function(errMsg) {
            // TODO: display to the user
            console.log(errMsg);
        });
    },

    /**
    Render the self-assessment step.

    Args:
        expand (bool): If true, expand the step.
    **/
    renderSelfAssessmentStep: function(expand) {
        var ui = this;
        this.server.render('self_assessment').done(
            function(html) {
                $('#openassessment__self-assessment', ui.element).replaceWith(html);
                ui.setExpanded('self-assessment', expand);
            }
        ).fail(function(errMsg) {
            // TODO: display to the user
            console.log(errMsg);
        });
    },

    /**
    Render the grade step.

    Args:
        expand (bool): If true, expand the step.
    **/
    renderGradeStep: function(expand) {
        var ui = this;
        this.server.render('grade').done(
            function(html) {
                $('#openassessment__grade', ui.element).replaceWith(html);
                ui.setExpanded('grade', expand);
            }
        ).fail(function(errMsg) {
            // TODO: display to the user
            console.log(errMsg);
        });
    },

    /**
    Save a response without submitting it.
    **/
    save: function() {
        // Retrieve the student's response from the DOM
        var submission = $('#submission__answer__value', this.element).val();
        var ui = this;
        this.server.save(submission).done(function() {
            // Update the "saved" icon
            $('#response__save_status', this.element).replaceWith("Saved");
        }).fail(function(errMsg) {
            // TODO: display to the user
            console.log(errMsg);
        });

    },

    /**
    Send a submission to the server and update the UI.
    **/
    submit: function() {
        // Send the submission to the server
        var submission = $('#submission__answer__value', this.element).val();
        var ui = this;
        this.server.submit(submission).done(
            // When we have successfully sent the submission, expand the next step
            function(studentId, attemptNum) {
                ui.renderSubmissionStep();
                ui.renderPeerAssessmentStep(true);
            }
        ).fail(function(errMsg) {
            // TODO: display to the user
            console.log(errMsg);
        });
    },

    /**
    Send an assessment to the server and update the UI.
    **/
    assess: function() {
        // Retrieve assessment info from the DOM
        var submissionId = $("span#peer_submission_uuid", this.element)[0].innerText;
        var optionsSelected = {};
        $("input[type=radio]:checked", this.element).each(
            function(index, sel) {
                optionsSelected[sel.name] = sel.value;
            }
        );
        var feedback = $('#assessment__rubric__question--feedback__value', this.element).val();

        // Send the assessment to the server
        var ui = this;
        this.server.assess(submissionId, optionsSelected, feedback).done(
            function() {
                // When we have successfully sent the assessment, expand the next step
                ui.renderPeerAssessmentStep(true);
                ui.renderSelfAssessmentStep(true);
                ui.renderGradeStep(true);
            }
        ).fail(function(errMsg) {
            // TODO: display to the user
            console.log(errMsg);
        });
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
