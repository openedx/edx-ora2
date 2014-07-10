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

    this.fixModalHeight();

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

    // Captures the HTML definition of the original criterion element. This will be the template
    // used for all other criterion creations
    var criterionHtml = $("#openassessment_criterion_1", liveElement).parent().html();

    // Replaces all instances of the original ID (1) with the new fake ID in the string
    // representation of the Criterion LI. This is our new template, with a C-C-C marker to replace.
    this.criterionHtmlTemplate = criterionHtml.replace(new RegExp("1", "g"), "C-C-C");

    // Captures the HTML definition of the original option element.  Note that there are TWO template
    // tags that need to be replaced "C-C-C" for the Criterion ID, and "O-O-O" for the option ID.
    var optionHtml = $("#openassessment_criterion_1_option_1", liveElement).parent().html();
    var criteriaReplaced = optionHtml.replace(new RegExp("criterion_1", "g"), "criterion_C-C-C");
    this.optionHtmlTemplate = criteriaReplaced.replace(new RegExp("option_1", "g"), "option_O-O-O");

    // Start us off with an empty setup, and uses the adding method to add a criteria (which in turn will
    // add an option).  This design choice was made to ensure consistent practices in adding and removing,
    // the logic of which is all maintained in the function calls.
    this.numberOfCriteria = 0;
    this.numberOfOptions = [];
    this.rubricCriteriaSelectors = [];
    this.rubricFeedbackPrompt =  $('#openassessment_rubric_feedback', liveElement);
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

};

OpenAssessment.StudioView.prototype = {

    /**
     Adjusts the modal's height, position and padding to be larger for OA editing only (Does not impact other modals)
     */
    fixModalHeight: function () {
        var element = this.liveElement;
        element.toggleClass('openassessment_full_height');
        element.parentsUntil('.modal-window').toggleClass('openassessment_full_height');
        $('.modal-window').toggleClass('openassessment_modal_window');
    },

    /**
     Load the XBlock XML definition from the server and display it in the view.
     **/
    load: function () {
        var view = this;
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
    Construct checkbox listeners for all of our assessment modules

    Args:
        name (string): name of assessment module to install listener on
        liveElement (DOM element): the live DOM selector
    */
    addSettingsAssessmentCheckboxListener: function (name, liveElement) {
        $("#include_" + name , liveElement) .change(function () {
            $("#" + name + "_description_closed", liveElement).toggleClass('is--hidden', this.checked);
            $("#" + name + "_settings_editor", liveElement).toggleClass('is--hidden', !this.checked);
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
    Adds a new criterion to the rubric.
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
    Removes a specified criterion from the problem's rubric definition.
    Changes are made in the DOM, in support/control structures.
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
    Initializes a new option for a given criterion.  This code block dictates the methodology for
    adding and removing options to a rubric.

    Args:
        liveElement (DOM element): An element containing the criterion interface in the DOM.
        criterionID (string): The specific number of the criterion the option is being added to
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
        );
    },

    /**
    Removes a specified element from the DOM and from all tracking data. Note that no action is
    taken against the specified element, rather, data is shifted down the chain (to construct the
    illusion that the specified element was deleted), and then the last element is actually deleted.

    Args:
        liveElement (DOM element): An element containing the criterion interface in the DOM.
        criterionID (string): The criterion ID that we are deleting from
        optionToRemove (string): The option ID that we are "deleting"
    */
    removeOptionFromCriterion: function(liveElement, criterionID, optionToRemove) {
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

        // Grabs values from all of our fields, and stores them in a format which can be easily validated.
        var rubricCriteria = [];

        for (var i = 1; i <= this.numberOfCriteria; i++){
            var selectorDict = this.rubricCriteriaSelectors[i];
            var criterionValueDict = {
                order_num: i - 1,
                name: selectorDict.name.prop('value'),
                prompt: selectorDict.prompt.prop('value'),
                feedback: $("#openassessment_criterion_" + i + "_feedback").val()
            };

            var optionSelectorList = selectorDict.options;
            var optionValueList = [];
            for (var j = 1; j <= this.numberOfOptions[i]; j++){
                var optionSelectors = optionSelectorList[j];
                optionValueList = optionValueList.concat([{
                    order_num: j-1,
                    points: this._getInt(optionSelectors.points),
                    name: optionSelectors.name.val(),
                    explanation: optionSelectors.explanation.val()
                }]);
            }
            criterionValueDict.options = optionValueList;
            rubricCriteria = rubricCriteria.concat([criterionValueDict]);
        }

        var assessments = [];

        if (this.settingsFieldSelectors.hasTraining.prop('checked')){
            assessments.push({
                name: "student-training",
                examples: this.studentTrainingExamplesCodeBox.getValue()
            });
        }

        if (this.settingsFieldSelectors.hasPeer.prop('checked')) {
            assessments.push({
                name: "peer-assessment",
                must_grade: this._getInt(this.settingsFieldSelectors.peerMustGrade),
                must_be_graded_by: this._getInt(this.settingsFieldSelectors.peerGradedBy),
                start: this._getDateTime(this.settingsFieldSelectors.peerStart),
                due: this._getDateTime(this.settingsFieldSelectors.peerDue)
            });
        }

        if (this.settingsFieldSelectors.hasSelf.prop('checked')) {
            assessments.push({
                name: "self-assessment",
                start: this._getDateTime(this.settingsFieldSelectors.selfStart),
                due: this._getDateTime(this.settingsFieldSelectors.selfDue)
            });
        }

        if (this.settingsFieldSelectors.hasAI.prop('checked')) {
            assessments.push({
                name: "example-based-assessment",
                examples: this.aiTrainingExamplesCodeBox.getValue()
            });
        }

        var view = this;
        this.server.updateEditorContext({
            title: this.settingsFieldSelectors.titleField.val(),
            prompt: this.settingsFieldSelectors.promptBox.val(),
            feedbackPrompt: this.rubricFeedbackPrompt.val(),
            submissionStart: this._getDateTime(this.settingsFieldSelectors.submissionStartField),
            submissionDue: this._getDateTime(this.settingsFieldSelectors.submissionDueField),
            criteria: rubricCriteria,
            assessments: assessments
        }).done(
            function () {
                // Notify the client-side runtime that we finished saving
                // so it can hide the "Saving..." notification.
                // Then reload the view.
                view.runtime.notify('save', {state: 'end'});
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
    },

    /**
    Retrieve a value from a datetime input.

    Args:
        selector: The JQuery selector for the datetime input.

    Returns:
        ISO-formatted datetime string or null
    **/
    _getDateTime: function(selector) {
        var dateStr = selector.val();

        // By convention, empty date strings are null,
        // meaning choose the default date based on
        // other dates set in the problem configuration.
        if (dateStr === "") {
            return null;
        }

        // Attempt to parse the date string
        // TO DO: currently invalid dates also are set as null,
        // which is probably NOT what the user wants!
        // We should add proper validation here.
        var timestamp = Date.parse(dateStr);
        if (isNaN(timestamp)) {
            return null;
        }

        // Send the datetime in ISO format
        // This will also convert the timezone to UTC
        return new Date(timestamp).toISOString();
    },

    /**
    Retrieve an integer value from an input.

    Args:
        selector: The JQuery selector for the input.

    Returns:
        int

    **/
    _getInt: function(selector) {
        return parseInt(selector.val(), 10);
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
