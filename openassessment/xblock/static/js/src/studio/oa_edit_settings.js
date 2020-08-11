/**
Editing interface for OpenAssessment settings.

Args:
    element (DOM element): The DOM element representing this view.
    assessmentViews (object literal): Mapping of CSS IDs to view objects.
    data (Object literal): The data object passed from XBlock backend.

Returns:
    OpenAssessment.EditSettingsView

**/
OpenAssessment.EditSettingsView = function(element, assessmentViews, data) {
    var self = this;
    this.settingsElement = element;
    this.assessmentViews = assessmentViews;

    new OpenAssessment.SelectControl(
        $('#openassessment_submission_file_upload_response', this.element),
        function(selectedValue) {
            var el = $('#openassessment_submission_file_upload_type_wrapper', self.element);
            if (!selectedValue) {
                el.addClass('is--hidden');
            } else {
                el.removeClass('is--hidden');
            }
        },
        new OpenAssessment.Notifier([
            new OpenAssessment.AssessmentToggleListener(),
        ])
    ).install();

    new OpenAssessment.SelectControl(
        $('#openassessment_submission_upload_selector', this.element),
        {'custom': $('#openassessment_submission_white_listed_file_types_wrapper', this.element)},
        new OpenAssessment.Notifier([
            new OpenAssessment.AssessmentToggleListener(),
        ])
    ).install();

    function onTeamsEnabledChange(selectedValue) {
        var teamsetElement = $('#openassessment_teamset_selection_wrapper', self.element);

        var selfAssessment = self.assessmentViews.oa_self_assessment_editor;
        var peerAssessment = self.assessmentViews.oa_peer_assessment_editor;
        var trainingAssessment = self.assessmentViews.oa_student_training_editor;
        var staffAssessment = self.assessmentViews.oa_staff_assessment_editor;

        if (!selectedValue || selectedValue === '0') {
            self.setHidden(teamsetElement, true);

            self.setHidden($(selfAssessment.element), false);
            self.setHidden($(peerAssessment.element), false);
            self.setHidden($(trainingAssessment.element), false);

            if (selfAssessment.isEnabled()) {
                self.setHidden($('#self_assessment_schedule_editor', selfAssessment.scheduleElement), false);
            }
            if (peerAssessment.isEnabled()) {
                self.setHidden($('#peer_assessment_schedule_editor', peerAssessment.scheduleElement), false);
            }
        } else {
            self.setHidden(teamsetElement, false);

            self.setHidden($(selfAssessment.element), true);
            self.setHidden($(peerAssessment.element), true);
            self.setHidden($(trainingAssessment.element), true);

            self.setHidden($('#self_assessment_schedule_editor', selfAssessment.scheduleElement), true);
            self.setHidden($('#peer_assessment_schedule_editor', peerAssessment.scheduleElement), true);

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

    this.leaderboardIntField = new OpenAssessment.IntField(
        $('#openassessment_leaderboard_editor', this.element),
        {min: 0, max: 100}
    );

    this.fileTypeWhiteListInputField = new OpenAssessment.InputControl(
        $('#openassessment_submission_white_listed_file_types', this.element),
        function(value) {
            var badExts = [];
            var errors = [];
            if (!value) {
                errors.push(gettext('File types can not be empty.'));
                return errors;
            }
            var whiteList = $.map(value.replace(/\./g, '').toLowerCase().split(','), $.trim);
            $.each(whiteList, function(index, ext) {
                if (data.FILE_EXT_BLACK_LIST.indexOf(ext) !== -1) {
                    badExts.push(ext);
                }
            });
            if (badExts.length) {
                errors.push(gettext('The following file types are not allowed: ') + badExts.join(','));
            }

            return errors;
        }
    );

    onTeamsEnabledChange($('#openassessment_team_enabled_selector').val());
};

OpenAssessment.EditSettingsView.prototype = {
    /**
    Get or set the display name of the problem.

    Args:
        name (string, optional): If provided, set the display name.

    Returns:
        string

    **/
    displayName: function(name) {
        var sel = $('#openassessment_title_editor', this.settingsElement);
        return OpenAssessment.Fields.stringField(sel, name);
    },

    /**
     Get or set text response necessity.

    Args:
        value (string, optional): If provided, set text response necessity.

    Returns:
        string ('required', 'optional' or '')
     */
    textResponseNecessity: function(value) {
        var sel = $('#openassessment_submission_text_response', this.settingsElement);
        if (value !== undefined) {
            sel.val(value);
        }
        return sel.val();
    },

    /**
     Get or set file upload necessity.

    Args:
        value (string, optional): If provided, set file upload necessity.

    Returns:
        string ('required', 'optional' or '')
     */
    fileUploadResponseNecessity: function(value, triggerChange) {
        var sel = $('#openassessment_submission_file_upload_response', this.settingsElement);
        if (value !== undefined) {
            triggerChange = triggerChange || false;
            sel.val(value);
            if (triggerChange) {
                $(sel).trigger('change');
            }
        }
        return sel.val();
    },

    /**
    Get or set upload file type.

    Args:
        uploadType (string, optional): If provided, enable specified upload type submission.

    Returns:
        string (image, file or custom)

    **/
    fileUploadType: function(uploadType) {
        var fileUploadTypeWrapper = $('#openassessment_submission_file_upload_type_wrapper', this.settingsElement);
        var fileUploadAllowed = !$(fileUploadTypeWrapper).hasClass('is--hidden');
        if (fileUploadAllowed) {
            var sel = $('#openassessment_submission_upload_selector', this.settingsElement);
            if (uploadType !== undefined) {
                sel.val(uploadType);
            }
            return sel.val();
        }

        return '';
    },

    /**
    Get or set upload file extension white list.

    Args:
        exts (string, optional): If provided, set the file extension white list

    Returns:
        string: comma separated file extension white list string
    **/
    fileTypeWhiteList: function(exts) {
        if (exts !== undefined) {
            this.fileTypeWhiteListInputField.set(exts);
        }
        return this.fileTypeWhiteListInputField.get();
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
    Enable / disable latex rendering.

    Args:
        isEnabled(boolean, optional): if provided enable/disable latex rendering
    Returns:
        boolean
    **/
    latexEnabled: function(isEnabled) {
        return this.settingSelectorEnabled('#openassessment_submission_latex_editor', isEnabled);
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
     * Check whether elements are hidden.
     *
     * @param {JQuery.selector} selector - The selector matching the elements to check.
     * @return {boolean} - True if all the elements are hidden, else false.
     */
    isHidden: function(selector) {
        return selector.hasClass('is--hidden') && selector.attr('aria-hidden') === 'true';
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
    Mark validation errors.

    Returns:
        Boolean indicating whether the view is valid.

    **/
    validate: function() {
        // Validate the start and due datetime controls
        var isValid = true;

        isValid = (this.leaderboardIntField.validate() && isValid);
        if (this.fileUploadType() === 'custom') {
            isValid = (this.fileTypeWhiteListInputField.validate() && isValid);
        } else {
            // we want to keep the valid white list in case author changes upload type back to custom
            if (this.fileTypeWhiteListInputField.get() && !this.fileTypeWhiteListInputField.validate()) {
                // but will clear the field in case it is invalid
                this.fileTypeWhiteListInputField.set('');
            }
        }

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

        if (this.leaderboardIntField.validationErrors().length > 0) {
            errors.push('Leaderboard number is invalid');
        }
        if (this.fileTypeWhiteListInputField.validationErrors().length > 0) {
            errors = errors.concat(this.fileTypeWhiteListInputField.validationErrors());
        }

        return errors;
    },

    /**
    Clear all validation errors from the UI.
    **/
    clearValidationErrors: function() {
        this.leaderboardIntField.clearValidationErrors();
        this.fileTypeWhiteListInputField.clearValidationErrors();
    },
};
