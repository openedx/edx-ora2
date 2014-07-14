/**
Editing interface for the rubric prompt.

Args:
    element (DOM element): The DOM element representing this view.

Returns:
    OpenAssessment.EditPromptView

**/
OpenAssessment.EditPromptView = function(element) {
    this.element = element;
};


OpenAssessment.EditPromptView.prototype = {

    /**
    Get or set the text of the prompt.

    Args:
        text (string, optional): If provided, set the text of the prompt.

    Returns:
        string

    **/
    promptText: function(text) {
        var sel = $('#openassessment_prompt_editor', this.element);
        return OpenAssessment.Fields.stringField(sel, text);
    },

};