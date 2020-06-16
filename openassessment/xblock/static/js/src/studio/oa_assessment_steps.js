/**
Editing interface for OpenAssessment Assessment Steps.

Args:
    element (DOM element): The DOM element representing this view.
    assessmentViews (object literal): Mapping of CSS IDs to view objects.
    data (Object literal): The data object passed from XBlock backend.

Returns:
    OpenAssessment.EditAssessmentStepsView

**/
OpenAssessment.EditAssessmentStepsView = function(element, assessmentViews, data) {
    var self = this;
    this.settingsElement = element;
    this.assessmentViews = assessmentViews;
    this.data = data;

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

OpenAssessment.EditAssessmentStepsView.prototype = {

    /**
    Installs click listeners which initialize drag and drop functionality for assessment modules.
    **/
    initializeSortableAssessments: function() {
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
            stop: function() {
                $('.openassessment_assessment_module_editor', view.element).show();
            },
            snap: true,
            axis: 'y',
            handle: '.drag-handle',
            cursorAt: {top: 20},
        });
        $('#openassessment_assessment_module_settings_editors .drag-handle', view.element).disableSelection();
    },

    /**
    Helper function that, given a selector element id,
    gets or sets the enabled state of the selector.

    Args:
        settingId(string, required): The identifier of the selector.
        isEnabled(boolean, optional): if provided, enable/disable the setting.
    **/
    settingSelectorEnabled: function(settingId, isEnabled) {
        var sel = $(settingId, this.settingsElement);
        if (isEnabled !== undefined) {
            if (isEnabled) {
                sel.val(1);
            } else {
                sel.val(0);
            }
        }
        return sel.val() === '1';
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
    >>> EditAssessmentStepsView.assessmentsDescription()
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

        $.each(this.assessmentViews, function() {
            errors = errors.concat(this.validationErrors());
        });

        return errors;
    },

    /**
    Clear all validation errors from the UI.
    **/
    clearValidationErrors: function() {
        $.each(this.assessmentViews, function() {
            this.clearValidationErrors();
        });
    },
};
