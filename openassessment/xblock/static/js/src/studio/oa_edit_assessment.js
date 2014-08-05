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
        { min: 0, max: 99 }
    );
    this.mustBeGradedByField = new OpenAssessment.IntField(
        $("#peer_assessment_graded_by", this.element),
        { min: 0, max: 99 }
    );
    this.trackChangesField = new OpenAssessment.Fields.stringField(
        $("#peer_assessment_track_changes", this.element)
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

    // Configure the date and time fields
    this.startDatetimeControl = new OpenAssessment.DatetimeControl(
        this.element,
        "#peer_assessment_start_date",
        "#peer_assessment_start_time"
    ).install();

    this.dueDatetimeControl = new OpenAssessment.DatetimeControl(
        this.element,
        "#peer_assessment_due_date",
        "#peer_assessment_due_time"
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
            track_changes: this.trackChanges(),
            start: this.startDatetime(),
            due: this.dueDatetime()
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

    trackChanges: function(text) {
        var sel = $("#peer_assessment_track_changes", this.element);
        return OpenAssessment.Fields.stringField(sel, text);
    },

    /**
    Get or set the start date and time of the assessment.

    Args:
        dateString (string, optional): If provided, set the date (YY-MM-DD).
        timeString (string, optional): If provided, set the time (HH:MM, 24-hour clock).

    Returns:
        string (ISO-formatted UTC datetime)
    **/
    startDatetime: function(dateString, timeString) {
        return this.startDatetimeControl.datetime(dateString, timeString);
    },

    /**
    Get or set the due date and time of the assessment.

    Args:
        dateString (string, optional): If provided, set the date (YY-MM-DD).
        timeString (string, optional): If provided, set the time (HH:MM, 24-hour clock).

    Returns:
        string (ISO-formatted UTC datetime)
    **/
    dueDatetime: function(dateString, timeString) {
        return this.dueDatetimeControl.datetime(dateString, timeString);
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
        var startValid = this.startDatetimeControl.validate();
        var dueValid = this.dueDatetimeControl.validate();
        var mustGradeValid = this.mustGradeField.validate();
        var mustBeGradedByValid = this.mustBeGradedByField.validate();
        return startValid && dueValid && mustGradeValid && mustBeGradedByValid;
    },

   /**
    Return a list of validation errors visible in the UI.
    Mainly useful for testing.

    Returns:
        list of string

    **/
    validationErrors: function() {
        var errors = [];
        if (this.startDatetimeControl.validationErrors().length > 0) {
            errors.push("Peer assessment start is invalid");
        }
        if (this.dueDatetimeControl.validationErrors().length > 0) {
            errors.push("Peer assessment due is invalid");
        }
        if (this.mustGradeField.validationErrors().length > 0) {
            errors.push("Peer assessment must grade is invalid");
        }
        if(this.mustBeGradedByField.validationErrors().length > 0) {
            errors.push("Peer assessment must be graded by is invalid");
        }
        return errors;
    },

    /**
    Clear all validation errors from the UI.
    **/
    clearValidationErrors: function() {
        this.startDatetimeControl.clearValidationErrors();
        this.dueDatetimeControl.clearValidationErrors();
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

    // Configure the date and time fields
    this.startDatetimeControl = new OpenAssessment.DatetimeControl(
        this.element,
        "#self_assessment_start_date",
        "#self_assessment_start_time"
    ).install();

    this.dueDatetimeControl = new OpenAssessment.DatetimeControl(
        this.element,
        "#self_assessment_due_date",
        "#self_assessment_due_time"
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
            start: this.startDatetime(),
            due: this.dueDatetime()
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
    Get or set the start date and time of the assessment.

    Args:
        dateString (string, optional): If provided, set the date (YY-MM-DD).
        timeString (string, optional): If provided, set the time (HH:MM, 24-hour clock).

    Returns:
        string (ISO-formatted UTC datetime)
    **/
    startDatetime: function(dateString, timeString) {
        return this.startDatetimeControl.datetime(dateString, timeString);
    },

    /**
    Get or set the due date and time of the assessment.

    Args:
        dateString (string, optional): If provided, set the date (YY-MM-DD).
        timeString (string, optional): If provided, set the time (HH:MM, 24-hour clock).

    Returns:
        string (ISO-formatted UTC datetime)
    **/
    dueDatetime: function(dateString, timeString) {
        return this.dueDatetimeControl.datetime(dateString, timeString);
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
        var startValid = this.startDatetimeControl.validate();
        var dueValid = this.dueDatetimeControl.validate();
        return startValid && dueValid;
    },

   /**
    Return a list of validation errors visible in the UI.
    Mainly useful for testing.

    Returns:
        list of string

    **/
    validationErrors: function() {
        var errors = [];
        if (this.startDatetimeControl.validationErrors().length > 0) {
            errors.push("Self assessment start is invalid");
        }
        if (this.dueDatetimeControl.validationErrors().length > 0) {
            errors.push("Self assessment due is invalid");
        }
        return errors;
    },

    /**
    Clear all validation errors from the UI.
    **/
    clearValidationErrors: function() {
        this.startDatetimeControl.clearValidationErrors();
        this.dueDatetimeControl.clearValidationErrors();
    },
};

/**
Interface for editing self assessment settings.

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
                answer: "I love pokemon",
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
Interface for editing example-based assessment settings.

Args:
    element (DOM element): The DOM element representing this view.

Returns:
    OpenAssessment.EditExampleBasedAssessmentView

**/
OpenAssessment.EditExampleBasedAssessmentView = function(element) {
    this.element = element;
    this.name = "example-based-assessment";

    new OpenAssessment.ToggleControl(
        $("#include_ai_assessment", this.element),
        $("#ai_assessment_settings_editor", this.element),
        $("#ai_assessment_description_closed", this.element),
        new OpenAssessment.Notifier([
            new OpenAssessment.AssessmentToggleListener()
        ])
    ).install();
};

OpenAssessment.EditExampleBasedAssessmentView.prototype = {

    /**
    Return a description of the assessment.

    Returns:
        object literal

    Example usage:
    >>> editTrainingView.description();
    {
        examples_xml: "XML DEFINITION HERE",
    }

    **/
    description: function() {
        return {
            examples_xml: this.exampleDefinitions()
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
        var sel = $("#include_ai_assessment", this.element);
        return OpenAssessment.Fields.booleanField(sel, isEnabled);
    },

    /**
    Toggle whether the assessment is enabled or disabled.
    This triggers the actual click event and is mainly useful for testing.
    **/
    toggleEnabled: function() {
        $("#include_ai_assessment", this.element).click();
    },

    /**
    Get or set the XML defining the training examples.

    Args:
        xml (string, optional): The XML of the training example definitions.

    Returns:
        string

    **/
    exampleDefinitions: function(xml) {
        var sel = $("#ai_training_examples", this.element);
        return OpenAssessment.Fields.stringField(sel, xml);
    },

    /**
    Gets the ID of the assessment

    Returns:
    string (CSS ID of the Element object)
    **/
    getID: function() {
        return $(this.element).attr('id');
    },

    validate: function() { return true; },
    validationErrors: function() { return []; },
    clearValidationErrors: function() {},
};
