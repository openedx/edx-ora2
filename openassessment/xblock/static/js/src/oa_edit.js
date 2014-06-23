/**
 Interface for editing view in Studio.
 The constructor initializes the DOM for editing.

 Args:
    runtime (Runtime): an XBlock runtime instance.
    element (DOM element): The DOM element representing this XBlock.
    server (OpenAssessment.Server): The interface to the XBlock server.

 Returns:
    OpenAssessment.StudioView
 **/

OpenAssessment.StudioView = function(runtime, element, server) {
    this.runtime = runtime;
    this.server = server;

    //Instantiates JQuery variables which will allow manipulation and display controls.

    var liveElement = $(element);

    this.promptBox = $('#openassessment_prompt_editor', liveElement).get(0);

    this.titleField = $('#openassessment_title_editor', liveElement).first().get(0);

    this.submissionStartField = $('#openassessment_submission_start_editor', liveElement).first().get(0);

    this.submissionDueField = $('#openassessment_submission_due_editor', liveElement).first().get(0);

    // Finds our boolean checkboxes that indicate the assessment definition
    this.hasPeer = $('#include_peer_assessment', liveElement);
    this.hasSelf = $('#include_self_assessment', liveElement);
    this.hasAI = $('#include_ai_assessment', liveElement);
    this.hasTraining = $('#include_student_training', liveElement);

    this.peerMustGrade = $('#peer_assessment_must_grade', liveElement);
    this.peerGradedBy = $('#peer_assessment_graded_by', liveElement);
    this.peerStart = $('#peer_assessment_start_date', liveElement);
    this.peerDue = $('#peer_assessment_due_date', liveElement);

    this.selfStart = $('#self_assessment_start_date', liveElement);
    this.selfDue = $('#self_assessment_due_date', liveElement);

    //Instantiates our codemirror codeboxes
    this.rubricXmlBox = CodeMirror.fromTextArea(
        $('#openassessment_rubric_editor', liveElement).first().get(0),
        {mode: "xml", lineNumbers: true, lineWrapping: true}
    );

    this.aiTrainingExamplesCodeBox = CodeMirror.fromTextArea(
        $('#ai_training_examples', liveElement).first().get(0),
        {mode: "xml", lineNumbers: true, lineWrapping: true}
    );

    this.studentTrainingExamplesCodeBox = CodeMirror.fromTextArea(
        $('#student_training_examples', liveElement).first().get(0),
        {mode: "xml", lineNumbers: true, lineWrapping: true}
    );

    // Install click handlers
    var view = this;
    $('.openassessment_save_button', liveElement) .click(
        function (eventData) {
            view.save();
        });

    $('.openassessment_cancel_button', liveElement) .click(
        function (eventData) {
            view.cancel();
        });

    $('.openassessment_editor_content_and_tabs', liveElement) .tabs({
        activate: function (event, ui){
            view.rubricXmlBox.refresh();
        }
    });

    $('#include_peer_assessment', liveElement) .change(function () {
        if (this.checked){
            $("#peer_assessment_description_closed", liveElement).fadeOut('fast');
            $("#peer_assessment_settings_editor", liveElement).fadeIn();
        } else {
            $("#peer_assessment_settings_editor", liveElement).fadeOut('fast');
            $("#peer_assessment_description_closed", liveElement).fadeIn();
        }
    });

    $('#include_self_assessment', liveElement) .change(function () {
        if (this.checked){
            $("#self_assessment_description_closed", liveElement).fadeOut('fast');
            $("#self_assessment_settings_editor", liveElement).fadeIn();
        } else {
            $("#self_assessment_settings_editor", liveElement).fadeOut('fast');
            $("#self_assessment_description_closed", liveElement).fadeIn();
        }
    });

    $('#include_ai_assessment', liveElement) .change(function () {
        if (this.checked){
            $("#ai_assessment_description_closed", liveElement).fadeOut('fast');
            $("#ai_assessment_settings_editor", liveElement).fadeIn();
        } else {
            $("#ai_assessment_settings_editor", liveElement).fadeOut('fast');
            $("#ai_assessment_description_closed", liveElement).fadeIn();
        }
    });

    $('#include_student_training', liveElement) .change(function () {
        if (this.checked){
            $("#student_training_description_closed", liveElement).fadeOut('fast');
            $("#student_training_settings_editor", liveElement).fadeIn();
        } else {
            $("#student_training_settings_editor", liveElement).fadeOut('fast');
            $("#student_training_description_closed", liveElement).fadeIn();
        }
    });

};

OpenAssessment.StudioView.prototype = {

    /**
     Load the XBlock XML definition from the server and display it in the view.
     **/
    load: function () {
        var view = this;
        this.server.loadEditorContext().done(
            function (prompt, rubricXml, title, subStart, subDue, assessments) {
                view.rubricXmlBox.setValue(rubricXml);
                view.submissionStartField.value = subStart;
                view.submissionDueField.value = subDue;
                view.promptBox.value = prompt;
                view.titleField.value = title;
                view.hasTraining.prop('checked', false).change();
                view.hasPeer.prop('checked', false).change();
                view.hasSelf.prop('checked', false).change();
                view.hasAI.prop('checked', false).change();
                for (var i = 0; i < assessments.length; i++) {
                    var assessment = assessments[i];
                    if (assessment.name == 'peer-assessment') {
                        view.peerMustGrade.prop('value', assessment.must_grade);
                        view.peerGradedBy.prop('value', assessment.must_be_graded_by);
                        view.peerStart.prop('value', assessment.start);
                        view.peerDue.prop('value', assessment.due);
                        view.hasPeer.prop('checked', true).change();
                    } else if (assessment.name == 'self-assessment') {
                        view.selfStart.prop('value', assessment.start);
                        view.selfDue.prop('value', assessment.due);
                        view.hasSelf.prop('checked', true).change();
                    } else if (assessment.name == 'example-based-assessment') {
                        view.aiTrainingExamplesCodeBox.setValue(assessment.examples);
                        view.hasAI.prop('checked', true).change();
                    } else if (assessment.name == 'student-training') {
                        view.studentTrainingExamplesCodeBox.setValue(assessment.examples);
                        view.hasTraining.prop('checked', true).change();
                    }
                }
            }).fail(function (msg) {
                view.showError(msg);
            }
        );
    },

    /**
     Save the problem's XML definition to the server.
     If the problem has been released, make the user confirm the save.
     **/
    save: function () {
        var view = this;

        // Check whether the problem has been released; if not,
        // warn the user and allow them to cancel.
        this.server.checkReleased().done(
            function (isReleased) {
                if (isReleased) {
                    view.confirmPostReleaseUpdate($.proxy(view.updateEditorContext, view));
                }
                else {
                    view.updateEditorContext();
                }
            }
        ).fail(function (errMsg) {
                view.showError(msg);
        });
    },

    /**
     Make the user confirm that he/she wants to update a problem
     that has already been released.

     Args:
        onConfirm (function): A function that accepts no arguments,
            executed if the user confirms the update.
     **/
    confirmPostReleaseUpdate: function (onConfirm) {
        var msg = gettext("This problem has already been released. Any changes will apply only to future assessments.");
        // TODO: classier confirm dialog
        if (confirm(msg)) {
            onConfirm();
        }
    },

    /**
     Save the updated XML definition to the server.
     **/
    updateEditorContext: function () {
        // Notify the client-side runtime that we are starting
        // to save so it can show the "Saving..." notification
        this.runtime.notify('save', {state: 'start'});

        // Send the updated XML to the server
        var prompt = this.promptBox.value;
        var rubricXml = this.rubricXmlBox.getValue();
        var title = this.titleField.value;
        var subStart = this.submissionStartField.value;
        var subDue = this.submissionDueField.value;

        var assessments = [];

        if (this.hasTraining.prop('checked')){
            assessments[assessments.length] = {
                "name": "student-training",
                "examples": this.studentTrainingExamplesCodeBox.getValue()
            };
        }

        if (this.hasPeer.prop('checked')) {
            var assessment = {
                "name": "peer-assessment",
                "must_grade": parseInt(this.peerMustGrade.prop('value')),
                "must_be_graded_by": parseInt(this.peerGradedBy.prop('value'))
            };
            var startStr = this.peerStart.prop('value');
            var dueStr = this.peerDue.prop('value');
            if (startStr){
                assessment = $.extend(assessment, {"start": startStr})
            }
            if (dueStr){
                assessment = $.extend(assessment, {"due": dueStr})
            }
            assessments[assessments.length] = assessment;
        }

        if (this.hasSelf.prop('checked')) {
            assessment = {
                "name": "self-assessment"
            };
            startStr = this.selfStart.prop('value');
            dueStr = this.selfDue.prop('value');
            if (startStr){
                assessment = $.extend(assessment, {"start": startStr})
            }
            if (dueStr){
                assessment = $.extend(assessment, {"due": dueStr})
            }
            assessments[assessments.length] = assessment;
        }

        if (this.hasAI.prop('checked')) {
            assessments[assessments.length] = {
                "name": "example-based-assessment",
                "examples": this.aiTrainingExamplesCodeBox.getValue()
            };
        }

        var view = this;
        this.server.updateEditorContext(prompt, rubricXml, title, subStart, subDue, assessments).done(function () {
            // Notify the client-side runtime that we finished saving
            // so it can hide the "Saving..." notification.
            view.runtime.notify('save', {state: 'end'});

            // Reload the XML definition in the editor
            view.load();
        }).fail(function (msg) {
            view.showError(msg);
        });
    },

    /**
     Cancel editing.
     **/
    cancel: function () {
        // Notify the client-side runtime so it will close the editing modal.
        this.runtime.notify('cancel', {});
    },

    /**
     Display an error message to the user.

     Args:
        errorMsg (string): The error message to display.
     **/
    showError: function (errorMsg) {
        this.runtime.notify('error', {msg: errorMsg});
    }
};


/* XBlock entry point for Studio view */
function OpenAssessmentEditor(runtime, element) {

    /**
    Initialize the editing interface on page load.
    **/
    var server = new OpenAssessment.Server(runtime, element);
    var view = new OpenAssessment.StudioView(runtime, element, server);
    view.load();
}
