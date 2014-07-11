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
    this.element = element;
    this.runtime = runtime;
    this.server = server;

    // Resize the editing modal
    this.fixModalHeight();

    // Initialize the tabs
    $(".openassessment_editor_content_and_tabs", this.element).tabs();

    // Initialize the prompt tab view
    this.promptView = new OpenAssessment.EditPromptView(
        $("#oa_prompt_editor_wrapper", this.element).get(0)
    );

    // Initialize the settings tab view
    var studentTrainingView = new OpenAssessment.EditStudentTrainingView(
        $("#oa_student_training_editor", this.element).get(0)
    );
    var peerAssessmentView = new OpenAssessment.EditPeerAssessmentView(
        $("#oa_peer_assessment_editor", this.element).get(0)
    );
    var selfAssessmentView = new OpenAssessment.EditSelfAssessmentView(
        $("#oa_self_assessment_editor", this.element).get(0)
    );
    var exampleBasedAssessmentView = new OpenAssessment.EditExampleBasedAssessmentView(
        $("#oa_ai_assessment_editor", this.element).get(0)
    );
    var assessmentLookupDictionary = {};
    assessmentLookupDictionary[studentTrainingView.getID()] = studentTrainingView;
    assessmentLookupDictionary[peerAssessmentView.getID()] = peerAssessmentView;
    assessmentLookupDictionary[selfAssessmentView.getID()] = selfAssessmentView;
    assessmentLookupDictionary[exampleBasedAssessmentView.getID()] = exampleBasedAssessmentView;

    this.settingsView = new OpenAssessment.EditSettingsView(
        $("#oa_basic_settings_editor", this.element).get(0), assessmentLookupDictionary
    );

    // Initialize the rubric tab view
    this.rubricView = new OpenAssessment.EditRubricView(
        $("#oa_rubric_editor_wrapper", this.element).get(0)
    );

    // Install the save and cancel buttons
    $(".openassessment_save_button", this.element).click($.proxy(this.save, this));
    $(".openassessment_cancel_button", this.element).click($.proxy(this.cancel, this));

    this.initializeSortableAssessments()
};

OpenAssessment.StudioView.prototype = {

    /**
    Adjusts the modal's height, position and padding to be larger for OA editing only (Does not impact other modals)
    **/
    fixModalHeight: function () {
        // Add the full height class to every element from the XBlock
        // to the modal window in Studio.
        $(this.element)
            .addClass('openassessment_full_height')
            .parentsUntil('.modal-window')
            .addClass('openassessment_full_height');

        // Add the modal window class to the modal window
        $(this.element)
            .closest('.modal-window')
            .addClass('openassessment_modal_window');
    },

    /**
    Installs click listeners which initialize drag and drop functionality for assessment modules.
    **/
    initializeSortableAssessments: function () {
        var view = this;
        // Initialize Drag and Drop of Assessment Modules
        $('#openassessment_assessment_module_settings_editors', view.element).sortable({
            // On Start, we want to collapse all draggable items so that dragging is visually simple (no scrolling)
            start: function(event, ui) {
                // Hide all of the contents (not the headers) of the divs, to collapse during dragging.
                $('.openassessment_assessment_module_editor', view.element).hide();

                // Because of the way that JQuery actively resizes elements during dragging (directly setting
                // the style property), the only way to over come it is to use an important tag ( :( ), or
                // to tell JQuery to set the height to be Automatic (i.e. resize to the minimum nescesary size.)
                // Because all of the information we don't want displayed is now hidden, an auto height will
                // perform the apparent "collapse" that we are looking for in the Placeholder and Helper.
                var targetHeight = 'auto';
                // Shrink the blank area behind the dragged item.
                ui.placeholder.height(targetHeight);
                // Shrink the dragged item itself.
                ui.helper.height(targetHeight);
                // Update the sortable to reflect these changes.
                $('#openassessment_assessment_module_settings_editors', view.element)
                    .sortable('refresh').sortable('refreshPositions');
            },
            // On stop, we redisplay the divs to their original state
            stop: function(event, ui){
                $('.openassessment_assessment_module_editor', view.element).show();
            },
            snap: true,
            axis: "y",
            handle: ".drag-handle",
            cursorAt: {top: 20}
        });
        $('#openassessment_assessment_module_settings_editors', view.element).disableSelection();
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
