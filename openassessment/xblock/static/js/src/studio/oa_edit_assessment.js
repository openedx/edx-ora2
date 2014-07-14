/**
Show and hide elements based on a checkbox.

Args:
    element (DOM element): The parent element, used to scope the selectors.
    hiddenSelector (string): The CSS selector string for elements
        to show when the checkbox is in the "off" state.
    shownSelector (string): The CSS selector string for elements
        to show when the checkbox is in the "on" state.
**/
OpenAssessment.ToggleControl = function(element, hiddenSelector, shownSelector) {
    this.element = element;
    this.hiddenSelector = hiddenSelector;
    this.shownSelector = shownSelector;
};

OpenAssessment.ToggleControl.prototype = {
    /**
    Install the event handler for the checkbox,
    passing in the toggle control object as the event data.

    Args:
        checkboxSelector (string): The CSS selector string for the checkbox.

    Returns:
        OpenAssessment.ToggleControl
    **/
    install: function(checkboxSelector) {
        $(checkboxSelector, this.element).change(
            this, function(event) {
                var control = event.data;
                if (this.checked) { control.show(); }
                else { control.hide(); }
            }
        );
        return this;
    },

    show: function() {
        $(this.hiddenSelector, this.element).addClass('is--hidden');
        $(this.shownSelector, this.element).removeClass('is--hidden');
    },

    hide: function() {
        $(this.hiddenSelector, this.element).removeClass('is--hidden');
        $(this.shownSelector, this.element).addClass('is--hidden');
    }
};


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

    new OpenAssessment.ToggleControl(
        this.element,
        "#peer_assessment_description_closed",
        "#peer_assessment_settings_editor"
    ).install("#include_peer_assessment");
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
        datetime (string, optional): If provided, set the datetime to this value.

    Returns:
        string (ISO-formatted UTC datetime)
    **/
    startDatetime: function(datetime) {
        var sel = $("#peer_assessment_start_date", this.element);
        return OpenAssessment.Fields.datetimeField(sel, datetime);
    },

    /**
    Get or set the due date and time of the assessment.

    Args:
        datetime (string, optional): If provided, set the datetime to this value.

    Returns:
        string (ISO-formatted UTC datetime)
    **/
    dueDatetime: function(datetime) {
        var sel = $("#peer_assessment_due_date", this.element);
        return OpenAssessment.Fields.datetimeField(sel, datetime);
    },

    /**
    Gets the ID of the assessment

    Returns:
        string (CSS ID of the Element object)
    **/
    getID: function() {
        return $(this.element).attr('id');
    }
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

    new OpenAssessment.ToggleControl(
        this.element,
        "#self_assessment_description_closed",
        "#self_assessment_settings_editor"
    ).install("#include_self_assessment");
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
        datetime (string, optional): If provided, set the datetime to this value.

    Returns:
        string (ISO-formatted UTC datetime)
    **/
    startDatetime: function(datetime) {
        var sel = $("#self_assessment_start_date", this.element);
        return OpenAssessment.Fields.datetimeField(sel, datetime);
    },

    /**
    Get or set the due date and time of the assessment.

    Args:
        datetime (string, optional): If provided, set the datetime to this value.

    Returns:
        string (ISO-formatted UTC datetime)
    **/
    dueDatetime: function(datetime) {
        var sel = $("#self_assessment_due_date", this.element);
        return OpenAssessment.Fields.datetimeField(sel, datetime);
    },

    /**
     Gets the ID of the assessment

     Returns:
     string (CSS ID of the Element object)
     **/
    getID: function() {
        return $(this.element).attr('id');
    }
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
};

OpenAssessment.EditStudentTrainingView.prototype = {

    /**
    Return a description of the assessment.

    Returns:
        object literal

    Example usage:
    >>> editTrainingView.description();
    {
        examples: "XML DEFINITION HERE"
    }

    **/
    description: function() {
        return {
            examples: this.exampleDefinitions()
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
    Get or set the XML defining the training examples.

    Args:
        xml (string, optional): The XML of the training example definitions.

    Returns:
        string

    **/
    exampleDefinitions: function(xml) {
        var sel = $("#student_training_examples", this.element);
        return OpenAssessment.Fields.stringField(sel, xml);
    },

    /**
     Gets the ID of the assessment

     Returns:
     string (CSS ID of the Element object)
     **/
    getID: function() {
        return $(this.element).attr('id');
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
        examples: "XML DEFINITION HERE"
    }

    **/
    description: function() {
        return {
            examples: this.exampleDefinitions()
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
    }
};