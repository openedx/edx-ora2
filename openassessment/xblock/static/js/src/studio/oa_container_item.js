OpenAssessment.ItemUtilities = {
    /**
     Utility method for creating a unique name given a set of
     options.

     Args:
     selector (JQuery selector): Selector used to find the relative attribute
     for the name.
     nameAttribute (str): The name of the attribute that stores the unique
     names for a particular set.

     Returns:
     A unique name for an object in the collection.
     */
    createUniqueName: function(selector, nameAttribute) {
        var index = 0;
        while (index <= selector.length) {
            if (selector.parent().find("*[" + nameAttribute + "='" + index + "']").length === 0) {
                return index.toString();
            }
            index++;
        }
        return index.toString();
    }
};

/**
The RubricOption Class used to construct and maintain references to rubric options from within an options
container object. Constructs a new RubricOption element.

Args:
    element (OpenAssessment.Container): The container that the option is a member of.
    notifier (OpenAssessment.Notifier): Used to send notifications of updates to rubric options.

Returns:
    OpenAssessment.RubricOption
**/
OpenAssessment.RubricOption = function(element, notifier) {
    this.element = element;
    this.notifier = notifier;
    this.pointsField = new OpenAssessment.IntField(
        $(".openassessment_criterion_option_points", this.element),
        { min: 0, max: 999 }
    );
    $(this.element).focusout($.proxy(this.updateHandler, this));
};

OpenAssessment.RubricOption.prototype = {

    /**
    Finds the values currently entered in the Option's fields, and returns them.

    Returns:
        object literal of the form:
        {
            'name': 'Real Bad',
            'points': 1,
            'explanation': 'Essay was primarily composed of emojis.'
        }
    **/
    getFieldValues: function () {
        var fields = {
            label: this.label(),
            points: this.points(),
            explanation: this.explanation()
        };

        // New options won't have unique names assigned.
        // By convention, we exclude the "name" key from the JSON dict
        // sent to the server, and the server will assign a unique name.
        var nameString = OpenAssessment.Fields.stringField(
            $('.openassessment_criterion_option_name', this.element)
        );
        if (nameString !== "") { fields.name = nameString; }

        return fields;
    },

    /**
    Get or set the label of the option.

    Args:
        label (string, optional): If provided, set the label to this string.

    Returns:
        string

    **/
    label: function(label) {
        var sel = $('.openassessment_criterion_option_label', this.element);
        return OpenAssessment.Fields.stringField(sel, label);
    },

    /**
    Get or set the point value of the option.

    Args:
        points (int, optional): If provided, set the point value of the option.

    Returns:
        int

    **/
    points: function(points) {
        if (points !== undefined) { this.pointsField.set(points); }
        return this.pointsField.get();
    },

    /**
    Get or set the explanation for the option.

    Args:
        explanation (string, optional): If provided, set the explanation to this string.

    Returns:
        string

    **/
    explanation: function(explanation) {
        var sel = $('.openassessment_criterion_option_explanation', this.element);
        return OpenAssessment.Fields.stringField(sel, explanation);
    },

    /**
     Hook into the event handler for addition of a criterion option.

     */
    addHandler: function (){

        var criterionElement = $(this.element).closest(".openassessment_criterion");
        var criterionName = $(criterionElement).data('criterion');
        var criterionLabel = $(".openassessment_criterion_label", criterionElement).val();
        var options = $(".openassessment_criterion_option", this.element.parent());
        // Create the unique name for this option.
        var name = OpenAssessment.ItemUtilities.createUniqueName(options, "data-option");

        // Set the criterion name and option name in the new rubric element.
        $(this.element)
            .attr("data-criterion", criterionName)
            .attr("data-option", name);
        $(".openassessment_criterion_option_name", this.element).attr("value", name);

        var fields = this.getFieldValues();
        this.notifier.notificationFired(
            "optionAdd",
            {
                "criterionName": criterionName,
                "criterionLabel": criterionLabel,
                "name": name,
                "label": fields.label,
                "points": fields.points
            }
        );
    },

    /**
     Hook into the event handler for removal of a criterion option.

     */
    removeHandler: function (){
        var criterionName = $(this.element).data('criterion');
        var optionName = $(this.element).data('option');
        this.notifier.notificationFired(
            "optionRemove",
            {
                "criterionName": criterionName,
                "name": optionName
            }
        );
    },

    /**
     Hook into the event handler when a rubric criterion option is
     modified.

     */
    updateHandler: function(){
        var fields = this.getFieldValues();
        var criterionName = $(this.element).data('criterion');
        var optionName = $(this.element).data('option');
        var optionLabel = fields.label;
        var optionPoints = fields.points;
        this.notifier.notificationFired(
            "optionUpdated",
            {
                "criterionName": criterionName,
                "name": optionName,
                "label": optionLabel,
                "points": optionPoints
            }
        );
    },

    /**
    Mark validation errors.

    Returns:
        Boolean indicating whether the option is valid.

    **/
    validate: function() {
        return this.pointsField.validate();
    },

    /**
    Return a list of validation errors visible in the UI.
    Mainly useful for testing.

    Returns:
        list of string

    **/
    validationErrors: function() {
        var hasError = (this.pointsField.validationErrors().length > 0);
        return hasError ? ["Option points are invalid"] : [];
    },

    /**
    Clear all validation errors from the UI.
    **/
    clearValidationErrors: function() {
        this.pointsField.clearValidationErrors();
    }
};

/**
The RubricCriterion Class is used to construct and get information from a rubric element within
the DOM.

Args:
    element (JQuery Object): The selection which describes the scope of the criterion.
    notifier (OpenAssessment.Notifier): Used to send notifications of updates to rubric criteria.

Returns:
    OpenAssessment.RubricCriterion
 **/
OpenAssessment.RubricCriterion = function(element, notifier) {
    this.element = element;
    this.notifier = notifier;
    this.optionContainer = new OpenAssessment.Container(
        OpenAssessment.RubricOption, {
            containerElement: $(".openassessment_criterion_option_list", this.element).get(0),
            templateElement: $("#openassessment_option_template").get(0),
            addButtonElement: $(".openassessment_criterion_add_option", this.element).get(0),
            removeButtonClass: "openassessment_criterion_option_remove_button",
            containerItemClass: "openassessment_criterion_option",
            notifier: this.notifier
        }
    );

    $(this.element).focusout($.proxy(this.updateHandler, this));
};


OpenAssessment.RubricCriterion.prototype = {
    /**
    Finds the values currently entered in the Criterion's fields, and returns them.

    Returns:
        object literal of the form:
        {
            'name': 'Emoji Content',
            'prompt': 'How expressive was the author with their words, and how much did they rely on emojis?',
            'feedback': 'optional',
            'options': [
                {
                    'name': 'Real Bad',
                    'points': 1,
                    'explanation': 'Essay was primarily composed of emojis.'
                },
                ...
            ]
        }
    **/
    getFieldValues: function () {
        var fields = {
            label: this.label(),
            prompt: this.prompt(),
            feedback: this.feedback(),
            options: this.optionContainer.getItemValues()
        };

        // New criteria won't have unique names assigned.
        // By convention, we exclude the "name" key from the JSON dict
        // sent to the server, and the server will assign a unique name.
        var nameString = OpenAssessment.Fields.stringField(
            $('.openassessment_criterion_name', this.element)
        );
        if (nameString !== "") { fields.name = nameString; }

        return fields;
    },

    /**
    Get or set the label of the criterion.

    Args:
        label (string, optional): If provided, set the label to this string.

    Returns:
        string

    **/
    label: function(label) {
        var sel = $('.openassessment_criterion_label', this.element);
        return OpenAssessment.Fields.stringField(sel, label);
    },

    /**
    Get or set the prompt of the criterion.

    Args:
        prompt (string, optional): If provided, set the prompt to this string.

    Returns:
        string

    **/
    prompt: function(prompt) {
        var sel = $('.openassessment_criterion_prompt', this.element);
        return OpenAssessment.Fields.stringField(sel, prompt);
    },

    /**
    Get the feedback value for the criterion.
    This is one of: "disabled", "optional", or "required".

    Returns:
        string

    **/
    feedback: function() {
        return $('.openassessment_criterion_feedback', this.element).val();
    },

    /**
    Add an option to the criterion.
    Uses the client-side template to create the new option.
    **/
    addOption: function() {
        this.optionContainer.add();
    },

    /**
     Hook into the event handler for addition of a criterion.

     */
    addHandler: function (){
        var criteria = $(".openassessment_criterion", this.element.parent());
        // Create the unique name for this option.
        var name = OpenAssessment.ItemUtilities.createUniqueName(criteria, "data-criterion");
        // Set the criterion name in the new rubric element.
        $(this.element).attr("data-criterion", name);
        $(".openassessment_criterion_name", this.element).attr("value", name);
    },

    /**
     Hook into the event handler for removal of a criterion.

     */
    removeHandler: function(){
        var criterionName = $(this.element).data('criterion');
        this.notifier.notificationFired("criterionRemove", {'criterionName': criterionName});
    },

    /**
     Hook into the event handler when a rubric criterion is modified.

     */
    updateHandler: function(){
        var fields = this.getFieldValues();
        var criterionName = fields.name;
        var criterionLabel = fields.label;
        this.notifier.notificationFired(
            "criterionUpdated",
            {'criterionName': criterionName, 'criterionLabel': criterionLabel}
        );
    },

    /**
    Mark validation errors.

    Returns:
        Boolean indicating whether the criterion is valid.

    **/
    validate: function() {
        var isValid = true;
        $.each(this.optionContainer.getAllItems(), function() {
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
        $.each(this.optionContainer.getAllItems(), function() {
            errors = errors.concat(this.validationErrors());
        });
        return errors;
    },

    /**
    Clear all validation errors from the UI.
    **/
    clearValidationErrors: function() {
        $.each(this.optionContainer.getAllItems(), function() {
            this.clearValidationErrors();
        });
    }
};


/**
 The TrainingExample class is used to construct and retrieve information from its element within the DOM

 Args:
     element (JQuery Object): the selection which identifies the scope of the training example.

 Returns:
     OpenAssessment.TrainingExample

 **/
OpenAssessment.TrainingExample = function(element){
    this.element = element;
};

OpenAssessment.TrainingExample.prototype = {
    /**
     Returns the values currently stored in the fields associated with this training example.
     **/
    getFieldValues: function () {

        // Iterates through all of the options selected by the training example, and adds them
        // to a list.
        var optionsSelected = [];
        $(".openassessment_training_example_criterion_option", this.element) .each( function () {
            optionsSelected.push({
                criterion: $(this).data('criterion'),
                option: $(this).prop('value')
            });
        });

        return {
            answer: $('.openassessment_training_example_essay', this.element).first().prop('value'),
            options_selected: optionsSelected
        };
    },

    addHandler: function() {},
    removeHandler: function() {},
    updateHandler: function() {},

    validate: function() { return true; },
    validationErrors: function() { return []; },
    clearValidationErrors: function() {}
};