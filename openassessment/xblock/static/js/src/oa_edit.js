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

    // Initialize the tabs
    $(".openassessment_editor_content_and_tabs", this.element).tabs();

    // Initialize the prompt tab view
    this.promptView = new OpenAssessment.EditPromptView(
        $("#oa_prompt_editor_wrapper", this.element).get(0)
    );

    // Initialize the settings tab view
    this.settingsView = new OpenAssessment.EditSettingsView(
        $("#oa_basic_settings_editor", this.element).get(0), [
            new OpenAssessment.EditPeerAssessmentView(
                $("#oa_peer_assessment_editor", this.element).get(0)
            ),
            new OpenAssessment.EditSelfAssessmentView(
                $("#oa_self_assessment_editor", this.element).get(0)
            ),
            new OpenAssessment.EditStudentTrainingView(
                $("#oa_student_training_editor", this.element).get(0)
            ),
            new OpenAssessment.EditExampleBasedAssessmentView(
                $("#oa_ai_assessment_editor", this.element).get(0)
            )
        ]
    );

    // Initialize the rubric tab view
    this.rubricView = new OpenAssessment.EditRubricView(
        $("#oa_rubric_editor_wrapper", this.element).get(0)
    );

    // Install the save and cancel buttons
    $(".openassessment_save_button", this.element).click($.proxy(this.save, this));
    $(".openassessment_cancel_button", this.element).click($.proxy(this.cancel, this));
};

OpenAssessment.StudioView.prototype = {

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
            view.showError(errMsg);
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
        if (confirm(msg)) { onConfirm(); }
    },

    /**
    Save the updated problem definition to the server.
    **/
    updateEditorContext: function () {
        // Notify the client-side runtime that we are starting
        // to save so it can show the "Saving..." notification
        this.runtime.notify('save', {state: 'start'});

        var view = this;
        this.server.updateEditorContext({
            prompt: view.promptView.promptText(),
            feedbackPrompt: view.rubricView.feedbackPrompt(),
            criteria: view.rubricView.criteriaDefinition(),
            title: view.settingsView.displayName(),
            submissionStart: view.settingsView.submissionStart(),
            submissionDue: view.settingsView.submissionDue(),
            assessments: view.settingsView.assessmentsDescription()
        }).done(
            // Notify the client-side runtime that we finished saving
            // so it can hide the "Saving..." notification.
            // Then reload the view.
            function () { view.runtime.notify('save', {state: 'end'}); }
        ).fail(
            function (msg) { view.showError(msg); }
        );
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
    },
};


/* XBlock entry point for Studio view */
function OpenAssessmentEditor(runtime, element) {

    /**
    Initialize the editing interface on page load.
    **/
    var server = new OpenAssessment.Server(runtime, element);
    var view = new OpenAssessment.StudioView(runtime, element, server);
}
