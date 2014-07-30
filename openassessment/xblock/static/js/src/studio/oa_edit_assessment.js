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

    // Configure the toggle checkbox to enable/disable this assessment
    new OpenAssessment.ToggleControl(
        this.element,
        "#peer_assessment_description_closed",
        "#peer_assessment_settings_editor"
    ).install("#include_peer_assessment");

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
    Get or set the required number of submissions a student must peer-assess.

    Args:
        num (int, optional): If provided, set the required number of assessments.

    Returns:
        int
    **/
    mustGradeNum: function(num) {
        var sel = $("#peer_assessment_must_grade", this.element);
        return OpenAssessment.Fields.intField(sel, num);
    },

    /**
    Get or set the required number of peer-assessments a student must receive.

    Args:
        num (int, optional): If provided, set the required number of assessments.

    Returns:
        int
    **/
    mustBeGradedByNum: function(num) {
        var sel = $("#peer_assessment_graded_by", this.element);
        return OpenAssessment.Fields.intField(sel, num);
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
    TODO
    **/
    validate: function() {
        return this.startDatetimeControl.validate() && this.dueDatetimeControl.validate();
    },

    /**
    TODO
    **/
    validationErrors: function() {
        var errors = [];
        if (this.startDatetimeControl.validationErrors().length > 0) {
            errors.push("Peer assessment start is invalid");
        }
        if (this.dueDatetimeControl.validationErrors().length > 0) {
            errors.push("Peer assessment due is invalid");
        }
        return errors;
    },

    /**
    TODO
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
    OpenAssessment.EditSelfAssessmentView

**/
OpenAssessment.EditSelfAssessmentView = function(element) {
    this.element = element;
    this.name = "self-assessment";

    // Configure the toggle checkbox to enable/disable this assessment
    new OpenAssessment.ToggleControl(
        this.element,
        "#self_assessment_description_closed",
        "#self_assessment_settings_editor"
    ).install("#include_self_assessment");

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
    TODO
    **/
    validate: function() {
        return this.startDatetimeControl.validate() && this.dueDatetimeControl.validate();
    },

    /**
    TODO
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
    TODO
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
        this.element,
        "#student_training_description_closed",
        "#student_training_settings_editor"
    ).install("#include_student_training");

    this.exampleContainer = new OpenAssessment.Container(
        OpenAssessment.TrainingExample, {
            containerElement: $("#openassessment_training_example_list", this.element).get(0),
            templateElement: $("#openassessment_training_example_template", this.element).get(0),
            addButtonElement: $(".openassessment_add_training_example", this.element).get(0),
            removeButtonClass: "openassessment_training_example_remove",
            containerItemClass: "openassessment_training_example"
        }
    );
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
     Gets the ID of the assessment

     Returns:
     string (CSS ID of the Element object)
     **/
    getID: function() {
        return $(this.element).attr('id');
    },

    /**
    TODO
    **/
    validate: function() {
        return true;
    },

    /**
    TODO
    **/
    validationErrors: function() {
        return [];
    },

    /**
    TODO
    **/
    clearValidationErrors: function() {
    },
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
        this.element,
        "#ai_assessment_description_closed",
        "#ai_assessment_settings_editor"
    ).install("#include_ai_assessment");
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

    /**
    TODO
    **/
    validate: function() {
        return true;
    },

    /**
    TODO
    **/
    validationErrors: function() {
        return [];
    },

    /**
    TODO
    **/
    clearValidationErrors: function() {
    },
};