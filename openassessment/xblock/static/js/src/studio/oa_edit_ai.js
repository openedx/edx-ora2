/**
 Interface for editing example definitions for AI assessment (Example Based Assessment).

 Args:
 element (DOM element): The DOM element representing the Examples Tab.

 **/
OpenAssessment.EditAIView = function(element) {
    var view = this;
    this.element = element;
    this.menuAndEditor = $("#openassessment_ai_editor_menu_and_editor", this.element);
    this.exampleAddButton = $('#openassessment_ai_menu_add_example', this.element);

    // The container for the examples stored in the view
    this.exampleContainer = new OpenAssessment.Container(
        OpenAssessment.AIExample, {
            containerElement: $("#openassessment_ai_examples", this.element).get(0),
            templateElement: $("#openassessment_ai_example_template", this.element).get(0),
            // Note that we do not add or remove using buttons, but rely on the MenuItem to perform that operation
            addButtonElement: "nope_we_dont_add_here",
            removeButtonClass: "nope_we_dont_remove_here",
            containerItemClass: "openassessment_ai_example"
        }
    );
    this.exampleContainer.addEventListeners();

    // A corresponding menu for the examples.  There is a 1:1 relationship between the two.
    this.exampleMenuContainer = new OpenAssessment.Container(
        OpenAssessment.AIExampleMenuItem, {
            containerElement: $("#openassessment_ai_example_menu", this.element).get(0),
            templateElement: $("#openassessment_ai_example_menu_item_template", this.element).get(0),
            addButtonElement: $("#openassessment_ai_menu_add_example", this.element).get(0),
            removeButtonClass: "openassessment_ai_example_remove_button",
            containerItemClass: "openassessment_ai_example_menu_item"
        }
    );
    this.exampleMenuContainer.addEventListeners();

    // Instantiates the button which switches between Normal editing mode and Import XML mode.
    $("#openassessment_ai_editor_upload_xml", this.element).click(function() {
        // Hides all editing panels, then shows the editing XML panel.
        OpenAssessment.ItemUtilities.addClassToAllButOne(
            view.menuAndEditor,
            '.openassessment_ai_editor_single_visibility',
            '#openassessment_ai_editor_import_xml',
            'is--hidden'
        );
        // Fades all menu items, then bods the selected menu item.
        OpenAssessment.ItemUtilities.addClassToAllButOne(
            view.menuAndEditor,
            '.openassessment_ai_menu_single_visibility',
            '#openassessment_ai_editor_upload_xml',
            'is--faded'
        );
    });

    // Identical to the above, but used for CSV upload
    $("#openassessment_ai_editor_upload_csv", this.element).click(function() {
        OpenAssessment.ItemUtilities.addClassToAllButOne(
            view.menuAndEditor,
            '.openassessment_ai_editor_single_visibility',
            '#openassessment_ai_editor_import_csv',
            'is--hidden'
        );
        OpenAssessment.ItemUtilities.addClassToAllButOne(
            view.menuAndEditor,
            '.openassessment_ai_menu_single_visibility',
            '#openassessment_ai_editor_upload_csv',
            'is--faded'
        );
    });

};


OpenAssessment.EditAIView.prototype = {

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
    },

    // TESTING METHODS, to clean up and make utile.

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
};
