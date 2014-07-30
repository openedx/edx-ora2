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
    },

    /**
     Format the option label, including the point value, and add it to the option.
     Relies on the data-points and data-label attributes to provide information about the option.

     Args:
     element (Jquery Element): The element that represents the object.
     **/
    refreshOptionString: function(element) {
        var points = $(element).data('points');
        var label = $(element).data('label');
        // We don't want the lack of a label to make it look like - 1 points.
        if (label == ""){
            label = gettext('Unnamed Option');
        }
        var singularString = label + " - " + points + " point";
        var multipleString = label + " - " + points + " points";
        // If the option doesn't have a data points value, that indicates to us that it is not a user-specified option,
        // but represents the "Not Selected" option which all criterion drop-downs have.
        if (typeof points === 'undefined') {
            $(element).text(
                gettext('Not Selected')
            );
        }
        // Otherwise, set the text of the option element to be the properly conjugated, translated string.
        else {
            $(element).text(
                ngettext(singularString, multipleString, points)
            );
        }
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
            label: OpenAssessment.Fields.stringField(
                $('.openassessment_criterion_option_label', this.element)
            ),
            points: OpenAssessment.Fields.intField(
                $('.openassessment_criterion_option_points', this.element)
            ),
            explanation: OpenAssessment.Fields.stringField(
                $('.openassessment_criterion_option_explanation', this.element)
            )
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
            label: OpenAssessment.Fields.stringField(
                $('.openassessment_criterion_label', this.element)
            ),
            prompt: OpenAssessment.Fields.stringField(
                $('.openassessment_criterion_prompt', this.element)
            ),
            feedback: OpenAssessment.Fields.stringField(
                $('.openassessment_criterion_feedback', this.element)
            ),
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
    // Goes through and instantiates the option description in the training example for each option.
    $(".openassessment_training_example_criterion_option", this.element) .each( function () {
        $('option', this).each(function(){
            OpenAssessment.ItemUtilities.refreshOptionString($(this));
        });
    });
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
    updateHandler: function() {}
};