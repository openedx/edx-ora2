/**
The RubricOption Class used to construct and maintain references to rubric options from within an options
container object. Constructs a new RubricOption element.

Args:
    parent (OpenAssessment.Container): The container that the option is a member of.

Returns:
    OpenAssessment.RubricOption
**/
OpenAssessment.RubricOption = function(element){
    this.element = element;
};

OpenAssessment.RubricOption.prototype = {

    /**
    Finds the values currently entered in the Option's fields, and returns them in a dictionary to the user.

    Returns:
        (dict) of the form:
            {
                'name': 'Real Bad',
                'points': 1,
                'explanation': 'Essay was primarily composed of emojis.'
            }
    **/
    getFieldValues: function (){
        var name = $('.openassessment_criterion_option_name', this.element).prop('value');
        var points = $('.openassessment_criterion_option_points', this.element).prop('value');
        var explanation = $('.openassessment_criterion_option_explanation', this.element).prop('value');
        return {
            'name': name,
            'points': points,
            'explanation': explanation
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
OpenAssessment.RubricCriterion = function(element){
    this.element = element;
    this.optionContainer = new OpenAssessment.Container(
        $('.openassessment_criterion_option_list'),
        {
            'openassessment_criterion_option': OpenAssessment.RubricOption
        }
    );
};


OpenAssessment.RubricCriterion.prototype = {
    /**
    Finds the values currently entered in the Criterion's fields, and returns them in a dictionary to the user.

    Returns:
        (dict) of the form:
            {
                'name': 'Emoji Content',
                'prompt': 'How expressive was the author with their words, and how much did they rely on emojis?',
                'feedback': 'optional',
                'options': [
                    {
                        'name': 'Real Bad',
                        'points': 1,
                        'explanation': 'Essay was primarily composed of emojis.'
                    }
                    ...
                ]
            }
    **/
    getFieldValues: function (){
        var name = $('.openassessment_criterion_name', this.element).prop('value');
        var prompt = $('.openassessment_criterion_prompt', this.element).prop('value');
        var feedback = $('.openassessment_criterion_feedback', this.element).prop('value');
        var options = this.optionContainer.getItemValues();
        return {
            'name': name,
            'prompt': prompt,
            'options': options,
            'feedback': feedback
        };
    }
};