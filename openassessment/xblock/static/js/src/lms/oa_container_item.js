/**
The RubricOption Class used to construct and maintain references to rubric options from within an options
container object. Constructs a new RubricOption element.

Args:
    element (OpenAssessment.Container): The container that the option is a member of.

Returns:
    OpenAssessment.RubricOption
**/
OpenAssessment.RubricOption = function(element) {
    this.element = element;
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
        return {
            name: OpenAssessment.Fields.stringField(
                $('.openassessment_criterion_option_name', this.element)
            ),
            points: OpenAssessment.Fields.intField(
                $('.openassessment_criterion_option_points', this.element)
            ),
            explanation: OpenAssessment.Fields.stringField(
                $('.openassessment_criterion_option_explanation', this.element)
            )
        };
    }
};

/**
The RubricCriterion Class is used to construct and get information from a rubric element within
the DOM.

Args:
    element (JQuery Object): The selection which describes the scope of the criterion.

Returns:
    OpenAssessment.RubricCriterion
 **/
OpenAssessment.RubricCriterion = function(element) {
    this.element = element;
    this.optionContainer = new OpenAssessment.Container(
        OpenAssessment.RubricOption, {
            containerElement: $(".openassessment_criterion_option_list", this.element).get(0),
            templateElement: $("#openassessment_option_template").get(0),
            addButtonElement: $(".openassessment_criterion_add_option", this.element).get(0),
            removeButtonClass: "openassessment_criterion_option_remove_button",
            containerItemClass: "openassessment_criterion_option",
        }
    );
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
        return {
            name: OpenAssessment.Fields.stringField(
                $('.openassessment_criterion_name', this.element)
            ),
            prompt: OpenAssessment.Fields.stringField(
                $('.openassessment_criterion_prompt', this.element)
            ),
            feedback: OpenAssessment.Fields.stringField(
                $('.openassessment_criterion_feedback', this.element)
            ),
            options: this.optionContainer.getItemValues()
        };
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
    }

};