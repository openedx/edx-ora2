/**
 Interface for editing view in Studio.
 The constructor initializes the DOM for editing.

 Args:
 runtime (Runtime): an XBlock runtime instance.
 element (DOM element): The DOM element representing this XBlock.
 server (OpenAssessment.Server): The interface to the XBlock server.
 data (Object literal): The data object passed from XBlock backend.

 Returns:
 OpenAssessment.StudioView
 **/

OpenAssessment.StudioView = function(runtime, element, server, data) {
    this.element = element;
    this.runtime = runtime;
    this.server = server;
    this.data = data;

    // Resize the editing modal
    this.fixModalHeight();

    // Initializes the tabbing functionality and activates the last used.
    this.initializeTabs();

    // Initialize the validation alert
    this.alert = new OpenAssessment.ValidationAlert().install();

    var studentTrainingListener = new OpenAssessment.StudentTrainingListener();

    // Initialize the prompt tab view
    this.promptsView = new OpenAssessment.EditPromptsView(
        $("#oa_prompts_editor_wrapper", this.element).get(0),
        new OpenAssessment.Notifier([
            studentTrainingListener
        ])
    );

    // Initialize the settings tab view
    var staffAssessmentView = new OpenAssessment.EditStaffAssessmentView(
        $("#oa_staff_assessment_editor", this.element).get(0)
    );
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
    assessmentLookupDictionary[staffAssessmentView.getID()] = staffAssessmentView;
    assessmentLookupDictionary[studentTrainingView.getID()] = studentTrainingView;
    assessmentLookupDictionary[peerAssessmentView.getID()] = peerAssessmentView;
    assessmentLookupDictionary[selfAssessmentView.getID()] = selfAssessmentView;
    assessmentLookupDictionary[exampleBasedAssessmentView.getID()] = exampleBasedAssessmentView;

    this.settingsView = new OpenAssessment.EditSettingsView(
        $("#oa_basic_settings_editor", this.element).get(0), assessmentLookupDictionary, data
    );

    // Initialize the rubric tab view
    this.rubricView = new OpenAssessment.EditRubricView(
        $("#oa_rubric_editor_wrapper", this.element).get(0),
        new OpenAssessment.Notifier([
            studentTrainingListener
        ])
    );

    // Install the save and cancel buttons
    $(".openassessment_save_button", this.element).click($.proxy(this.save, this));
    $(".openassessment_cancel_button", this.element).click($.proxy(this.cancel, this));
};

OpenAssessment.StudioView.prototype = {

    /**
     Adjusts the modal's height, position and padding to be larger for OA editing only (Does not impact other modals)
     **/
    fixModalHeight: function() {
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
     Initializes the tabs that seperate the sections of the editor.

     Because this function relies on the OpenAssessment Name space, the tab that it first
     active will be the one that the USER was presented with, regardless of which editor they
     were using.  I.E.  If I leave Editor A in the settings state, and enter editor B, editor B
     will automatically open with the settings state.

     **/
    initializeTabs: function() {
        // If this is the first editor that the user has opened, default to the prompt view.
        if (typeof(OpenAssessment.lastOpenEditingTab) === "undefined") {
            OpenAssessment.lastOpenEditingTab = 2;
        }
        // Initialize JQuery UI Tabs, and activates the appropriate tab.
        $(".openassessment_editor_content_and_tabs", this.element)
            .tabs({
                active: OpenAssessment.lastOpenEditingTab
            });
    },

    /**
     Saves the state of the editing tabs in a variable outside of the scope of the editor.
     When the user reopens the editing view, they will be greeted by the same tab that they left.
     This code is called by the two paths that we could exit the modal through: Saving and canceling.
     **/
    saveTabState: function() {
        var tabElement = $(".openassessment_editor_content_and_tabs", this.element);
        OpenAssessment.lastOpenEditingTab = tabElement.tabs('option', 'active');
    },

    /**
     Save the problem's XML definition to the server.
     If the problem has been released, make the user confirm the save.
     **/
    save: function() {
        var view = this;
        this.saveTabState();

        // Perform client-side validation:
        // * Clear errors from any field marked as invalid.
        // * Mark invalid fields in the UI.
        // * If there are any validation errors, show an alert.
        //
        // The `validate()` method calls `validate()` on any subviews,
        // so that each subview has the opportunity to validate
        // its fields.
        this.clearValidationErrors();
        if (!this.validate()) {
            this.alert.setMessage(
                gettext("Couldn't Save This Assignment"),
                gettext("Please correct the outlined fields.")
            ).show();
        }
        else {
            // At this point, we know that all fields are valid,
            // so we can dismiss the validation alert.
            this.alert.hide();

            // Check whether the problem has been released; if not,
            // warn the user and allow them to cancel.
            this.server.checkReleased().done(
                function(isReleased) {
                    if (isReleased) {
                        view.confirmPostReleaseUpdate($.proxy(view.updateEditorContext, view));
                    }
                    else {
                        view.updateEditorContext();
                    }
                }
            ).fail(function(errMsg) {
                view.showError(errMsg);
            });
        }
    },

    /**
     Make the user confirm that he/she wants to update a problem
     that has already been released.

     Args:
     onConfirm (function): A function that accepts no arguments,
     executed if the user confirms the update.
     **/
    confirmPostReleaseUpdate: function(onConfirm) {
        var msg = gettext("This problem has already been released. Any changes will apply only to future assessments.");
        // TODO: classier confirm dialog
        if (confirm(msg)) { onConfirm(); }
    },

    /**
     Save the updated problem definition to the server.
     **/
    updateEditorContext: function() {
        // Notify the client-side runtime that we are starting
        // to save so it can show the "Saving..." notification
        this.runtime.notify('save', {state: 'start'});

        var view = this;
        this.server.updateEditorContext({
            prompts: view.promptsView.promptsDefinition(),
            feedbackPrompt: view.rubricView.feedbackPrompt(),
            feedback_default_text: view.rubricView.feedback_default_text(),
            criteria: view.rubricView.criteriaDefinition(),
            title: view.settingsView.displayName(),
            submissionStart: view.settingsView.submissionStart(),
            submissionDue: view.settingsView.submissionDue(),
            assessments: view.settingsView.assessmentsDescription(),
            fileUploadType: view.settingsView.fileUploadType(),
            fileTypeWhiteList: view.settingsView.fileTypeWhiteList(),
            latexEnabled: view.settingsView.latexEnabled(),
            leaderboardNum: view.settingsView.leaderboardNum(),
            editorAssessmentsOrder: view.settingsView.editorAssessmentsOrder()
        }).done(
            // Notify the client-side runtime that we finished saving
            // so it can hide the "Saving..." notification.
            // Then reload the view.
            function() { view.runtime.notify('save', {state: 'end'}); }
        ).fail(
            function(msg) { view.showError(msg); }
        );
    },

    /**
     Cancel editing.
     **/
    cancel: function() {
        // Notify the client-side runtime so it will close the editing modal
        this.saveTabState();
        this.runtime.notify('cancel', {});
    },

    /**
     Display an error message to the user.

     Args:
     errorMsg (string): The error message to display.
     **/
    showError: function(errorMsg) {
        this.runtime.notify('error', {msg: errorMsg});
    },

    /**
     Mark validation errors.

     Returns:
     Boolean indicating whether the view is valid.

     **/
    validate: function() {
        var settingsValid = this.settingsView.validate();
        var rubricValid = this.rubricView.validate();
        var promptsValid = this.promptsView.validate();
        return settingsValid && rubricValid && promptsValid;
    },

    /**
     Return a list of validation errors visible in the UI.
     Mainly useful for testing.

     Returns:
     list of string

     **/
    validationErrors: function() {
        return this.settingsView.validationErrors().concat(
            this.rubricView.validationErrors().concat(
                this.promptsView.validationErrors()
            )
        );
    },

    /**
     Clear all validation errors from the UI.
     **/
    clearValidationErrors: function() {
        this.settingsView.clearValidationErrors();
        this.rubricView.clearValidationErrors();
        this.promptsView.clearValidationErrors();
    }
};

/* XBlock entry point for Studio view */
/* jshint unused:false */
function OpenAssessmentEditor(runtime, element, data) {

    /**
     Initialize the editing interface on page load.
     **/
    var server = new OpenAssessment.Server(runtime, element);
    new OpenAssessment.StudioView(runtime, element, server, data);
}
