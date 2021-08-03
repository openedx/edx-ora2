import {
  Fields,
  InputControl,
  IntField,
  SelectControl,
} from './oa_edit_fields';
import Notifier from './oa_edit_notifier';
import { AssessmentToggleListener } from './oa_edit_listeners';

/**
Editing interface for OpenAssessment settings.

Args:
    element (DOM element): The DOM element representing this view.
    assessmentViews (object literal): Mapping of CSS IDs to view objects.
    data (Object literal): The data object passed from XBlock backend.

Returns:
    OpenAssessment.EditSettingsView

* */
export class EditSettingsView {
  constructor(element, assessmentViews, data) {
    this.settingsElement = element;
    this.tabElement = $('#oa_edit_settings_tab');
    this.assessmentViews = assessmentViews;
    this.data = data;

    this.onFileUploadTypeChanged = this.onFileUploadTypeChanged.bind(this);
    this.onTeamsEnabledChange = this.onTeamsEnabledChange.bind(this);
    this.displayName = this.displayName.bind(this);
    this.textResponseNecessity = this.textResponseNecessity.bind(this);
    this.textResponseEditor = this.textResponseEditor.bind(this);
    this.fileUploadResponseNecessity = this.fileUploadResponseNecessity.bind(this);
    this.fileUploadType = this.fileUploadType.bind(this);
    this.fileTypeWhiteList = this.fileTypeWhiteList.bind(this);
    this.settingSelectorEnabled = this.settingSelectorEnabled.bind(this);
    this.multipleFilesEnabled = this.multipleFilesEnabled.bind(this);
    this.latexEnabled = this.latexEnabled.bind(this);
    this.teamsEnabled = this.teamsEnabled.bind(this);
    this.isHidden = this.isHidden.bind(this);
    this.setHidden = this.setHidden.bind(this);
    this.teamset = this.teamset.bind(this);
    this.leaderboardNum = this.leaderboardNum.bind(this);
    this.validate = this.validate.bind(this);
    this.validationErrors = this.validationErrors.bind(this);
    this.clearValidationErrors = this.clearValidationErrors.bind(this);

    new SelectControl(
      $('#openassessment_submission_file_upload_response', this.element),
      (selectedValue) => {
        const el = $('#openassessment_submission_file_upload_type_wrapper', this.element);
        const uploadType = $('#openassessment_submission_upload_selector', this.element).val();

        if (!selectedValue) {
          el.addClass('is--hidden');
        } else {
          el.removeClass('is--hidden');
          // trigger refresh of file upload type to load extension list
          this.onFileUploadTypeChanged(uploadType);
        }
      },
      new Notifier([new AssessmentToggleListener()]),
    ).install();

    new SelectControl(
      $('#openassessment_submission_upload_selector', this.element),
      this.onFileUploadTypeChanged,
      new Notifier([new AssessmentToggleListener()]),
    ).install();

    this.teamsEnabledSelectControl = new SelectControl(
      $('#openassessment_team_enabled_selector', this.element),
      this.onTeamsEnabledChange,
      new Notifier([
        new AssessmentToggleListener(),
      ]),
    ).install();

    this.leaderboardIntField = new IntField(
      $('#openassessment_leaderboard_editor', this.element),
      { min: 0, max: 100 },
    );

    this.fileTypeWhiteListInputField = new InputControl(
      $('#openassessment_submission_white_listed_file_types', this.element),
      ((value) => {
        const badExts = [];
        const errors = [];
        if (!value) {
          errors.push(gettext('File types can not be empty.'));
          return errors;
        }
        const whiteList = $.map(value.replace(/\./g, '').toLowerCase().split(','), $.trim);
        $.each(whiteList, (index, ext) => {
          if (this.data.FILE_EXT_BLACK_LIST.indexOf(ext) !== -1) {
            badExts.push(ext);
          }
        });
        if (badExts.length) {
          errors.push(gettext('The following file types are not allowed: ') + badExts.join(','));
        }

        return errors;
      }),
    );

    this.onTeamsEnabledChange($('#openassessment_team_enabled_selector').val());
  }

  getTab() {
    return this.tabElement;
  }

  /**
   * When file upload type is changed, show the corresponding extensions that will be
   * allowed for upload
   * @param {String} selectedValue
   */
  onFileUploadTypeChanged(selectedValue) {
    const el = $(
      '#openassessment_submission_white_listed_file_types',
      this.element,
    );
    const extNote = $(
      '#openassessment_submission_white_listed_file_types_wrapper .extension-warning',
      this.element,
    );

    this.fileTypeWhiteListInputField.clearValidationErrors();

    if (selectedValue === 'custom') {
      // Enable the "allowed file types" field and hide the note banner
      el.prop('disabled', false);
      this.setHidden(extNote, true);
    } else {
      // Fill, but disable, the "allowed file types" field and show the note banner
      if (selectedValue === 'image') {
        el.val(this.data.ALLOWED_IMAGE_EXTENSIONS.join(', '));
      } else if (selectedValue === 'pdf-and-image') {
        el.val(this.data.ALLOWED_FILE_EXTENSIONS.join(', '));
      }

      el.prop('disabled', true);
      this.setHidden(extNote, false);
    }
  }

  onTeamsEnabledChange(selectedValue) {
    const teamsetElement = $('#openassessment_teamset_selection_wrapper', this.element);
    const multipleFilesElement = $('#openassessment_submission_nfile_editor', this.element);

    const selfAssessment = this.assessmentViews.oa_self_assessment_editor;
    const peerAssessment = this.assessmentViews.oa_peer_assessment_editor;
    const trainingAssessment = this.assessmentViews.oa_student_training_editor;
    const staffAssessment = this.assessmentViews.oa_staff_assessment_editor;

    if (!selectedValue || selectedValue === '0') {
      this.setHidden(teamsetElement, true);

      this.setHidden($(selfAssessment.element), false);
      this.setHidden($(peerAssessment.element), false);
      this.setHidden($(trainingAssessment.element), false);

      if (selfAssessment.isEnabled()) {
        this.setHidden($('#self_assessment_schedule_editor', selfAssessment.scheduleElement), false);
      }
      if (peerAssessment.isEnabled()) {
        this.setHidden($('#peer_assessment_schedule_editor', peerAssessment.scheduleElement), false);
      }

      this.setHidden($('#openassessment_leaderboard_wrapper .disabled-label'), true);
      this.setHidden($('#openassessment_leaderboard_wrapper .teams-warning'), true);
      $('#openassessment_leaderboard_editor').prop('disabled', false);
      multipleFilesElement.prop('disabled', false);
    } else {
      this.setHidden(teamsetElement, false);

      this.setHidden($(selfAssessment.element), true);
      this.setHidden($(peerAssessment.element), true);
      this.setHidden($(trainingAssessment.element), true);

      this.setHidden($('#self_assessment_schedule_editor', selfAssessment.scheduleElement), true);
      this.setHidden($('#peer_assessment_schedule_editor', peerAssessment.scheduleElement), true);

      this.setHidden($('#openassessment_leaderboard_wrapper .disabled-label'), false);
      this.setHidden($('#openassessment_leaderboard_wrapper .teams-warning'), false);
      $('#openassessment_leaderboard_editor').prop('disabled', true);
      staffAssessment.isEnabled(true);

      multipleFilesElement.prop('disblaed', true);
      multipleFilesElement.val(1);
    }
  }

  /**
    Get or set the display name of the problem.

    Args:
        name (string, optional): If provided, set the display name.

    Returns:
        string

    * */
  displayName(name) {
    const sel = $('#openassessment_title_editor', this.settingsElement);
    return Fields.stringField(sel, name);
  }

  /**
     Get or set text response necessity.

    Args:
        value (string, optional): If provided, set text response necessity.

    Returns:
        string ('required', 'optional' or '')
     */
  textResponseNecessity(value) {
    const sel = $('#openassessment_submission_text_response', this.settingsElement);
    if (value !== undefined) {
      sel.val(value);
    }
    return sel.val();
  }

  /**
     Get or set response editor.

    Args:
        value (string, optional): If provided, set text response necessity.

    Returns:
        string: One of available response editors
     */
  textResponseEditor(value) {
    const sel = $('#openassessment_submission_text_response_editor', this.settingsElement);
    if (value !== undefined) {
      sel.val(value);
    }
    return sel.val();
  }

  /**
     Get or set file upload necessity.

    Args:
        value (string, optional): If provided, set file upload necessity.

    Returns:
        string ('required', 'optional' or '')
     */
  /* eslint "no-param-reassign": 0 */
  fileUploadResponseNecessity(value, triggerChange) {
    const sel = $('#openassessment_submission_file_upload_response', this.settingsElement);
    if (value !== undefined) {
      triggerChange = triggerChange || false;
      sel.val(value);
      if (triggerChange) {
        $(sel).trigger('change');
      }
    }
    return sel.val();
  }

  /**
    Get or set upload file type.

    Args:
        uploadType (string, optional): If provided, enable specified upload type submission.

    Returns:
        string (image, file or custom)

    * */
  fileUploadType(uploadType) {
    const fileUploadTypeWrapper = $(
      '#openassessment_submission_file_upload_type_wrapper',
      this.settingsElement,
    );
    const fileUploadAllowed = !$(fileUploadTypeWrapper).hasClass('is--hidden');
    if (fileUploadAllowed) {
      const sel = $(
        '#openassessment_submission_upload_selector',
        this.settingsElement,
      );
      if (uploadType !== undefined) {
        sel.val(uploadType);
      }
      $(sel).trigger('change');
      return sel.val();
    }

    return '';
  }

  /**
    Get or set upload file extension white list.

    Args:
        exts (string, optional): If provided, set the file extension white list

    Returns:
        string: comma separated file extension white list string
    * */
  fileTypeWhiteList(exts) {
    if (exts !== undefined) {
      this.fileTypeWhiteListInputField.set(exts);
    }
    return this.fileTypeWhiteListInputField.get();
  }

  /**
    Helper function that, given a selector element id,
    gets or sets the enabled state of the selector.

    Args:
        settingId(string, required): The identifier of the selector.
        isEnabled(boolean, optional): if provided, enable/disable the setting.
    * */
  settingSelectorEnabled(settingId, isEnabled) {
    const sel = $(settingId, this.settingsElement);
    if (isEnabled !== undefined) {
      if (isEnabled) {
        sel.val(1);
      } else {
        sel.val(0);
      }
    }
    return sel.val() === '1';
  }

  /**
  Enable / disable multiple files upload

  Args:
      isEnabled(boolean, optional): if provided enable/disable multiple files upload
  Returns:
      boolean
  * */
  multipleFilesEnabled(isEnabled) {
    return this.settingSelectorEnabled('#openassessment_submission_nfile_editor', isEnabled);
  }

  /**
    Enable / disable latex rendering.

    Args:
        isEnabled(boolean, optional): if provided enable/disable latex rendering
    Returns:
        boolean
    * */
  latexEnabled(isEnabled) {
    return this.settingSelectorEnabled('#openassessment_submission_latex_editor', isEnabled);
  }

  /**
    Enable/disable team assignments.

    Args:
        isEnabled(boolean, optional): if provided, enable/disable team assignments.
    Returns:
        boolean
    * */
  teamsEnabled(isEnabled) {
    if (isEnabled !== undefined) {
      this.teamsEnabledSelectControl.change(isEnabled ? '1' : '0');
    }
    return this.settingSelectorEnabled('#openassessment_team_enabled_selector', isEnabled);
  }

  /**
     * Check whether elements are hidden.
     *
     * @param {JQuery.selector} selector - The selector matching the elements to check.
     * @return {boolean} - True if all the elements are hidden, else false.
     */
  isHidden(selector) {
    return selector.hasClass('is--hidden') && selector.attr('aria-hidden') === 'true';
  }

  /**
     * Hide elements, including setting the aria-hidden attribute for screen readers.
     *
     * @param {JQuery.selector} selector - The selector matching the elements to hide.
     * @param {boolean} hidden - Whether to hide or show the elements.
     */
  setHidden(selector, hidden) {
    selector.toggleClass('is--hidden', hidden);
    selector.attr('aria-hidden', hidden ? 'true' : 'false');
  }

  /**
    Get or set the teamset.

    Args:
        teamset (string, optional): If provided, teams are enabled for the given teamset.

    Returns:
        string (teamset)

    * */
  teamset(teamsetIdentifier) {
    if (this.teamsEnabled()) {
      const sel = $('#openassessment_teamset_selector', this.settingsElement);
      if (teamsetIdentifier !== undefined) {
        sel.val(teamsetIdentifier);
      }
      return sel.val();
    }

    return '';
  }

  /**
    Get or set the number of scores to show in the leaderboard.
    If set to 0, the leaderboard will not be shown.

    Args:
        num (int, optional)

    Returns:
        int

    * */
  leaderboardNum(num) {
    if (num !== undefined) {
      this.leaderboardIntField.set(num);
    }
    return this.leaderboardIntField.get(num);
  }

  /**
    Enable / disable showing learners the assessment rubric while working on their response.

    Args:
        isEnabled(boolean, optional): if provided enable/disable showing the rubric
    Returns:
        boolean
     * */
  showRubricDuringResponse(isEnabled) {
    return this.settingSelectorEnabled('#openassessment_show_rubric_during_response_selector', isEnabled);
  }

  /**
    Mark validation errors.

    Returns:
        Boolean indicating whether the view is valid.

    * */
  validate() {
    // Validate the start and due datetime controls
    let isValid = true;

    isValid = (this.leaderboardIntField.validate() && isValid);
    if (this.fileUploadType() === 'custom') {
      isValid = (this.fileTypeWhiteListInputField.validate() && isValid);
    } else {
      // we want to keep the valid white list in case author changes upload type back to custom
      /* eslint-disable-next-line no-lonely-if */
      if (this.fileTypeWhiteListInputField.get() && !this.fileTypeWhiteListInputField.validate()) {
        // but will clear the field in case it is invalid
        this.fileTypeWhiteListInputField.set('');
      }
    }

    return isValid;
  }

  /**
    Return a list of validation errors visible in the UI.
    Mainly useful for testing.

    Returns:
        list of string

    * */
  validationErrors() {
    let errors = [];

    if (this.leaderboardIntField.validationErrors().length > 0) {
      errors.push('Leaderboard number is invalid');
    }
    if (this.fileTypeWhiteListInputField.validationErrors().length > 0) {
      errors = errors.concat(this.fileTypeWhiteListInputField.validationErrors());
    }

    return errors;
  }

  /**
    Clear all validation errors from the UI.
    * */
  clearValidationErrors() {
    this.leaderboardIntField.clearValidationErrors();
    this.fileTypeWhiteListInputField.clearValidationErrors();
  }
}

export default EditSettingsView;
