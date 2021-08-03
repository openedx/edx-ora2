import { DatetimeControl } from './oa_edit_fields';
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
    Mark validation errors.

    Returns:
        Boolean indicating whether the view is valid.

    * */
  validate() {
    // Validate the start and due datetime controls
    let isValid = true;

    isValid = (this.startDatetimeControl.validate() && isValid);
    isValid = (this.dueDatetimeControl.validate() && isValid);

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
