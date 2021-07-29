/* eslint-disable max-classes-per-file */
import Container from './oa_container';
import {
  DatetimeControl,
  Fields,
  IntField,
  ToggleControl,
} from './oa_edit_fields';
import {
  ShowControl,
  TrainingExample,
} from './oa_container_item';
import { AssessmentToggleListener } from './oa_edit_listeners';
import Notifier from './oa_edit_notifier';
/**
 Interface for editing peer assessment settings.

 Args:
 element (DOM element): The DOM element representing this view.
 scheduleElement (DOM element): The DOM element representing EditScheduleView.
 Returns:
 OpenAssessment.EditPeerAssessmentView

 * */

export class EditPeerAssessmentView {
  constructor(element, scheduleElement) {
    this.element = element;
    this.name = 'peer-assessment';
    this.scheduleElement = scheduleElement;

    this.mustGradeField = new IntField(
      $('#peer_assessment_must_grade', this.element),
      { min: 0, max: 99 },
    );
    this.mustBeGradedByField = new IntField(
      $('#peer_assessment_graded_by', this.element),
      { min: 0, max: 99 },
    );

    // Configure the toggle checkbox to enable/disable this assessment and show schedules
    new ToggleControl(
      $('#include_peer_assessment', this.element),
      [
        $('#peer_assessment_settings_editor', this.element),
        $('#peer_assessment_schedule_editor', this.scheduleElement),
      ],
      [],
      new Notifier([
        new AssessmentToggleListener(),
      ]),
    ).install();

    new ShowControl(
      $('#peer_assessment_settings_editor_show_details', this.element),
      $('#peer_assessment_settings_editor_details', this.element),
    ).install();

    // Configure the date and time fields
    this.startDatetimeControl = new DatetimeControl(
      this.scheduleElement,
      '#peer_assessment_start_date',
      '#peer_assessment_start_time',
    ).install();

    this.dueDatetimeControl = new DatetimeControl(
      this.scheduleElement,
      '#peer_assessment_due_date',
      '#peer_assessment_due_time',
    ).install();
  }

  /**
     Return a description of the assessment.

     Returns:
     object literal

     Example usage:
     >>> editPeerView.description();
     {
         must_grade: 5,
         must_be_graded_by: 2,
         enable_flexible_grading: true,
         start: null,
         due: "2014-04-1T00:00"
     }
     * */
  description() {
    return {
      must_grade: this.mustGradeNum(),
      must_be_graded_by: this.mustBeGradedByNum(),
      enable_flexible_grading: this.enableFlexibleGrading(),
      start: this.startDatetime(),
      due: this.dueDatetime(),
    };
  }

  /**
     Get or set whether the assessment is enabled.

     Args:
     isEnabled (boolean, optional): If provided, set the enabled state of the assessment.

     Returns:
     boolean
     ** */
  isEnabled(isEnabled) {
    const sel = $('#include_peer_assessment', this.element);
    return Fields.booleanField(sel, isEnabled);
  }

  /**
     Toggle whether the assessment is enabled or disabled.
     This triggers the actual click event and is mainly useful for testing.
     * */
  toggleEnabled() {
    $('#include_peer_assessment', this.element).click();
  }

  /**
     Get or set the required number of submissions a student must peer-assess.

     Args:
     num (int, optional): If provided, set the required number of assessments.

     Returns:
     int
     * */
  mustGradeNum(num) {
    if (num !== undefined) { this.mustGradeField.set(num); }
    return this.mustGradeField.get();
  }

  /**
     Get or set the required number of peer-assessments a student must receive.

     Args:
     num (int, optional): If provided, set the required number of assessments.

     Returns:
     int
     * */
  mustBeGradedByNum(num) {
    if (num !== undefined) { this.mustBeGradedByField.set(num); }
    return this.mustBeGradedByField.get();
  }

  /**
     Get or set the flexible grading setting to enabled/disabled

     Args:
     enabled (bool, optional): If provided, set `enable_flexible_grading` to the given value

     Returns:
     boolean
     * */
  enableFlexibleGrading(isEnabled) {
    const self = $('#peer_assessment_enable_flexible_grading', this.element);
    if (isEnabled !== undefined) {
      self.val(isEnabled ? '0' : '1');
    }
    return self.val() === '1';
  }

  /**
     Get or set the start date and time of the assessment.

     Args:
     dateString (string, optional): If provided, set the date (YY-MM-DD).
     timeString (string, optional): If provided, set the time (HH:MM, 24-hour clock).

     Returns:
     string (ISO-formatted UTC datetime)
     * */
  startDatetime(dateString, timeString) {
    return this.startDatetimeControl.datetime(dateString, timeString);
  }

  /**
     Get or set the due date and time of the assessment.

     Args:
     dateString (string, optional): If provided, set the date (YY-MM-DD).
     timeString (string, optional): If provided, set the time (HH:MM, 24-hour clock).

     Returns:
     string (ISO-formatted UTC datetime)
     * */
  dueDatetime(dateString, timeString) {
    return this.dueDatetimeControl.datetime(dateString, timeString);
  }

  /**
     Gets the ID of the assessment

     Returns:
     string (CSS ID of the Element object)
     * */
  getID() {
    return $(this.element).attr('id');
  }

  /**
     Mark validation errors.

     Returns:
     Boolean indicating whether the view is valid.

     * */
  validate() {
    const mustGradeValid = this.mustGradeField.validate();
    const mustBeGradedByValid = this.mustBeGradedByField.validate();
    return mustGradeValid && mustBeGradedByValid;
  }

  /**
     Return a list of validation errors visible in the UI.
     Mainly useful for testing.

     Returns:
     list of string

     * */
  validationErrors() {
    const errors = [];
    if (this.mustGradeField.validationErrors().length > 0) {
      errors.push('Peer assessment must grade is invalid');
    }
    if (this.mustBeGradedByField.validationErrors().length > 0) {
      errors.push('Peer assessment must be graded by is invalid');
    }
    return errors;
  }

  /**
     Clear all validation errors from the UI.
     * */
  clearValidationErrors() {
    this.mustGradeField.clearValidationErrors();
    this.mustBeGradedByField.clearValidationErrors();
  }
}

/**
 Interface for editing self assessment settings.

 Args:
 element (DOM element): The DOM element representing this view.

 Returns:
 OpenAssessment.EditSelfAssessmentView

 * */
export class EditSelfAssessmentView {
  constructor(element, scheduleElement) {
    this.element = element;
    this.scheduleElement = scheduleElement;

    this.name = 'self-assessment';

    // Configure the toggle checkbox to enable/disable this assessment
    new ToggleControl(
      $('#include_self_assessment', this.element),
      [
        $('#self_assessment_settings_editor', this.element),
        $('#self_assessment_schedule_editor', this.scheduleElement),
      ],
      [
        $('#self_assessment_description_closed', this.element),
      ],
      new Notifier([
        new AssessmentToggleListener(),
      ]),
    ).install();

    // Configure the date and time fields
    this.startDatetimeControl = new DatetimeControl(
      this.scheduleElement,
      '#self_assessment_start_date',
      '#self_assessment_start_time',
    ).install();

    this.dueDatetimeControl = new DatetimeControl(
      this.scheduleElement,
      '#self_assessment_due_date',
      '#self_assessment_due_time',
    ).install();
  }

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

     * */
  description() {
    return {
      start: this.startDatetime(),
      due: this.dueDatetime(),
    };
  }

  /**
     Get or set whether the assessment is enabled.

     Args:
     isEnabled (boolean, optional): If provided, set the enabled state of the assessment.

     Returns:
     boolean
     ** */
  isEnabled(isEnabled) {
    const sel = $('#include_self_assessment', this.element);
    return Fields.booleanField(sel, isEnabled);
  }

  /**
     Toggle whether the assessment is enabled or disabled.
     This triggers the actual click event and is mainly useful for testing.
     * */
  toggleEnabled() {
    $('#include_self_assessment', this.element).click();
  }

  /**
     Get or set the start date and time of the assessment.

     Args:
     dateString (string, optional): If provided, set the date (YY-MM-DD).
     timeString (string, optional): If provided, set the time (HH:MM, 24-hour clock).

     Returns:
     string (ISO-formatted UTC datetime)
     * */
  startDatetime(dateString, timeString) {
    return this.startDatetimeControl.datetime(dateString, timeString);
  }

  /**
     Get or set the due date and time of the assessment.

     Args:
     dateString (string, optional): If provided, set the date (YY-MM-DD).
     timeString (string, optional): If provided, set the time (HH:MM, 24-hour clock).

     Returns:
     string (ISO-formatted UTC datetime)
     * */
  dueDatetime(dateString, timeString) {
    return this.dueDatetimeControl.datetime(dateString, timeString);
  }

  /**
     Gets the ID of the assessment

     Returns:
     string (CSS ID of the Element object)
     * */
  getID() {
    return $(this.element).attr('id');
  }

  /**
     Mark validation errors. Always true for self assessment.

     Returns:
     Boolean indicating whether the view is valid.

     * */
  validate() {
    return true;
  }

  /**
     Return a list of validation errors visible in the UI.
     Mainly useful for testing.

     Returns:
     list of string

     * */
  validationErrors() {
    return [];
  }

  /**
     Clear all validation errors from the UI.
     * */
  clearValidationErrors() {
    // nothing to clear
  }
}

/**
 Interface for editing student training assessment settings.

 Args:
 element (DOM element): The DOM element representing this view.

 Returns:
 OpenAssessment.EditStudentTrainingView

 * */
export class EditStudentTrainingView {
  constructor(element) {
    this.element = element;
    this.name = 'student-training';

    new ToggleControl(
      $('#include_student_training', this.element),
      [
        $('#student_training_settings_editor', this.element),
      ],
      [],
      new Notifier([
        new AssessmentToggleListener(),
      ]),
    ).install();

    new ShowControl(
      $('#student_training_settings_editor_show_details', this.element),
      $('#student_training_settings_editor_details', this.element),
    ).install();

    this.exampleContainer = new Container(
      TrainingExample, {
        containerElement: $('#openassessment_training_example_list', this.element).get(0),
        templateElement: $('#openassessment_training_example_template', this.element).get(0),
        addButtonElement: $('.openassessment_add_training_example', this.element).get(0),
        removeButtonClass: 'openassessment_training_example_remove',
        containerItemClass: 'openassessment_training_example',
      },
    );

    this.exampleContainer.addEventListeners();
  }

  /**
     Return a description of the assessment.

     Returns:
     object literal

     Example usage:
     >>> editTrainingView.description();
     {
         examples: [
             {
                 answer: ("I love pokemon 1", "I love pokemon 2"),
                 options_selected: [
                     {
                         criterion: "brevity",
                         option: "suberb"
                     },
                     {
                         criterion: "accuracy",
                         option: "alright"
                     }
                     ...
                 ]
             }
     ...
     ]
     }
     * */
  description() {
    return {
      examples: this.exampleContainer.getItemValues(),
    };
  }

  /**
     Get or set whether the assessment is enabled.

     Args:
     isEnabled (boolean, optional): If provided, set the enabled state of the assessment.

     Returns:
     boolean
     ** */
  isEnabled(isEnabled) {
    const sel = $('#include_student_training', this.element);
    return Fields.booleanField(sel, isEnabled);
  }

  /**
     Toggle whether the assessment is enabled or disabled.
     This triggers the actual click event and is mainly useful for testing.
     * */
  toggleEnabled() {
    $('#include_student_training', this.element).click();
  }

  /**
     Gets the ID of the assessment

     Returns:
     string (CSS ID of the Element object)
     * */
  getID() {
    return $(this.element).attr('id');
  }

  /**
     Mark validation errors.

     Returns:
     Boolean indicating whether the view is valid.

     * */
  validate() {
    let isValid = true;

    $.each(this.exampleContainer.getAllItems(), function () {
      isValid = this.validate() && isValid;
    });

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
    $.each(this.exampleContainer.getAllItems(), function () {
      errors = errors.concat(this.validationErrors());
    });
    return errors;
  }

  /**
     Clear all validation errors from the UI.
     * */
  clearValidationErrors() {
    $.each(this.exampleContainer.getAllItems(), function () {
      this.clearValidationErrors();
    });
  }

  /**
     Adds a new training example by copying the training example template.
     Primarily used for testing.
     * */
  addTrainingExample() {
    this.exampleContainer.add();
  }
}

/**
 * Interface for editing staff assessment settings.
 *
 * @param {Object} element - The DOM element representing this view.
 * @constructor
 *
 */
export class EditStaffAssessmentView {
  constructor(element) {
    this.element = element;
    this.name = 'staff-assessment';

    // Configure the toggle checkbox to enable/disable this assessment
    new ToggleControl(
      $('#include_staff_assessment', this.element),
      [
        $('#staff_assessment_description', this.element),
      ],
      [
        $('#staff_assessment_description', this.element),
      ], // open and closed selectors are the same!
      new Notifier([
        new AssessmentToggleListener(),
      ]),
    ).install();
  }

  /**
     * Return a description of the assessment.
     *
     * @return {Object} Representation of the view.
     */
  description() {
    return {
      required: this.isEnabled(),
    };
  }

  /**
     * Get or set whether the assessment is enabled.
     *
     * @param {Boolean} isEnabled - If provided, set the enabled state of the assessment.
     * @return {Boolean}
     */
  isEnabled(isEnabled) {
    const sel = $('#include_staff_assessment', this.element);
    return Fields.booleanField(sel, isEnabled);
  }

  /**
     * Toggle whether the assessment is enabled or disabled.
     * This triggers the actual click event and is mainly useful for testing.
     */
  toggleEnabled() {
    $('#include_staff_assessment', this.element).click();
  }

  /**
     * Gets the ID of the assessment
     *
     * @return {String} CSS class of the Element object
     */
  getID() {
    return $(this.element).attr('id');
  }

  /**
     * Mark validation errors.
     *
     * @return {Boolean} Whether the view is valid.
     *
     */
  validate() {
    return true; // Nothing to validate, the only input is a boolean and either state is valid
  }

  /**
     * Return a list of validation errors visible in the UI.
     * Mainly useful for testing.
     *
     * @return {Array} - always empty, function called but not actually used.
     */
  validationErrors() {
    return [];
  }

  /**
     * Clear all validation errors from the UI.
     */
  clearValidationErrors() {
    // do nothing
  }
}
