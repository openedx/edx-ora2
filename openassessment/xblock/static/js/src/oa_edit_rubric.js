/**
Interface for editing rubric definitions.
**/
OpenAssessment.EditRubricView = function(element) {
    this.element = element;
    this.criteriaContainer = new OpenAssessment.Container(
        OpenAssessment.RubricCriterion, {
            containerElement: $("#openassessment_criterion_list", this.element).get(0),
            templateElement: $("#openassessment_criterion_template", this.element).get(0),
            addButtonElement: $("#openassessment_rubric_add_criterion", this.element).get(0),
            removeButtonClass: "openassessment_rubric_remove_button",
            containerItemClass: "openassessment_criterion",
        }
    );
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
        for (var criterion_idx = 0; criterion_idx < criteria.length; criterion_idx++) {
            var criterion = criteria[criterion_idx];
            criterion.order_num = criterion_idx;
            for (var option_idx = 0; option_idx < criterion.options.length; option_idx++) {
                var option = criterion.options[option_idx];
                option.order_num = option_idx;
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
    }
};