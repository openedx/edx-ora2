/**
Editing interface for OpenAssessment Schedule.

Args:
    element (DOM element): The DOM element representing this view.
    assessmentViews (object literal): Mapping of CSS IDs to view objects.
    data (Object literal): The data object passed from XBlock backend.

Returns:
    OpenAssessment.EditScheduleView

**/
OpenAssessment.EditScheduleView = function(element, assessmentViews, data) {
    var self = this;
    this.settingsElement = element;
    this.assessmentViews = assessmentViews;
    this.data = data;

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

    function onTeamsEnabledChange(selectedValue) {
        var teamsetElement = $('#openassessment_teamset_selection_wrapper', self.element);

        var selfAssessment = self.assessmentViews.oa_self_assessment_editor;
        var selfAssessmentSchedule = self.assessmentViews.oa_self_assessment_schedule_editor;
        var peerAssessment = self.assessmentViews.oa_peer_assessment_editor;
        var peerAssessmentSchedule = self.assessmentViews.oa_peer_assessment_schedule_editor;
        var trainingAssessment = self.assessmentViews.oa_student_training_editor;
        var staffAssessment = self.assessmentViews.oa_staff_assessment_editor;

        if (!selectedValue || selectedValue === '0') {
            self.setHidden(teamsetElement, true);

            self.setHidden($(selfAssessment.element), false);
            self.setHidden($(selfAssessmentSchedule.element), false);
            self.setHidden($(peerAssessment.element), false);
            self.setHidden($(peerAssessmentSchedule.element), false);
            self.setHidden($(trainingAssessment.element), false);
        } else {
            self.setHidden(teamsetElement, false);

            self.setHidden($(selfAssessment.element), true);
            self.setHidden($(selfAssessmentSchedule.element), true);
            self.setHidden($(peerAssessment.element), true);
            self.setHidden($(peerAssessmentSchedule.element), true);
            self.setHidden($(trainingAssessment.element), true);

            staffAssessment.isEnabled(true);
        }
    }

    this.teamsEnabledSelectControl = new OpenAssessment.SelectControl(
        $('#openassessment_team_enabled_selector', this.element),
        onTeamsEnabledChange,
        new OpenAssessment.Notifier([
            new OpenAssessment.AssessmentToggleListener(),
        ])
    ).install();

    this.initializeSortableAssessments();
    onTeamsEnabledChange($('#openassessment_team_enabled_selector').val());
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
    Enable/disable team assignments.

    Args:
        isEnabled(boolean, optional): if provided, enable/disable team assignments.
    Returns:
        boolean
    **/
    teamsEnabled: function(isEnabled) {
        if (isEnabled !== undefined) {
            this.teamsEnabledSelectControl.change(isEnabled ? '1' : '0');
        }
        return this.settingSelectorEnabled('#openassessment_team_enabled_selector', isEnabled);
    },

    /**
     * Hide elements, including setting the aria-hidden attribute for screen readers.
     *
     * @param {JQuery.selector} selector - The selector matching the elements to hide.
     * @param {boolean} hidden - Whether to hide or show the elements.
     */
    setHidden: function(selector, hidden) {
        selector.toggleClass('is--hidden', hidden);
        selector.attr('aria-hidden', hidden ? 'true' : 'false');
    },

    /**
     * Check whether elements are hidden.
     *
     * @param {JQuery.selector} selector - The selector matching the elements to check.
     * @return {boolean} - True if all the elements are hidden, else false.
     */
    isHidden: function(selector) {
        return selector.hasClass('is--hidden') && selector.attr('aria-hidden') === 'true';
    },

    /**
    Get or set the teamset.

    Args:
        teamset (string, optional): If provided, teams are enabled for the given teamset.

    Returns:
        string (teamset)

    **/
    teamset: function(teamsetIdentifier) {
        if (this.teamsEnabled()) {
            var sel = $('#openassessment_teamset_selector', this.settingsElement);
            if (teamsetIdentifier !== undefined) {
                sel.val(teamsetIdentifier);
            }
            return sel.val();
        }

        return '';
    },

    /**
    Construct a list of enabled assessments and their properties.


    Returns:
        list of object literals representing the assessments.

    Example usage:
    >>> editScheduleView.assessmentsDescription()
    [
        {
            name: "peer-assessment",
            start: "2014-04-01T00:00",
            due: null
            must_grade: 5,
            must_be_graded_by: 2,
        },
        {
            name: "self-assessment",
            start: null,
            due: null
        }
    ]
    **/
    assessmentsDescription: function() {
        var assessmentDescList = [];
        var view = this;

        // Find all assessment modules within our element in the DOM,
        // and append their definitions to the description
        $('.openassessment_assessment_module_settings_editor', this.assessmentsElement).each(
            function() {
                var asmntView = view.assessmentViews[$(this).attr('id')];
                var isVisible = !view.isHidden($(asmntView.element));

                if (asmntView.isEnabled() && isVisible) {
                    var description = asmntView.description();
                    description.name = asmntView.name;
                    assessmentDescList.push(description);
                }
            }
        );
        return assessmentDescList;
    },

    /**
    Retrieve the names of all assessments in the editor,
    in the order that the user defined,
    including assessments that are not currently active.

    Returns:
        list of strings

    **/
    editorAssessmentsOrder: function() {
        var editorAssessments = [];
        var view = this;
        $('.openassessment_assessment_module_settings_editor', this.assessmentsElement).each(
            function() {
                var asmntView = view.assessmentViews[$(this).attr('id')];
                editorAssessments.push(asmntView.name);
            }
        );
        return editorAssessments;
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

        // Validate each of the *enabled* assessment views
        $.each(this.assessmentViews, function() {
            if (this.isEnabled()) {
                isValid = (this.validate() && isValid);
            }
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

        if (this.startDatetimeControl.validationErrors().length > 0) {
            errors.push('Submission start is invalid');
        }
        if (this.dueDatetimeControl.validationErrors().length > 0) {
            errors.push('Submission due is invalid');
        }

        $.each(this.assessmentViews, function() {
            errors = errors.concat(this.validationErrors());
        });

        return errors;
    },

    /**
    Clear all validation errors from the UI.
    **/
    clearValidationErrors: function() {
        this.startDatetimeControl.clearValidationErrors();
        this.dueDatetimeControl.clearValidationErrors();
        $.each(this.assessmentViews, function() {
            this.clearValidationErrors();
        });
    },
};
