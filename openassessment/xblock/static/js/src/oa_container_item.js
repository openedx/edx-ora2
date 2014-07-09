/**
 * Created by gward on 7/9/14.
 */


/**
The RubricOption Class used to construct and maintain references to rubric options from within an options
container object. Constructs a new RubricOption element.

Args:
    parent (OpenAssessment.Container): The container that the option is a member of.

Returns:
    OpenAssessment.RubricOption
**/
OpenAssessment.RubricOption = function(selector){
    this.selector = selector;
};

OpenAssessment.RubricOption.prototype = {
    /**

    **/
    getFieldValues: function (){
        var name = $('.openassessment_criterion_option_name', this.selector).prop('value');
        var points = $('.openassessment_criterion_option_points', this.selector).prop('value');
        var explanation = $('.openassessment_criterion_option_explanation', this.selector).prop('value');
        return {
            'name': name,
            'points': points,
            'explanation': explanation
        };
    }
};

