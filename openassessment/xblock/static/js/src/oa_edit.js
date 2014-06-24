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

    // Caputres the HTML definition of the original criterion element. This will be the template
    // used for all other criterion creations
    var criterionBodyHtml = $("#openassessment_criterion_1", liveElement).html();
    // Adds the wrapping LI tag which is not captured by the find element.
    var criterionHtml = '<li class="openassessment_criterion" id="openassessment_criterion_1">'
        + criterionBodyHtml + '</li>';
    // Replaces all instances of the original ID (1) with the new fake ID in the string
    // representation of the Criterion LI. This is our new template, with a C-C-C marker to replace.
    this.criterionHtmlTemplate = criterionHtml.replace(new RegExp("1", "g"), "C-C-C");

    // Captures the HTML definition of the original option element.  Note that there are TWO template
    // tags that need to be replaced "C-C-C" for the Criterion ID, and "O-O-O" for the option ID.
    var optionBodyHtml = $("#openassessment_criterion_1_option_1", liveElement).html();
    var optionHtml = '<li id=openassessment_criterion_1_option_1 class="openassessment_criterion_option">' +
        optionBodyHtml + '</li>';
    var criterionsReplaced = optionHtml.replace(new RegExp("criterion_1", "g"), "criterion_C-C-C");
    this.optionHtmlTemplate = criterionsReplaced.replace(new RegExp("option_1", "g"), "option_O-O-O");

    // Start us off with an empty setup, and uses the adding method to add a critera (which in turn will
    // add an option.  This design choice was made to ensure consistent practices in adding and removing,
    // the logic of which is all maintained in the function call.
    this.numberOfCriteria = 0;
    this.numberOfOptions = [];
    this.rubricCriteriaSelectors = [];

    $('#openassessment_criterion_list', liveElement).empty();
    this.addNewCriterionToRubric(liveElement);

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

    $('#openassessment_rubric_add_criterion', liveElement).click(
        function (eventData) {
            view.addNewCriterionToRubric(liveElement);
        }
    );

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
        if (confirm(msg)) {
            onConfirm();
        }
    },

    /**
     Initializes a new criterion for the rubric. Has multiple elements. This block of code dictates
     the methodology that we add and remove rubric criteria
     */
    addNewCriterionToRubric: function (liveElement){
        var view = this;

        // Always appends the new criterion to the end of the list, and we force linear ordering.
        var newCriterionID = this.numberOfCriteria + 1;
        this.numberOfCriteria += 1;
        this.numberOfOptions[newCriterionID] = 0;

        // Fills in the template with the new criterion ID
        var criterionHtml = this.criterionHtmlTemplate.replace(new RegExp('C-C-C', 'g'), '' + newCriterionID);

        // Adds the new criterion to the DOM
        $("#openassessment_criterion_list", liveElement).append(criterionHtml);

        // Now that we have altered our LiveElement, we need to "reset" it so that it recognizes the new criterion.
        liveElement = $("#openassessment_criterion_" + newCriterionID);
        $(".openassessment_criterion_option_list", liveElement).empty();

        // Adds our selector elements for easy future access.
        view.rubricCriteriaSelectors[newCriterionID] = {
            criterion: liveElement,
            name: $('.openassessment_criterion_name', liveElement).first(),
            prompt: $('.openassessment_criterion_prompt', liveElement).first(),
            options: [],
            feedback: $('.openassessment_criterion_feedbac', liveElement).first()
        };

        view.addNewOptionToCriterion(liveElement, newCriterionID);

        // Adds a listener that will collapse/expand the criterion on click.
        $('#openassessment_display_criterion_' + newCriterionID, liveElement) .change( function () {
            if (this.checked){
                $('#openassessment_criterion_body_' + newCriterionID, liveElement).fadeIn();
            } else {
                $('#openassessment_criterion_body_' + newCriterionID, liveElement).fadeOut();
            }
        });

        // Adds a listener which will delete the criterion on a click of the remove button
        // The methodology for deletion is to shift all information from previous elements down into
        $("#openassessment_criterion_" + newCriterionID + "_remove", liveElement) .click( function(eventData) {
            var numCriteria = view.numberOfCriteria;
            var selectors = view.rubricCriteriaSelectors;

            // shifts all data from "higher up" criterions down one in order to allow us to delete the last
            // element without deleting information input by the user
            for (var i = newCriterionID; i < numCriteria; i++){
                selectors[i].name.prop('value', selectors[i+1].name.prop('value'));
                selectors[i].prompt.prop('value', selectors[i+1].prompt.prop('value'));
                selectors[i].feedback.prop('value', selectors[i+1].feedback.prop('value'));
                var options1 = selectors[i].options;
                var options2 = selectors[i].options;
                var numOptions = view.numberOfOptions[i+1];
                for (var j = 1; j < numOptions; j++){
                    options1[j].points.prop('value', options2[j].points.prop('value'));
                    options1[j].name.prop('value', options2[j].name.prop('value'));
                    options1[j].explanation.prop('value', options2[j].explanation.prop('value'));
                }
            }

            // Physically removes the rubric criteria from the DOM
            view.rubricCriteriaSelectors[view.rubricCriteriaSelectors.length].criterion.remove();

            // Deletes the criteria from our three tracking statistics/structures
            view.rubricCriteriaSelectors = view.rubricCriteriaSelectors.slice(0,numCriteria);
            view.numberOfOptions = view.numberOfOptions.slice(0, numCriteria);
            view.numberOfCriteria -= 1;



        });

        // Adds a listener which will add another option to the Criterion's definition.
        $("#openassessment_criterion_" + newCriterionID + "_add_option", liveElement).click( function(eventData){
            view.addNewOptionToCriterion(liveElement, newCriterionID);
        });

        // Adds a listener which removes criterion feedback
        $(".openassessment_feedback_remove_button", liveElement). click( function(eventData){
            $(".openassessment_criterion_feedback_direction", liveElement).fadeOut();
            $(".openassessment_criterion_feedback_header_open", liveElement).fadeOut();
            $(".openassessment_criterion_feedback_header_closed", liveElement).fadeIn();
            $(".openassessment_feedback_remove_button", liveElement).fadeOut();
        });

        // Adds a listener which adds criterion feedback if not already displayed.
        $(".openassessment_criterion_feedback_header_closed", liveElement).click( function (eventData){
            $(".openassessment_criterion_feedback_direction", liveElement).fadeIn();
            $(".openassessment_criterion_feedback_header_open", liveElement).fadeIn();
            $(".openassessment_criterion_feedback_header_closed", liveElement).fadeOut();
            $(".openassessment_feedback_remove_button", liveElement).fadeIn();
        });

        // Hides the criterion header used for adding
        $(".openassessment_criterion_feedback_header_closed", liveElement).hide();

    },

    /**
     * Initializes a new option for a given criterion.  This code block dictates the methodology for
     * adding and removing options to a rubric.
     * @param liveElement A selector representing the current state of the Criterion DOM
     * @param criterionID The specific number of the criterion the option is being added to
     */
    addNewOptionToCriterion: function (liveElement, criterionID){
        var view = this;

        // Finds the ID that will be associated with the option (it will be added to the end)
        var newOptionID = this.numberOfOptions[criterionID] + 1;

        this.numberOfOptions[criterionID] += 1;

        // Replaces the template values with the true criterion and option ID's, and appends it on to the DOM
        var optionHtml = this.optionHtmlTemplate;
        optionHtml = optionHtml.replace(new RegExp("C-C-C", 'g'), "" + criterionID);
        optionHtml = optionHtml.replace(new RegExp("O-O-O", 'g'), "" + newOptionID);
        $("#openassessment_criterion_" + criterionID + "_options", liveElement).append(optionHtml);

        // Resets the Live Element to be the updated (and newly created) option.
        liveElement = $("#openassessment_criterion_" + criterionID + "_option_" + newOptionID);

        // Constructs and assigns a dictionary of all of the selectors we store for each option.
        view.rubricCriteriaSelectors[criterionID].options[newOptionID] = {
            option: liveElement,
            points: $("#openassessment_criterion_" + criterionID + "_option_" + newOptionID + "_points", liveElement),
            name: $("#openassessment_criterion_" + criterionID + "_option_" + newOptionID + "_name", liveElement),
            explanation: $("#openassessment_criterion_" + criterionID + "_option_" + newOptionID + "_explanation", liveElement)
        };

        // Sets the remove behavior. When deleted, an option will shift all of the data "behind" it on the list
        // of options toward itself, and then deletes the last element in the list. This ensures that our options
        // are always increasing by one, and that the data doesn't remain tethered to where it was entered.
        $("#openassessment_criterion_" + criterionID + "_option_" + newOptionID + "_remove", liveElement).click(
            function(eventData){
                var numberOfOptions = view.numberOfOptions[criterionID];
                var optionSelectors = view.rubricCriteriaSelectors[criterionID].options;

                // Shifts all data down, then deletes the last element, to create the appearance we deleted the given
                // elements.
                for (var i = newOptionID; i < numberOfOptions; i++){
                    // Utilizes stored selectors to perform the swaps.
                    optionSelectors[i].points.prop('value', optionSelectors[i+1].points.prop('value'));
                    optionSelectors[i].name.prop('value', optionSelectors[i+1].name.prop('value'));
                    optionSelectors[i].explanation.prop('value', optionSelectors[i+1].explanation.prop('value'));
                }

                optionSelectors[optionSelectors.length - 1].option.remove();
                view.rubricCriteriaSelectors[criterionID].options =
                    view.rubricCriteriaSelectors[criterionID].options.slice(0, (optionSelectors.length - 1));

                view.numberOfOptions[criterionID] -= 1;
            }
        )
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
