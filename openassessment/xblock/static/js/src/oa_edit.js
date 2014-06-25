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

    this.liveElement = $(element);
    
    var liveElement = this.liveElement;

    // Instantiates JQuery selector variables which will allow manipulation and display controls.
    this.settingsFieldSelectors = {
        promptBox: $('#openassessment_prompt_editor', liveElement),
        titleField: $('#openassessment_title_editor', liveElement),
        submissionStartField: $('#openassessment_submission_start_editor', liveElement),
        submissionDueField: $('#openassessment_submission_due_editor', liveElement),
        hasPeer: $('#include_peer_assessment', liveElement),
        hasSelf: $('#include_self_assessment', liveElement),
        hasAI: $('#include_ai_assessment', liveElement),
        hasTraining: $('#include_student_training', liveElement),
        peerMustGrade: $('#peer_assessment_must_grade', liveElement),
        peerGradedBy: $('#peer_assessment_graded_by', liveElement),
        peerStart: $('#peer_assessment_start_date', liveElement),
        peerDue: $('#peer_assessment_due_date', liveElement),
        selfStart: $('#self_assessment_start_date', liveElement),
        selfDue: $('#self_assessment_due_date', liveElement)
    };

    this.aiTrainingExamplesCodeBox = CodeMirror.fromTextArea(
        $('#ai_training_examples', liveElement).first().get(0),
        {mode: "xml", lineNumbers: true, lineWrapping: true}
    );

    this.studentTrainingExamplesCodeBox = CodeMirror.fromTextArea(
        $('#student_training_examples', liveElement).first().get(0),
        {mode: "xml", lineNumbers: true, lineWrapping: true}
    );

    // Captures the HTML definition of the original criterion element. This will be the template
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
    var criteriaReplaced = optionHtml.replace(new RegExp("criterion_1", "g"), "criterion_C-C-C");
    this.optionHtmlTemplate = criteriaReplaced.replace(new RegExp("option_1", "g"), "option_O-O-O");

    // Start us off with an empty setup, and uses the adding method to add a criteria (which in turn will
    // add an option).  This design choice was made to ensure consistent practices in adding and removing,
    // the logic of which is all maintained in the function calls.
    this.numberOfCriteria = 0;
    this.numberOfOptions = [];
    this.rubricCriteriaSelectors = [];
    this.rubricFeedbackPrompt =  $('#openassessment_rubric_feedback', liveElement);
    this.hasRubricFeedbackPrompt = true;
    $('#openassessment_criterion_list', liveElement).empty();
    this.addNewCriterionToRubric();

    var view = this;

    // Installs the save and cancel buttons
    $('.openassessment_save_button', liveElement) .click( function (eventData) {
            view.save();
    });

    $('.openassessment_cancel_button', liveElement) .click( function (eventData) {
            view.cancel();
    });

    // Adds the tabbing functionality
    $('.openassessment_editor_content_and_tabs', liveElement) .tabs();

    // Installs all of the checkbox listeners in the settings tab
    view.addSettingsAssessmentCheckboxListener("ai_assessment", liveElement);
    view.addSettingsAssessmentCheckboxListener("self_assessment", liveElement);
    view.addSettingsAssessmentCheckboxListener("peer_assessment", liveElement);
    view.addSettingsAssessmentCheckboxListener("student_training", liveElement);

    $('#openassessment_rubric_add_criterion', liveElement) .click( function (eventData) {
            view.addNewCriterionToRubric(liveElement);
    });

    // Adds a listener which removes rubric feedback
    $("#openassessment_rubric_feedback_remove", liveElement). click( function(eventData){
        $("#openassessment_rubric_feedback_header_open", liveElement).fadeOut();
        $("#openassessment_rubric_feedback_input_wrapper", liveElement).fadeOut();
        $("#openassessment_rubric_feedback_header_closed", liveElement).fadeIn();
        view.hasRubricFeedbackPrompt = false;
    });

    // Adds a listener which adds rubric feedback if not already displayed.
    $("#openassessment_rubric_feedback_header_closed", liveElement). click( function(eventData){
        $("#openassessment_rubric_feedback_header_closed", liveElement).fadeOut();
        $("#openassessment_rubric_feedback_header_open", liveElement).fadeIn();
        $("#openassessment_rubric_feedback_input_wrapper", liveElement).fadeIn();
        view.hasRubricFeedbackPrompt = true;
    });

    // Initially Hides the rubric "add rubric feedback" div
    $("#openassessment_rubric_feedback_header_closed", liveElement).hide();

};

OpenAssessment.StudioView.prototype = {

    /**
     Load the XBlock XML definition from the server and display it in the view.
     **/
    load: function () {
        var view = this;
        this.server.loadEditorContext().done(
            function (prompt, rubric, title, subStart, subDue, assessments) {
                view.settingsFieldSelectors.submissionStartField.prop('value', subStart);
                view.settingsFieldSelectors.submissionDueField.prop('value', subDue);
                view.settingsFieldSelectors.promptBox.prop('value', prompt);
                view.settingsFieldSelectors.titleField.prop('value', title);
                view.settingsFieldSelectors.hasTraining.prop('checked', false).change();
                view.settingsFieldSelectors.hasPeer.prop('checked', false).change();
                view.settingsFieldSelectors.hasSelf.prop('checked', false).change();
                view.settingsFieldSelectors.hasAI.prop('checked', false).change();
                for (var i = 0; i < assessments.length; i++) {
                    var assessment = assessments[i];
                    if (assessment.name == 'peer-assessment') {
                        view.settingsFieldSelectors.peerMustGrade.prop('value', assessment.must_grade);
                        view.settingsFieldSelectors.peerGradedBy.prop('value', assessment.must_be_graded_by);
                        view.settingsFieldSelectors.peerStart.prop('value', assessment.start);
                        view.settingsFieldSelectors.peerDue.prop('value', assessment.due);
                        view.settingsFieldSelectors.hasPeer.prop('checked', true).change();
                    } else if (assessment.name == 'self-assessment') {
                        view.settingsFieldSelectors.selfStart.prop('value', assessment.start);
                        view.settingsFieldSelectors.selfDue.prop('value', assessment.due);
                        view.settingsFieldSelectors.hasSelf.prop('checked', true).change();
                    } else if (assessment.name == 'example-based-assessment') {
                        view.settingsFieldSelectors.aiTrainingExamplesCodeBox.setValue(assessment.examples);
                        view.settingsFieldSelectors.hasAI.prop('checked', true).change();
                    } else if (assessment.name == 'student-training') {
                        view.studentTrainingExamplesCodeBox.setValue(assessment.examples);
                        view.settingsFieldSelectors.hasTraining.prop('checked', true).change();
                    }
                }

                // Corrects the length of the number of criteria
                while(view.numberOfCriteria < rubric.criteria.length){
                    view.addNewCriterionToRubric();
                }
                while(view.numberOfCriteria > rubric.criteria.length){
                    view.removeCriterionFromRubric(1)
                }

                // Corrects the number of options in each criterion
                for (i = 0; i < rubric.criteria.length; i++){
                    while(view.numberOfOptions[i+1] < rubric.criteria[i].options.length){
                        view.addNewOptionToCriterion(view.liveElement, i+1);
                    }
                    while(view.numberOfOptions[i+1] > rubric.criteria[i].options.length){
                        view.removeOptionFromCriterion(view.liveElement, i+1, 1);
                    }
                }

                // Inserts the data from the rubric into the GUI's fields
                for (i = 0; i < rubric.criteria.length; i++){
                    var criterion = rubric.criteria[i];
                    var selectors = view.rubricCriteriaSelectors[i+1];
                    // Transfers the Criteria Fields
                    selectors.name.prop('value', criterion.name);
                    selectors.prompt.prop('value', criterion.prompt);
                    selectors.feedback = criterion.feedback;
                    for (var j = 0; j < criterion.options.length; j++){
                        var option = criterion.options[j];
                        var optionSelectors = selectors.options[j+1];
                        // Transfers all of the option data.
                        optionSelectors.name.prop('value', option.name);
                        optionSelectors.points.prop('value', option.points);
                        optionSelectors.explanation.prop('value', option.explanation);
                    }
                }

                if (rubric.feedbackprompt){
                    view.rubricFeedbackPrompt.prop('value', rubric.feedbackprompt);
                    view.hasRubricFeedbackPrompt = true;
                } else {
                    view.rubricFeedbackPrompt.prop('value', "");
                    view.hasRubricFeedbackPrompt = false;
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
     * A simple helper method which constructs checkbox listeners for all of our assessment modules
     * @param name name of assessment module to install listener on
     * @param liveElement the live DOM selector
     */
    addSettingsAssessmentCheckboxListener: function (name, liveElement) {
        $("#include_" + name , liveElement) .change(function () {
            if (this.checked){
                $("#" + name + "_description_closed", liveElement).fadeOut('fast');
                $("#" + name + "_settings_editor", liveElement).fadeIn();
            } else {
                $("#" + name + "_settings_editor", liveElement).fadeOut('fast');
                $("#" + name + "_description_closed", liveElement).fadeIn();
            }
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
    addNewCriterionToRubric: function (){
        var view = this;
        var liveElement = this.liveElement;
        
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
            feedback: 'disabled'
        };

        // Defaults to no feedback
        $('input:radio[value=disabled]', liveElement).prop('checked', true);

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
        $("#openassessment_criterion_" + newCriterionID + "_remove", liveElement) .click( function (eventData) {
            view.removeCriterionFromRubric(newCriterionID);
        });

        // Adds a listener which will add another option to the Criterion's definition.
        $("#openassessment_criterion_" + newCriterionID + "_add_option", liveElement).click( function (eventData) {
            view.addNewOptionToCriterion(liveElement, newCriterionID);
        });

        // Adds a listener which removes criterion feedback
        $(".openassessment_feedback_remove_button", liveElement). click( function(eventData){
            $(".openassessment_criterion_feedback_direction", liveElement).fadeOut();
            $(".openassessment_criterion_feedback_header_open", liveElement).fadeOut();
            $(".openassessment_criterion_feedback_header_closed", liveElement).fadeIn();
            $(".openassessment_feedback_remove_button", liveElement).fadeOut();
            view.rubricCriteriaSelectors[newCriterionID].hasFeedback = false;
        });

        // Adds a listener which adds criterion feedback if not already displayed.
        $(".openassessment_criterion_feedback_header_closed", liveElement).click( function (eventData){
            $(".openassessment_criterion_feedback_direction", liveElement).fadeIn();
            $(".openassessment_criterion_feedback_header_open", liveElement).fadeIn();
            $(".openassessment_criterion_feedback_header_closed", liveElement).fadeOut();
            $(".openassessment_feedback_remove_button", liveElement).fadeIn();
            view.rubricCriteriaSelectors[newCriterionID].hasFeedback = true;
        });

        // Hides the criterion header used for adding
        $(".openassessment_criterion_feedback_header_closed", liveElement).hide();

    },

    /**
     * Removes a specified criterion from the problem's rubric definition. Changes are made in the DOM,
     * in support/control structures.
     * @param criterionToRemove
     */
    removeCriterionFromRubric: function(criterionToRemove){
        var view = this;
        var numCriteria = view.numberOfCriteria;
        var selectors = view.rubricCriteriaSelectors;

        // Shifts all data from "higher up" criteria down one in order to allow us to delete the last
        // element without deleting information input by the user
        for (var i = criterionToRemove; i < numCriteria; i++){

            // Shifts all criterion field values
            selectors[i].name.prop('value', selectors[i+1].name.prop('value'));
            selectors[i].prompt.prop('value', selectors[i+1].prompt.prop('value'));
            selectors[i].feedback = selectors[i+1].feedback;
            $('input:radio[value="disabled"]', selectors[i].criterion).prop('checked', true);

            // Ensures that we won't delete information during the shift by ensuring that the option lists are of the
            //same length. Note it doesn't matter what we add or delete, simply that the lengths add up.
            while (view.numberOfOptions[i] < view.numberOfOptions[i+1]){
                view.addNewOptionToCriterion(selectors[i].criteria, i);
            }
            while (view.numberOfOptions[i] > view.numberOfOptions[i+1]){
                view.removeOptionFromCriterion(selectors[i].criteria, i, 1);
            }

            // Transfers all data from each option to the next within a criterion.
            var options1 = selectors[i].options;
            var options2 = selectors[i+1].options;

            var numOptions2 = view.numberOfOptions[i+1];
            for (var j = 1; j < numOptions2; j++){
                options1[j].points.prop('value', options2[j].points.prop('value'));
                options1[j].name.prop('value', options2[j].name.prop('value'));
                options1[j].explanation.prop('value', options2[j].explanation.prop('value'));
            }
        }

        // Physically removes the rubric criteria from the DOM
        view.rubricCriteriaSelectors[view.rubricCriteriaSelectors.length - 1].criterion.remove();

        // Deletes the criteria from our three tracking statistics/structures
        view.rubricCriteriaSelectors = view.rubricCriteriaSelectors.slice(0,numCriteria);
        view.numberOfOptions = view.numberOfOptions.slice(0, numCriteria);
        view.numberOfCriteria -= 1;
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
                view.removeOptionFromCriterion(liveElement, criterionID, newOptionID);
            }
        )
    },

    /**
     * Removes a specified element from the DOM and from all tracking data. Note that no action is
     * taken against the specified element, rather, data is shifted down the chain (to construct the
     * illusion that the specified element was deleted), and then the last element is actually deleted.
     * @param liveElement A selector for the criterion that we are deleting from
     * @param criterionID The criterion ID that we are deleting from
     * @param optionToRemove The option ID (discriminator really) that we are "deleting"
     */
    removeOptionFromCriterion: function(liveElement, criterionID, optionToRemove){
        var view = this;
        var numberOfOptions = view.numberOfOptions[criterionID];
        var optionSelectors = view.rubricCriteriaSelectors[criterionID].options;

        // Shifts all data down, then deletes the last element, to create the appearance we deleted the given
        // elements.
        for (var i = optionToRemove; i < numberOfOptions; i++){
            // Utilizes stored selectors to perform the swaps.
            optionSelectors[i].points.prop('value', optionSelectors[i+1].points.prop('value'));
            optionSelectors[i].name.prop('value', optionSelectors[i+1].name.prop('value'));
            optionSelectors[i].explanation.prop('value', optionSelectors[i+1].explanation.prop('value'));
        }

        optionSelectors[optionSelectors.length - 1].option.remove();
        view.rubricCriteriaSelectors[criterionID].options =
            view.rubricCriteriaSelectors[criterionID].options.slice(0, (optionSelectors.length - 1));

        view.numberOfOptions[criterionID] -= 1;
    },

    /**
     Save the updated XML definition to the server.
     **/
    updateEditorContext: function () {
        // Notify the client-side runtime that we are starting
        // to save so it can show the "Saving..." notification
        this.runtime.notify('save', {state: 'start'});

        // Send the updated XML to the server
        var prompt = this.settingsFieldSelectors.promptBox.prop('value');
        var title = this.settingsFieldSelectors.titleField.prop('value');
        var subStart = this.settingsFieldSelectors.submissionStartField.prop('value');
        var subDue = this.settingsFieldSelectors.submissionDueField.prop('value');

        // Grabs values from all of our fields, and stores them in a format which can be easily validated.
        var rubricCriteria = [];

        for (var i = 1; i <= this.numberOfCriteria; i++){
            var selectorDict = this.rubricCriteriaSelectors[i];
            var criterionValueDict = {
                order_num: i - 1,
                name: selectorDict.name.prop('value'),
                prompt: selectorDict.prompt.prop('value'),
                feedback: $('input[name="criterion_'+ i +'_feedback"]:checked', selectorDict.criterion).val()
            };

            var optionSelectorList = selectorDict.options;
            var optionValueList = [];
            for (var j = 1; j <= this.numberOfOptions[i]; j++){
                var optionSelectors = optionSelectorList[j];
                optionValueList = optionValueList.concat([{
                    order_num: j-1,
                    points: optionSelectors.points.prop('value'),
                    name: optionSelectors.name.prop('value'),
                    explanation: optionSelectors.explanation.prop('value')
                }]);
            }
            criterionValueDict.options = optionValueList;
            rubricCriteria = rubricCriteria.concat([criterionValueDict]);
        }

        var rubric = { 'criteria': rubricCriteria };

        if (this.hasRubricFeedbackPrompt){
            rubric.feedbackprompt = this.rubricFeedbackPrompt.prop('value');
        }

        var assessments = [];

        if (this.settingsFieldSelectors.hasTraining.prop('checked')){
            assessments[assessments.length] = {
                "name": "student-training",
                "examples": this.studentTrainingExamplesCodeBox.getValue()
            };
        }

        if (this.settingsFieldSelectors.hasPeer.prop('checked')) {
            var assessment = {
                "name": "peer-assessment",
                "must_grade": parseInt(this.settingsFieldSelectors.peerMustGrade.prop('value')),
                "must_be_graded_by": parseInt(this.settingsFieldSelectors.peerGradedBy.prop('value'))
            };
            var startStr = this.settingsFieldSelectors.peerStart.prop('value');
            var dueStr = this.settingsFieldSelectors.peerDue.prop('value');
            if (startStr){
                assessment = $.extend(assessment, {"start": startStr})
            }
            if (dueStr){
                assessment = $.extend(assessment, {"due": dueStr})
            }
            assessments[assessments.length] = assessment;
        }

        if (this.settingsFieldSelectors.hasSelf.prop('checked')) {
            assessment = {
                "name": "self-assessment"
            };
            startStr = this.settingsFieldSelectors.selfStart.prop('value');
            dueStr = this.settingsFieldSelectors.selfDue.prop('value');
            if (startStr){
                assessment = $.extend(assessment, {"start": startStr})
            }
            if (dueStr){
                assessment = $.extend(assessment, {"due": dueStr})
            }
            assessments[assessments.length] = assessment;
        }

        if (this.settingsFieldSelectors.hasAI.prop('checked')) {
            assessments[assessments.length] = {
                "name": "example-based-assessment",
                "examples": this.aiTrainingExamplesCodeBox.getValue()
            };
        }

        var view = this;
        this.server.updateEditorContext(prompt, rubric, title, subStart, subDue, assessments).done(function () {
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
