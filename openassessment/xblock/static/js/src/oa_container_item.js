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
OpenAssessment.RubricOption = function(parent){
    this.parent = parent;

    var htmlDefinition = parent.getHtmlDefinition();
    var id = parent.generateItemID();
    var replacementMechanism = new RegExp(htmlDefinition.replace, 'g');
    this.html = htmlDefinition.template.replace(replacementMechanism, id);

    this.selector =

};

OpenAssessment.RubricOption.prototype = {
    /**
    Returns: (str) the HTML definition for the rubric option, now with the appropriate substitutions.
    **/
    getHtml: function (){
        return this.html;
    },

    /**
    Returns: (str) the string selector which can be used to uniquely identify the object.
    **/
    getSelector: function (){
        return this.selector;
    },

    /**

    **/
    getFieldValues: function (){


    }
};

