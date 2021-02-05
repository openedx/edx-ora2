/**
 Interface for editing peer assessment settings.

 Args:
 element (DOM element): The DOM element representing this view.

 Returns:
 OpenAssessment.EditPeerAssessmentView

 **/
OpenAssessment.EditPeerAssessmentView = function(element) {
    this.element = element;
    this.name = "peer-assessment";
    this.mustGradeField = new OpenAssessment.IntField(
        $("#peer_assessment_must_grade", this.element),
        {min: 0, max: 99}
    );
    this.mustBeGradedByField = new OpenAssessment.IntField(
        $("#peer_assessment_graded_by", this.element),
        {min: 0, max: 99}
    );

    // Configure the toggle checkbox to enable/disable this assessment
    new OpenAssessment.ToggleControl(
        $("#include_peer_assessment", this.element),
        $("#peer_assessment_settings_editor", this.element),
        $("#peer_assessment_description_closed", this.element),
        new OpenAssessment.Notifier([
            new OpenAssessment.AssessmentToggleListener()
        ])
    ).install();
};

OpenAssessment.EditPeerAssessmentView.prototype = {

    /**
     Return a description of the assessment.

     Returns:
     object literal

     Example usage:
     >>> editPeerView.description();
     {
         must_grade: 5,
         must_be_graded_by: 2,
         start: null,
         due: "2014-04-1T00:00"
     }
     **/
    description: function() {
        return {
            must_grade: this.mustGradeNum(),
            must_be_graded_by: this.mustBeGradedByNum(),
        };
    },

    /**
     Get or set whether the assessment is enabled.

     Args:
     isEnabled (boolean, optional): If provided, set the enabled state of the assessment.

     Returns:
     boolean
     ***/
    isEnabled: function(isEnabled) {
        var sel = $("#include_peer_assessment", this.element);
        return OpenAssessment.Fields.booleanField(sel, isEnabled);
    },

    /**
     Toggle whether the assessment is enabled or disabled.
     This triggers the actual click event and is mainly useful for testing.
     **/
    toggleEnabled: function() {
        $("#include_peer_assessment", this.element).click();
    },

    /**
     Get or set the required number of submissions a student must peer-assess.

     Args:
     num (int, optional): If provided, set the required number of assessments.

     Returns:
     int
     **/
    mustGradeNum: function(num) {
        if (num !== undefined) { this.mustGradeField.set(num); }
        return this.mustGradeField.get();
    },

    /**
     Get or set the required number of peer-assessments a student must receive.

     Args:
     num (int, optional): If provided, set the required number of assessments.

     Returns:
     int
     **/
    mustBeGradedByNum: function(num) {
        if (num !== undefined) { this.mustBeGradedByField.set(num); }
        return this.mustBeGradedByField.get();
    },

    /**
     Gets the ID of the assessment

     Returns:
     string (CSS ID of the Element object)
     **/
    getID: function() {
        return $(this.element).attr('id');
    },

    /**
     Mark validation errors.

     Returns:
     Boolean indicating whether the view is valid.

     **/
    validate: function() {
        var mustGradeValid = this.mustGradeField.validate();
        var mustBeGradedByValid = this.mustBeGradedByField.validate();
        return mustGradeValid && mustBeGradedByValid;
    },

    /**
     Return a list of validation errors visible in the UI.
     Mainly useful for testing.

     Returns:
     list of string

     **/
    validationErrors: function() {
        var errors = [];
        if (this.mustGradeField.validationErrors().length > 0) {
            errors.push("Peer assessment must grade is invalid");
        }
        if (this.mustBeGradedByField.validationErrors().length > 0) {
            errors.push("Peer assessment must be graded by is invalid");
        }
        return errors;
    },

    /**
     Clear all validation errors from the UI.
     **/
    clearValidationErrors: function() {
        this.mustGradeField.clearValidationErrors();
        this.mustBeGradedByField.clearValidationErrors();
    },
};

/**
 Interface for editing self assessment settings.

 Args:
 element (DOM element): The DOM element representing this view.

 Returns:
 OpenAssessment.EditSelfAssessmentView

 **/
OpenAssessment.EditSelfAssessmentView = function(element) {
    this.element = element;
    this.name = "self-assessment";

    // Configure the toggle checkbox to enable/disable this assessment
    new OpenAssessment.ToggleControl(
        $("#include_self_assessment", this.element),
        $("#self_assessment_settings_editor", this.element),
        $("#self_assessment_description_closed", this.element),
        new OpenAssessment.Notifier([
            new OpenAssessment.AssessmentToggleListener()
        ])
    ).install();
};

OpenAssessment.EditSelfAssessmentView.prototype = {

    /**
     Return a description of the assessment.

     Returns:
     object literal

     Example usage:
     >>> editSelfView.description();
     {
         start: null,
         due: "2014-04-1T00:00"
     }

     **/
    description: function() {
        return {
            required: this.isEnabled(),
        };
    },

    /**
     Get or set whether the assessment is enabled.

     Args:
     isEnabled (boolean, optional): If provided, set the enabled state of the assessment.

     Returns:
     boolean
     ***/
    isEnabled: function(isEnabled) {
        var sel = $("#include_self_assessment", this.element);
        return OpenAssessment.Fields.booleanField(sel, isEnabled);
    },

    /**
     Toggle whether the assessment is enabled or disabled.
     This triggers the actual click event and is mainly useful for testing.
     **/
    toggleEnabled: function() {
        $("#include_self_assessment", this.element).click();
    },

    /**
     Gets the ID of the assessment

     Returns:
     string (CSS ID of the Element object)
     **/
    getID: function() {
        return $(this.element).attr('id');
    },

    /**
     Mark validation errors.

     Returns:
     Boolean indicating whether the view is valid.

     **/
    validate: function() {
        return true; //Nothing to validate, the only input is a boolean and either state is valid
    },

    /**
     * Return a list of validation errors visible in the UI.
     * Mainly useful for testing.
     *
     * @returns {Array} - always empty, function called but not actually used.
     */
    validationErrors: function() {
        return [];
    },

    /**
     * Clear all validation errors from the UI.
     */
    clearValidationErrors: function() {
        //do nothing
    }
};

/**
 Interface for editing student training assessment settings.

 Args:
 element (DOM element): The DOM element representing this view.

 Returns:
 OpenAssessment.EditStudentTrainingView

 **/
OpenAssessment.EditStudentTrainingView = function(element) {
    this.element = element;
    this.name = "student-training";

    new OpenAssessment.ToggleControl(
        $("#include_student_training", this.element),
        $("#student_training_settings_editor", this.element),
        $("#student_training_description_closed", this.element),
        new OpenAssessment.Notifier([
            new OpenAssessment.AssessmentToggleListener()
        ])
    ).install();

    this.exampleContainer = new OpenAssessment.Container(
        OpenAssessment.TrainingExample, {
            containerElement: $("#openassessment_training_example_list", this.element).get(0),
            templateElement: $("#openassessment_training_example_template", this.element).get(0),
            addButtonElement: $(".openassessment_add_training_example", this.element).get(0),
            removeButtonClass: "openassessment_training_example_remove",
            containerItemClass: "openassessment_training_example"
        }
    );

    this.exampleContainer.addEventListeners();
};

OpenAssessment.EditStudentTrainingView.prototype = {

    /**
     Return a description of the assessment.

     Returns:
     object literal

     Example usage:
     >>> editTrainingView.description();
     {
         examples: [
             {
                 answer: ("I love pokemon 1", "I love pokemon 2"),
                 options_selected: [
                     {
                         criterion: "brevity",
                         option: "suberb"
                     },
                         criterion: "accuracy",
                         option: "alright"
                     }
                     ...
                 ]
             },
     ...
     ]
     }
     **/
    description: function() {
        return {
            examples: this.exampleContainer.getItemValues()
        };
    },

    /**
     Get or set whether the assessment is enabled.

     Args:
     isEnabled (boolean, optional): If provided, set the enabled state of the assessment.

     Returns:
     boolean
     ***/
    isEnabled: function(isEnabled) {
        var sel = $("#include_student_training", this.element);
        return OpenAssessment.Fields.booleanField(sel, isEnabled);
    },

    /**
     Toggle whether the assessment is enabled or disabled.
     This triggers the actual click event and is mainly useful for testing.
     **/
    toggleEnabled: function() {
        $("#include_student_training", this.element).click();
    },

    /**
     Gets the ID of the assessment

     Returns:
     string (CSS ID of the Element object)
     **/
    getID: function() {
        return $(this.element).attr('id');
    },

    /**
     Mark validation errors.

     Returns:
     Boolean indicating whether the view is valid.

     **/
    validate: function() {
        var isValid = true;

        $.each(this.exampleContainer.getAllItems(), function() {
            isValid = this.validate() && isValid;
        });

        return isValid;
    },

    /**
     Return a list of validation errors visible in the UI.
     Mainly useful for testing.

     Returns:
     list of string

     **/
    validationErrors: function() {
        var errors = [];
        $.each(this.exampleContainer.getAllItems(), function() {
            errors = errors.concat(this.validationErrors());
        });
        return errors;
    },

    /**
     Clear all validation errors from the UI.
     **/
    clearValidationErrors: function() {
        $.each(this.exampleContainer.getAllItems(), function() {
            this.clearValidationErrors();
        });
    },

    /**
     Adds a new training example by copying the training example template.
     Primarily used for testing.
     **/
    addTrainingExample: function() {
        this.exampleContainer.add();
    }
};

/**
 * Interface for editing staff assessment settings.
 *
 * @param {Object} element - The DOM element representing this view.
 * @constructor
 *
 */
OpenAssessment.EditStaffAssessmentView = function(element) {
    this.element = element;
    this.name = "staff-assessment";

    // Configure the toggle checkbox to enable/disable this assessment
    new OpenAssessment.ToggleControl(
        $("#include_staff_assessment", this.element),
        $("#staff_assessment_description", this.element),
        $("#staff_assessment_description", this.element), //open and closed selectors are the same!
        new OpenAssessment.Notifier([
            new OpenAssessment.AssessmentToggleListener()
        ])
    ).install();
};

OpenAssessment.EditStaffAssessmentView.prototype = {

    /**
     * Return a description of the assessment.
     *
     * @returns {Object} Representation of the view.
     */
    description: function() {
        return {
            required: this.isEnabled(),
        };
    },

    /**
     * Get or set whether the assessment is enabled.
     *
     * @param {Boolean} isEnabled - If provided, set the enabled state of the assessment.
     * @returns {Boolean}
     */
    isEnabled: function(isEnabled) {
        var sel = $("#include_staff_assessment", this.element);
        return OpenAssessment.Fields.booleanField(sel, isEnabled);
    },

    /**
     * Toggle whether the assessment is enabled or disabled.
     * This triggers the actual click event and is mainly useful for testing.
     */
    toggleEnabled: function() {
        $("#include_staff_assessment", this.element).click();
    },

    /**
     * Gets the ID of the assessment
     *
     * @returns {String} CSS class of the Element object
     */
    getID: function() {
        return $(this.element).attr('id');
    },

    /**
     * Mark validation errors.
     *
     * @returns {Boolean} Whether the view is valid.
     *
     */
    validate: function() {
        return true; //Nothing to validate, the only input is a boolean and either state is valid
    },

    /**
     * Return a list of validation errors visible in the UI.
     * Mainly useful for testing.
     *
     * @returns {Array} - always empty, function called but not actually used.
     */
    validationErrors: function() {
        return [];
    },

    /**
     * Clear all validation errors from the UI.
     */
    clearValidationErrors: function() {
        //do nothing
    },
};
