/**
Editing interface for OpenAssessment schedule settings.

Args:
    element (DOM element): The DOM element representing this view.

Returns:
    OpenAssessment.EditScheduleView

**/
OpenAssessment.EditScheduleView = function(element) {
    this.element = element;

    // Configure the date and time fields
    this.startDatetimeControl = new OpenAssessment.DatetimeControl(
        this.element,
        '#openassessment_submission_start_date',
        '#openassessment_submission_start_time'
    ).install();

    this.dueDatetimeControl = new OpenAssessment.DatetimeControl(
        this.element,
        '#openassessment_submission_due_date',
        '#openassessment_submission_due_time'
    ).install();
};

OpenAssessment.EditScheduleView.prototype = {
    /**
    Get or set the submission start date.

    Args:
        dateString (string, optional): If provided, set the date (YY-MM-DD).
        timeString (string, optional): If provided, set the time (HH:MM, 24-hour clock).

    Returns:
        string (ISO-format UTC datetime)

    **/
    submissionStart: function(dateString, timeString) {
        return this.startDatetimeControl.datetime(dateString, timeString);
    },

    /**
    Get or set the submission end date.

    Args:
        dateString (string, optional): If provided, set the date (YY-MM-DD).
        timeString (string, optional): If provided, set the time (HH:MM, 24-hour clock).

    Returns:
        string (ISO-format UTC datetime)

    **/
    submissionDue: function(dateString, timeString) {
        return this.dueDatetimeControl.datetime(dateString, timeString);
    },

    /**
    Mark validation errors.

    Returns:
        Boolean indicating whether the view is valid.

    **/
    validate: function() {
        // Validate the start and due datetime controls
        var isValid = true;

        isValid = (this.startDatetimeControl.validate() && isValid);
        isValid = (this.dueDatetimeControl.validate() && isValid);

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

        if (this.startDatetimeControl.validationErrors().length > 0) {
            errors.push('Submission start is invalid');
        }
        if (this.dueDatetimeControl.validationErrors().length > 0) {
            errors.push('Submission due is invalid');
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
