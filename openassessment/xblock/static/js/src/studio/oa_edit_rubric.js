/**
 Interface for editing rubric definitions.

 Args:
 element (DOM element): The DOM element representing the rubric.
 notifier (OpenAssessment.Notifier): Used to notify other views about updates to the rubric.

 This view fires the following notification events:
 * optionAdd: An option was added to the rubric.
 * optionRemove: An option was removed from the rubric.
 * optionUpdated: An option's label and/or points were updated in the rubric.
 * criterionRemove: A criterion was removed from the rubric.
 * criterionUpdated: A criterion's label was updated in the rubric.

 **/
OpenAssessment.EditRubricView = function(element, notifier) {
    this.element = element;
    this.criterionAddButton = $('#openassessment_rubric_add_criterion', this.element);

    this.criteriaContainer = new OpenAssessment.Container(
        OpenAssessment.RubricCriterion, {
            containerElement: $("#openassessment_criterion_list", this.element).get(0),
            templateElement: $("#openassessment_criterion_template", this.element).get(0),
            addButtonElement: $("#openassessment_rubric_add_criterion", this.element).get(0),
            removeButtonClass: "openassessment_criterion_remove_button",
            containerItemClass: "openassessment_criterion",
            notifier: notifier
        }
    );
    this.criteriaContainer.addEventListeners();
};

OpenAssessment.EditRubricView.prototype = {
    /**
     Construct a list of criteria definitions from the editor UI.

     Returns:
     list of criteria objects

     Example usage:
     >>> editRubricView.criteriaDefinition();
     [
     {
         name: "Criterion",
         prompt: "Prompt",
         order_num: 0,
         feedback: "disabled",
         options: [
             {
                 order_num: 0,
                 points: 1,
                 name: "Good",
                 explanation: "Explanation"
             },
             ...
         ]
     },
     ...
     ]

     **/
    criteriaDefinition: function() {
        var criteria = this.criteriaContainer.getItemValues();

        // Add order_num fields for criteria and options
        for (var criterionIndex = 0; criterionIndex < criteria.length; criterionIndex++) {
            var criterion = criteria[criterionIndex];
            criterion.order_num = criterionIndex;
            for (var optionIndex = 0; optionIndex < criterion.options.length; optionIndex++) {
                var option = criterion.options[optionIndex];
                option.order_num = optionIndex;
            }
        }

        return criteria;
    },

    /**
     Get or set the feedback prompt in the editor.
     This is the prompt shown to students when giving "overall" feedback
     on a submission.

     Args:
     text (string, optional): If provided, set the feedback prompt to this value.

     Returns:
     string

     **/
    feedbackPrompt: function(text) {
        var sel = $("#openassessment_rubric_feedback", this.element);
        return OpenAssessment.Fields.stringField(sel, text);
    },

    /**
     Get or set the default feedback response text in the editor.
     The text is used as a student's default response to the feedback
     prompt.

     Args:
     text (string, option): If provided, sets the default text to this value.

     Returns:
     string

     **/
    feedback_default_text: function(text) {
        var sel = $("#openassessment_rubric_feedback_default_text", this.element);
        return OpenAssessment.Fields.stringField(sel, text);
    },

    /**
     Add a new criterion to the rubric.
     Uses a client-side template to create the new criterion.
     **/
    addCriterion: function() {
        this.criteriaContainer.add();
    },

    /**
     Remove a criterion from the rubric.

     Args:
     item (OpenAssessment.RubricCriterion): The criterion item to remove.
     **/
    removeCriterion: function(item) {
        this.criteriaContainer.remove(item);
    },

    /**
     Retrieve all criteria from the rubric.

     Returns:
     Array of OpenAssessment.RubricCriterion objects.

     **/
    getAllCriteria: function() {
        return this.criteriaContainer.getAllItems();
    },

    /**
     Retrieve a criterion item from the rubric.

     Args:
     index (int): The index of the criterion, starting from 0.

     Returns:
     OpenAssessment.RubricCriterion or null

     **/
    getCriterionItem: function(index) {
        return this.criteriaContainer.getItem(index);
    },

    /**
     Add a new option to the rubric.

     Args:
     criterionIndex (int): The index of the criterion to which
     the option will be added (starts from 0).

     **/
    addOption: function(criterionIndex) {
        var criterionItem = this.getCriterionItem(criterionIndex);
        criterionItem.optionContainer.add();
    },

    /**
     Remove an option from the rubric.

     Args:
     criterionIndex (int): The index of the criterion, starting from 0.
     item (OpenAssessment.RubricOption): The option item to remove.

     **/
    removeOption: function(criterionIndex, item) {
        var criterionItem = this.getCriterionItem(criterionIndex);
        criterionItem.optionContainer.remove(item);
    },

    /**
     Retrieve all options for a particular criterion.

     Args:
     criterionIndex (int): The index of the criterion, starting from 0.

     Returns:
     Array of OpenAssessment.RubricOption
     **/
    getAllOptions: function(criterionIndex) {
        var criterionItem = this.getCriterionItem(criterionIndex);
        return criterionItem.optionContainer.getAllItems();
    },

    /**
     Retrieve a particular option from the rubric.

     Args:
     criterionIndex (int): The index of the criterion, starting from 0.
     optionIndex (int): The index of the option within the criterion,
     starting from 0.

     Returns:
     OpenAssessment.RubricOption

     **/
    getOptionItem: function(criterionIndex, optionIndex) {
        var criterionItem = this.getCriterionItem(criterionIndex);
        return criterionItem.optionContainer.getItem(optionIndex);
    },

    /**
     Mark validation errors.

     Returns:
     Boolean indicating whether the view is valid.

     **/
    validate: function() {
        var criteria = this.getAllCriteria();
        var isValid = criteria.length > 0;
        if (!isValid) {
            this.criterionAddButton
                .addClass("openassessment_highlighted_field")
                .click(function() {
                        $(this).removeClass("openassessment_highlighted_field");
                    }
                );
        }

        $.each(criteria, function() {
            isValid = (this.validate() && isValid);
        });

        return isValid;
    },

    /**
     Return a list of validation errors visible in the UI.
     Mainly useful for testing.

     Returns:
     list of string

     **/
    validationErrors: function() {
        var errors = [];

        if (this.criterionAddButton.hasClass("openassessment_highlighted_field")) {
            errors.push("The rubric must contain at least one criterion");
        }

        // Sub-validates the criteria defined by the rubric
        $.each(this.getAllCriteria(), function() {
            errors = errors.concat(this.validationErrors());
        });

        return errors;
    },

    /**
     Clear all validation errors from the UI.
     **/
    clearValidationErrors: function() {
        this.criterionAddButton.removeClass("openassessment_highlighted_field");

        $.each(this.getAllCriteria(), function() {
            this.clearValidationErrors();
        });
    }
};
