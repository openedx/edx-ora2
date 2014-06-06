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

    // Initialize the code box

    this.promptBox = $('.openassessment-prompt-editor').first().get(0);

    this.rubricXmlBox = CodeMirror.fromTextArea(
        $(element).find('.openassessment-rubric-editor').first().get(0),
        {mode: "xml", lineNumbers: true, lineWrapping: true}
    );

    this.titleField = $(element).find('.openassessment-title-editor');

    this.submissionStartField = $(element).find('.openassessment-submission-start-editor').first().get(0);

    this.submissionDueField = $(element).find('.openassessment-submission-due-editor').first().get(0);

    this.assessmentsXmlBox = CodeMirror.fromTextArea(
        $(element).find('.openassessment-assessments-editor').first().get(0),
        {mode: "xml", lineNumbers: true, lineWrapping: true}
    );

    // Install click handlers
    var view = this;
    $(element).find('.openassessment-save-button').click(
        function (eventData) {
            view.save();
        });

    $(element).find('.openassessment-cancel-button').click(
        function (eventData) {
            view.cancel();
        });

    $('.openassessment-editor-content-and-tabs').tabs();
};

OpenAssessment.StudioView.prototype = {

    /**
     Load the XBlock XML definition from the server and display it in the view.
     **/
    load: function () {
        var view = this;
        this.server.loadXml().done(
            function (prompt, rubricXml, settings) {
                view.rubricXmlBox.setValue(rubricXml);
                view.assessmentsXmlBox.setValue(settings.assessments);
                view.submissionStartField.value = settings.submission_start;
                view.submissionDueField.value = settings.submission_due;
                view.promptBox.value = prompt;
                view.titleField.value = settings.title;
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
                    view.confirmPostReleaseUpdate($.proxy(view.updateXml, view));
                }
                else {
                    view.updateXml();
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
    updateXml: function () {
        // Notify the client-side runtime that we are starting
        // to save so it can show the "Saving..." notification
        this.runtime.notify('save', {state: 'start'});

        // Send the updated XML to the server
        var prompt = this.promptBox.value;
        var rubricXml = this.rubricXmlBox.getValue();
        var title = this.titleField.value;
        var sub_start = this.submissionStartField.value;
        var sub_due = this.submissionDueField.value;
        var assessmentsXml = this.assessmentsXmlBox.getValue();

        var view = this;
        this.server.updateXml(prompt, rubricXml, title, sub_start, sub_due, assessmentsXml).done(function () {
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
    $(function ($) {
        var server = new OpenAssessment.Server(runtime, element);
        var view = new OpenAssessment.StudioView(runtime, element, server);
        view.load();
    });
};