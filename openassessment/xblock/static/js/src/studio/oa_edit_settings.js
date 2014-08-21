/**
Editing interface for OpenAssessment settings (including assessments).

Args:
    element (DOM element): The DOM element representing this view.
    assessmentViews (object literal): Mapping of CSS IDs to view objects.

Returns:
    OpenAssessment.EditSettingsView

**/
OpenAssessment.EditSettingsView = function(element, assessmentViews) {
    this.settingsElement = element;
    this.assessmentsElement = $(element).siblings('#openassessment_assessment_module_settings_editors').get(0);
    this.assessmentViews = assessmentViews;

    // Configure the date and time fields
    this.startDatetimeControl = new OpenAssessment.DatetimeControl(
        this.element,
        "#openassessment_submission_start_date",
        "#openassessment_submission_start_time"
    ).install();

    this.dueDatetimeControl = new OpenAssessment.DatetimeControl(
        this.element,
        "#openassessment_submission_due_date",
        "#openassessment_submission_due_time"
    ).install();

    this.leaderboardIntField = new OpenAssessment.IntField(
        $("#openassessment_leaderboard_editor", this.element),
        { min: 0, max: 100 }
    );

    this.initializeSortableAssessments();
};


OpenAssessment.EditSettingsView.prototype = {

    /**
    Installs click listeners which initialize drag and drop functionality for assessment modules.
    **/
    initializeSortableAssessments: function () {
        var view = this;
        // Initialize Drag and Drop of Assessment Modules
        $('#openassessment_assessment_module_settings_editors', view.element).sortable({
            // On Start, we want to collapse all draggable items so that dragging is visually simple (no scrolling)
            start: function(event, ui) {
                // Hide all of the contents (not the headers) of the divs, to collapse during dragging.
                $('.openassessment_assessment_module_editor', view.element).hide();

                // Because of the way that JQuery actively resizes elements during dragging (directly setting
                // the style property), the only way to over come it is to use an important tag ( :( ), or
                // to tell JQuery to set the height to be Automatic (i.e. resize to the minimum nescesary size.)
                // Because all of the information we don't want displayed is now hidden, an auto height will
                // perform the apparent "collapse" that we are looking for in the Placeholder and Helper.
                var targetHeight = 'auto';
                // Shrink the blank area behind the dragged item.
                ui.placeholder.height(targetHeight);
                // Shrink the dragged item itself.
                ui.helper.height(targetHeight);
                // Update the sortable to reflect these changes.
                $('#openassessment_assessment_module_settings_editors', view.element)
                    .sortable('refresh').sortable('refreshPositions');
            },
            // On stop, we redisplay the divs to their original state
            stop: function(event, ui){
                $('.openassessment_assessment_module_editor', view.element).show();
            },
            snap: true,
            axis: "y",
            handle: ".drag-handle",
            cursorAt: {top: 20}
        });
        $('#openassessment_assessment_module_settings_editors .drag-handle', view.element).disableSelection();
    },

    /**
    Get or set the display name of the problem.

    Args:
        name (string, optional): If provided, set the display name.

    Returns:
        string

    **/
    displayName: function(name) {
        var sel = $("#openassessment_title_editor", this.settingsElement);
        return OpenAssessment.Fields.stringField(sel, name);
    },

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
    Enable / disable image submission.

    Args:
        isEnabled (boolean, optional): If provided, enable/disable image submission.

    Returns:
        boolean

    **/
    imageSubmissionEnabled: function(isEnabled) {
        var sel = $("#openassessment_submission_image_editor", this.settingsElement);
        if (isEnabled !== undefined) {
            if (isEnabled) { sel.val(1); }
            else { sel.val(0); }
        }
        return (sel.val() == 1);
    },

    /**
    Enable / disable latex rendering.

    Args: 
        isEnabled(boolean, optional): if provided enable/disable latex rendering
    Returns:
        boolean
    **/
    latexEnabled: function(isEnabled) {
        var sel = $('#openassessment_submission_latex_editor', this.settingsElement);
        if (isEnabled !== undefined) {
            if (isEnabled) {
                sel.val(1);
            } else {
                sel.val(0)
            }
        }
        return (sel.val() == 1);
    },
    /**
    Get or set the number of scores to show in the leaderboard.
    If set to 0, the leaderboard will not be shown.

    Args:
        num (int, optional)

    Returns:
        int

    **/
    leaderboardNum: function(num) {
        if (num !== undefined) {
            this.leaderboardIntField.set(num);
        }
        return this.leaderboardIntField.get(num);
    },

    /**
    Construct a list of enabled assessments and their properties.


    Returns:
        list of object literals representing the assessments.

    Example usage:
    >>> editSettingsView.assessmentsDescription()
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
            function () {
                var asmntView = view.assessmentViews[$(this).attr('id')];
                if (asmntView.isEnabled()) {
                    var description = asmntView.description();
                    description["name"] = asmntView.name;
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
            function () {
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
        isValid = (this.leaderboardIntField.validate() && isValid);

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
            errors.push("Submission start is invalid");
        }
        if (this.dueDatetimeControl.validationErrors().length > 0) {
            errors.push("Submission due is invalid");
        }
        if (this.leaderboardIntField.validationErrors().length > 0) {
            errors.push("Leaderboard number is invalid");
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
        this.leaderboardIntField.clearValidationErrors();
        $.each(this.assessmentViews, function() {
            this.clearValidationErrors();
        });
    },
};