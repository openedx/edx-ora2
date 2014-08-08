OpenAssessment.EditAIView = function(element) {
    this.element = element;

    this.exampleAddButton = $('#openassessment_ai_selector_add_example', this.element);

    this.exampleContainer = new OpenAssessment.Container(
        OpenAssessment.AIExample, {
            containerElement: $("#openassessment_ai_examples", this.element).get(0),
            templateElement: $("#openassessment_ai_example_template", this.element).get(0),
            addButtonElement: $("#openassessment_ai_selector_add_example", this.element).get(0),
            removeButtonClass: "openassessment_ai_example_remove_button",
            containerItemClass: "openassessment_ai_example"
        }
    );
    this.exampleContainer.addEventListeners();

    this.exampleMenuContainer = new OpenAssessment.Container(
        OpenAssessment.AIExampleMenuItem, {
            containerElement: $("#openassessment_ai_example_selector", this.element).get(0),
            templateElement: $("#openassessment_ai_example_selector_item_template", this.element).get(0),
            addButtonElement: $("#openassessment_ai_selector_add_example", this.element).get(0),
            removeButtonClass: "openassessment_ai_example_remove_button",
            containerItemClass: "openassessment_ai_example_selector_item"
        }
    );
    this.exampleMenuContainer.addEventListeners();
};


OpenAssessment.EditAIView.prototype = {

    exampleDefinition: function() {
        return this.exampleContainer.getItemValues();
    },

    addExample: function() {
        this.exampleContainer.add();
        this.exampleMenuContainer.add();
    },

    removeExample: function(item) {
        this.exampleContainer.remove(item);
    },

    getExampleItem: function(index) {
        return this.exampleContainer.getItem(index);
    },

    /**
     Retrieve all examples from the AI Tab.

     Returns:
     Array of OpenAssessment.AIExample objects.

     **/
    getAllExamples: function() {
        return this.exampleContainer.getAllItems();
    },

    /**
     Mark validation errors.

     Returns:
     Boolean indicating whether the view is valid.

     **/
    validate: function() {
        var examples = this.getAllExamples();
        var isValid = examples.length > 0;
        if (!isValid) {
            this.exampleAddButton
                .addClass("openassessment_highlighted_field")
                .click( function() {
                    $(this).removeClass("openassessment_highlighted_field");
                }
            );
        }

        $.each(examples, function() {
            isValid = (this.validate() && isValid);
        });

    },

    /**
     Return a list of validation errors visible in the UI.
     Mainly useful for testing.

     Returns:
     list of string

     **/
    validationErrors: function() {
        var errors = [];

        if (this.exampleAddButton.hasClass("openassessment_highlighted_field")) {
            errors.push("There must be at least one example for Example Based Assessment (AI).");
        }

        // Sub-validates the criteria defined by the rubric
        $.each(this.getAllExamples(), function() {
            errors = errors.concat(this.validationErrors());
        });

        return errors;
    },

    /**
     Clear all validation errors from the UI.
     **/
    clearValidationErrors: function() {
        this.criterionAddButton.removeClass("openassessment_highlighted_field");

        $.each(this.getAllExamples(), function() {
            this.clearValidationErrors();
        });
    }
};
