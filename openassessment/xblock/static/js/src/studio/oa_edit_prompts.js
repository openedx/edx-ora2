/**
Editing interface for the prompts.

Args:
    element (DOM element): The DOM element representing this view.

Returns:
    OpenAssessment.EditPromptsView

**/
OpenAssessment.EditPromptsView = function(element) {
    this.element = element;

    this.promptsContainer = new OpenAssessment.Container(
        OpenAssessment.Prompt, {
            containerElement: $("#openassessment_prompts_list", this.element).get(0),
            templateElement: $("#openassessment_prompt_template", this.element).get(0),
            addButtonElement: $("#openassessment_prompts_add_prompt", this.element).get(0),
            removeButtonClass: "openassessment_prompt_remove_button",
            containerItemClass: "openassessment_prompt"
        }
    );
    this.promptsContainer.addEventListeners();
};


OpenAssessment.EditPromptsView.prototype = {

    /**
    Construct a list of prompts definitions from the editor UI.

    Returns:
        list of prompt objects

    Example usage:
    >>> editPromptsView.promptsDefinition();
    [
        {
            uuid: "cfvgbh657",
            description: "Description",
            order_num: 0,
        },
        ...
    ]

    **/
    promptsDefinition: function() {
        var prompts = this.promptsContainer.getItemValues();

        // Add order_num fields for prompts
        for (var prompt_idx = 0; prompt_idx < prompts.length; prompt_idx++) {
            var prompt = prompts[prompt_idx];
            prompt.order_num = prompt_idx;
        }

        return prompts;
    },

    /**
    Add a new prompt.
    Uses a client-side template to create the new prompt.
    **/
    addPrompt: function() {
        this.promptsContainer.add();
    },

    /**
    Remove a prompt.

    Args:
        item (OpenAssessment.RubricCriterion): The criterion item to remove.
    **/
    removePrompt: function(item) {
        this.promptsContainer.remove(item);
    },

    /**
    Retrieve all prompts.

    Returns:
        Array of OpenAssessment.Prompt objects.

    **/
    getAllPrompts: function() {
        return this.promptsContainer.getAllItems();
    },

    /**
    Retrieve a prompt item from the prompts.

    Args:
        index (int): The index of the prompt, starting from 0.

    Returns:
        OpenAssessment.Prompt or null

    **/
    getPromptItem: function(index) {
        return this.promptsContainer.getItem(index);
    },

    /**
    Mark validation errors.

    Returns:
        Boolean indicating whether the view is valid.

    **/
    validate: function() {
        return true;
    },

   /**
    Return a list of validation errors visible in the UI.
    Mainly useful for testing.

    Returns:
        list of string

    **/
    validationErrors: function() {
        var errors = [];
        return errors;
    },

    /**
    Clear all validation errors from the UI.
    **/
    clearValidationErrors: function() {}
};