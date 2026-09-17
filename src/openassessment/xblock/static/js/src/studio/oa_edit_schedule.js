import { DatetimeControl, SelectControl } from './oa_edit_fields';
import Notifier from './oa_edit_notifier';
/**
Editing interface for OpenAssessment schedule settings.

Args:
    element (DOM element): The DOM element representing this view.

Returns:
    OpenAssessment.EditScheduleView

* */
export class EditScheduleView {
  constructor(element, assessmentViews) {
    this.element = element;
    this.tabElement = $('#oa_edit_schedule_tab');
    this.assessmentViews = assessmentViews;

    this.handleDateTimeConfigChanged = this.handleDateTimeConfigChanged.bind(this);
    this.showSelectedDateConfigSettings = this.showSelectedDateConfigSettings.bind(this);
    this.stashManualDates = this.stashManualDates.bind(this);
    this.popManualDates = this.popManualDates.bind(this);

    // Configure the date and time fields
    this.startDatetimeControl = new DatetimeControl(
      this.element,
      '#openassessment_submission_start_date',
      '#openassessment_submission_start_time',
    ).install();

    this.dueDatetimeControl = new DatetimeControl(
      this.element,
      '#openassessment_submission_due_date',
      '#openassessment_submission_due_time',
    ).install();

    this.selectedDateConfigType = $('input[name="date_config_type"][type="radio"]:checked', this.element).val();

    new SelectControl(
      $('input[name="date_config_type"][type="radio"]', this.element),
      this.handleDateTimeConfigChanged,
      new Notifier([]),
    ).install();
  }

  getTab() {
    return this.tabElement;
  }

  /**
    Get or set the submission start date.

    Args:
        dateString (string, optional): If provided, set the date (YY-MM-DD).
        timeString (string, optional): If provided, set the time (HH:MM, 24-hour clock).

    Returns:
        string (ISO-format UTC datetime)

    * */
  submissionStart(dateString, timeString) {
    return this.startDatetimeControl.datetime(dateString, timeString);
  }

  /**
    Get or set the submission end date.

    Args:
        dateString (string, optional): If provided, set the date (YY-MM-DD).
        timeString (string, optional): If provided, set the time (HH:MM, 24-hour clock).

    Returns:
        string (ISO-format UTC datetime)

    * */
  submissionDue(dateString, timeString) {
    return this.dueDatetimeControl.datetime(dateString, timeString);
  }

  /**
   * Handles the date config selection being changed.
   * "Stashes" the current start and due dates and displays the correct date settings panel.
   *
   * @param {string} value The currently selected date config type, one of [ manual, subsection, course_end ]
   */
  handleDateTimeConfigChanged(value) {
    if (value === 'manual') {
      this.popManualDates();
    } else {
      this.stashManualDates();
    }
    this.showSelectedDateConfigSettings(value);
    this.selectedDateConfigType = value;
  }

  /**
   * Displays the schedule_setting_list entry for the associated date config type and hides the others
   *
   * @param {string} value The currently selected date config type, one of [ manual, subsection, course_end ]
   */
  showSelectedDateConfigSettings(value) {
    $('.schedule_setting_list ', this.element).each((_, el) => {
      if (el.id !== `${value}_schedule_settings_list`) {
        $(el).addClass('is--hidden');
      } else {
        $(el).removeClass('is--hidden');
      }
    });
  }

  /**
   * "Stashes" the current values of all manual start and due date settings and replaces the value of the disabled
   * input elements with default date values.
   *
   * Calling this function once will do the stash, and calling it repeatedly after that will have no effect until
   * `popManualDates` is called
   *
   * This allows us to essentially ignore all date validation for non-manual date config on the backend
   */
  stashManualDates() {
    const defaultStartDate = '2001-01-01';
    const defaultDueDate = '2099-12-31';

    this.startDatetimeControl.stash(defaultStartDate);
    this.dueDatetimeControl.stash(defaultDueDate);

    const peerStep = this.assessmentViews.oa_peer_assessment_editor;
    peerStep.startDatetimeControl.stash(defaultStartDate);
    peerStep.dueDatetimeControl.stash(defaultDueDate);

    const selfStep = this.assessmentViews.oa_self_assessment_editor;
    selfStep.startDatetimeControl.stash(defaultStartDate);
    selfStep.dueDatetimeControl.stash(defaultDueDate);
  }

  /**
   * "Pops" the stashed values of all manual start and due date settings back into the actual input controls.
   *
   * Calling this function once will perform the pop action.
   * Calling it repeatedly after that will have no effect until`stashManualDates` is called again,
   * and if `stashManualDates` has never been called, this function will have no effect.
   */

  popManualDates() {
    this.startDatetimeControl.pop();
    this.dueDatetimeControl.pop();

    const peerStep = this.assessmentViews.oa_peer_assessment_editor;
    peerStep.startDatetimeControl.pop();
    peerStep.dueDatetimeControl.pop();

    const selfStep = this.assessmentViews.oa_self_assessment_editor;
    selfStep.startDatetimeControl.pop();
    selfStep.dueDatetimeControl.pop();
  }

  /**
   * Returns the current date config type
   */
  dateConfigType() {
    return this.selectedDateConfigType;
  }

  /**
  * Returns true if the current date config type is manual
  */
  isManualDateConfig() {
    return this.dateConfigType() === 'manual';
  }

  /**
    Mark validation errors.

    Returns:
        Boolean indicating whether the view is valid.

    * */
  validate() {
    // If we are using a non-manual date config type, don't validate
    // the hidden fields
    if (!this.isManualDateConfig()) {
      return true;
    }

    // Validate the start and due datetime controls
    let isValid = true;

    isValid = this.startDatetimeControl.validate() && isValid;
    isValid = this.dueDatetimeControl.validate() && isValid;

    // Validate assessment dates
    const peerStep = this.assessmentViews.oa_peer_assessment_editor;
    const selfStep = this.assessmentViews.oa_self_assessment_editor;

    if (peerStep.isEnabled()) {
      isValid = peerStep.startDatetimeControl.validate() && isValid;
      isValid = peerStep.dueDatetimeControl.validate() && isValid;
    }

    if (selfStep.isEnabled()) {
      isValid = selfStep.startDatetimeControl.validate() && isValid;
      isValid = selfStep.dueDatetimeControl.validate() && isValid;
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
    const errors = [];

    if (this.startDatetimeControl.validationErrors().length > 0) {
      errors.push('Submission start is invalid');
    }
    if (this.dueDatetimeControl.validationErrors().length > 0) {
      errors.push('Submission due is invalid');
    }

    // Validate assessment step dates
    const peerStep = this.assessmentViews.oa_peer_assessment_editor;
    const selfStep = this.assessmentViews.oa_self_assessment_editor;

    if (peerStep.startDatetimeControl.validationErrors().length > 0) {
      errors.push('Peer assessment start is invalid');
    }
    if (peerStep.dueDatetimeControl.validationErrors().length > 0) {
      errors.push('Peer assessment due is invalid');
    }

    if (selfStep.startDatetimeControl.validationErrors().length > 0) {
      errors.push('Self assessment start is invalid');
    }
    if (selfStep.dueDatetimeControl.validationErrors().length > 0) {
      errors.push('Self assessment due is invalid');
    }
    return errors;
  }

  /**
    Clear all validation errors from the UI.
    * */
  clearValidationErrors() {
    this.startDatetimeControl.clearValidationErrors();
    this.dueDatetimeControl.clearValidationErrors();

    const peerStep = this.assessmentViews.oa_peer_assessment_editor;
    const selfStep = this.assessmentViews.oa_self_assessment_editor;

    peerStep.startDatetimeControl.clearValidationErrors();
    peerStep.dueDatetimeControl.clearValidationErrors();

    selfStep.startDatetimeControl.clearValidationErrors();
    selfStep.dueDatetimeControl.clearValidationErrors();
  }
}

export default EditScheduleView;
