import ValidationAlert from './oa_edit_validation_alert';
import EditPromptsView from './oa_edit_prompts';
import EditRubricView from './oa_edit_rubric';
import EditScheduleView from './oa_edit_schedule';
import Notifier from './oa_edit_notifier';
import {
  EditSelfAssessmentView,
  EditStaffAssessmentView,
  EditStudentTrainingView,
  EditPeerAssessmentView,
} from './oa_edit_assessment';
import EditAssessmentsStepsView from './oa_edit_assessments_steps';
import EditSettingsView from './oa_edit_settings';
import Server from '../oa_server';
import { StudentTrainingListener } from './oa_edit_listeners';
/**
 Interface for editing view in Studio.
 The constructor initializes the DOM for editing.

 Args:
 runtime (Runtime): an XBlock runtime instance.
 element (DOM element): The DOM element representing this XBlock.
 server (OpenAssessment.Server): The interface to the XBlock server.
 data (Object literal): The data object passed from XBlock backend.

 Returns:
 OpenAssessment.StudioView
 * */

export class StudioView {
  constructor(runtime, element, server, data) {
    this.element = element;
    this.runtime = runtime;
    this.server = server;
    this.data = data;

    // Resize the editing modal
    this.fixModalHeight();

    // Initializes the tabbing functionality and activates the last used.
    this.initializeTabs();

    // Initialize the validation alert
    this.alert = new ValidationAlert().install();

    const studentTrainingListener = new StudentTrainingListener();

    // Initialize the prompt tab view
    this.promptsView = new EditPromptsView(
      $('#oa_prompts_editor_wrapper', this.element).get(0),
      new Notifier([
        studentTrainingListener,
      ]),
    );

    // Initialize the rubric tab view
    this.rubricView = new EditRubricView(
      $('#oa_rubric_editor_wrapper', this.element).get(0),
      new Notifier([
        studentTrainingListener,
      ]),
      this.server,
    );

    // Initialize the settings and assessments steps tab views
    const staffAssessmentView = new EditStaffAssessmentView(
      $('#oa_staff_assessment_editor', this.element).get(0),
    );
    const studentTrainingView = new EditStudentTrainingView(
      $('#oa_student_training_editor', this.element).get(0),
    );
    const peerAssessmentView = new EditPeerAssessmentView(
      $('#oa_peer_assessment_editor', this.element).get(0),
      $('#oa_schedule_editor_wrapper', this.element).get(0),
    );
    const selfAssessmentView = new EditSelfAssessmentView(
      $('#oa_self_assessment_editor', this.element).get(0),
      $('#oa_schedule_editor_wrapper', this.element).get(0),
    );
    const assessmentLookupDictionary = {};
    assessmentLookupDictionary[staffAssessmentView.getID()] = staffAssessmentView;
    assessmentLookupDictionary[studentTrainingView.getID()] = studentTrainingView;
    assessmentLookupDictionary[peerAssessmentView.getID()] = peerAssessmentView;
    assessmentLookupDictionary[selfAssessmentView.getID()] = selfAssessmentView;

    this.assessmentsStepsView = new EditAssessmentsStepsView(
      $('#oa_assessment_steps_editor_wrapper', this.element).get(0), assessmentLookupDictionary,
    );

    this.settingsView = new EditSettingsView(
      $('#oa_basic_settings_editor', this.element).get(0), assessmentLookupDictionary, data,
    );

    // Initialize the schedule tab
    this.scheduleView = new EditScheduleView(
      $('#oa_schedule_editor_wrapper', this.element).get(0), assessmentLookupDictionary,
    );

    // list all views in tab order for easy iteration, e.g. validation
    this.views = [
      this.promptsView,
      this.rubricView,
      this.scheduleView,
      this.assessmentsStepsView,
      this.settingsView,
    ];

    // Install the save and cancel buttons
    $('.openassessment_save_button', this.element).click($.proxy(this.save, this));
    $('.openassessment_cancel_button', this.element).click($.proxy(this.cancel, this));
  }

  /**
     Adjusts the modal's height, position and padding to be larger for OA editing only (Does not impact other modals)
     * */
  fixModalHeight() {
    // Add the full height class to every element from the XBlock
    // to the modal window in Studio.
    $(this.element)
      .addClass('openassessment_full_height')
      .parentsUntil('.modal-window')
      .addClass('openassessment_full_height');

    // Add the modal window class to the modal window
    $(this.element)
      .closest('.modal-window')
      .addClass('openassessment_modal_window');
  }

  /**
     Initializes the tabs that seperate the sections of the editor.

     Because this function relies on the OpenAssessment Name space, the tab that it first
     active will be the one that the USER was presented with, regardless of which editor they
     were using.  I.E.  If I leave Editor A in the settings state, and enter editor B, editor B
     will automatically open with the settings state.

     * */
  initializeTabs() {
    // If this is the first editor that the user has opened, default to the prompt view.
    if (typeof (this.lastOpenEditingTab) === 'undefined') {
      this.lastOpenEditingTab = 0;
    }
    // Initialize JQuery UI Tabs, and activates the appropriate tab.
    $('.openassessment_editor_content_and_tabs', this.element).tabs({
      active: this.lastOpenEditingTab,
    });
  }

  /**
     Saves the state of the editing tabs in a variable outside of the scope of the editor.
     When the user reopens the editing view, they will be greeted by the same tab that they left.
     This code is called by the two paths that we could exit the modal through: Saving and canceling.
     * */
  saveTabState() {
    const tabElement = $('.openassessment_editor_content_and_tabs', this.element);
    this.lastOpenEditingTab = tabElement.tabs('option', 'active');
  }

  /**
     Save the problem's XML definition to the server.
     If the problem has been released, make the user confirm the save.
     * */
  save() {
    this.saveTabState();

    // Perform client-side validation:
    // * Clear errors from any field marked as invalid.
    // * Mark invalid fields in the UI.
    // * If there are any validation errors, show an alert.
    //
    // The `validate()` method calls `validate()` on any subviews,
    // so that each subview has the opportunity to validate
    // its fields. It returns tabs which fail validation.
    this.clearValidationErrors();
    const viewsFailingValidation = this.validate();
    this.markTabsWithValidationErrors(viewsFailingValidation);

    if (viewsFailingValidation.length > 0) {
      const tabNames = viewsFailingValidation.map(view => view.getTab().find('a').text());
      this.alert.setMessage(
        gettext('Save Unsuccessful'),
        gettext(`We've detected errors on the following tabs: ${tabNames.join(', ')}`),
      ).show();
    } else {
      // At this point, we know that all fields are valid,
      // so we can dismiss the validation alert.
      this.alert.hide();

      // Check whether the problem has been released; if not,
      // warn the user and allow them to cancel.
      this.server.checkReleased().done(
        (isReleased) => {
          if (isReleased) {
            this.confirmPostReleaseUpdate($.proxy(this.updateEditorContext, this));
          } else {
            this.updateEditorContext();
          }
        },
      ).fail((errMsg) => {
        this.showError(errMsg);
      });
    }
  }

  /**
     Make the user confirm that he/she wants to update a problem
     that has already been released.

     Args:
     onConfirm (function): A function that accepts no arguments,
     executed if the user confirms the update.
     * */
  confirmPostReleaseUpdate(onConfirm) {
    const msg = 'This ORA has already been released. '
                + 'Changes will only affect learners making new submissions. '
                + 'Existing submissions will not be modified by this change.';
    // TODO: classier confirm dialog
    if (window.confirm(gettext(msg))) { onConfirm(); }
  }

  /**
   * Save the updated problem definition to the server.
   * */
  updateEditorContext() {
    // Notify the client-side runtime that we are starting
    // to save so it can show the "Saving..." notification
    this.runtime.notify('save', { state: 'start' });

    const fileUploadType = this.settingsView.fileUploadType();
    const teamsEnabled = this.settingsView.teamsEnabled();

    this.server.updateEditorContext({
      prompts: this.promptsView.promptsDefinition(),
      prompts_type: this.promptsView.promptsType(),
      feedbackPrompt: this.rubricView.feedbackPrompt(),
      feedback_default_text: this.rubricView.feedback_default_text(),
      criteria: this.rubricView.criteriaDefinition(),
      title: this.settingsView.displayName(),
      submissionStart: this.scheduleView.submissionStart(),
      submissionDue: this.scheduleView.submissionDue(),
      assessments: this.assessmentsStepsView.assessmentsDescription(),
      textResponse: this.settingsView.textResponseNecessity(),
      textResponseEditor: this.settingsView.textResponseEditor(),
      fileUploadResponse: this.settingsView.fileUploadResponseNecessity(),
      fileUploadType: fileUploadType !== '' ? fileUploadType : null,
      fileTypeWhiteList: this.settingsView.fileTypeWhiteList(),
      multipleFilesEnabled: teamsEnabled ? true : this.settingsView.multipleFilesEnabled(),
      latexEnabled: this.settingsView.latexEnabled(),
      leaderboardNum: this.settingsView.leaderboardNum(),
      editorAssessmentsOrder: this.assessmentsStepsView.editorAssessmentsOrder(),
      teamsEnabled,
      selectedTeamsetId: this.settingsView.teamset(),
      showRubricDuringResponse: this.settingsView.showRubricDuringResponse(),
    }).done(
      // Notify the client-side runtime that we finished saving
      // so it can hide the "Saving..." notification.
      // Then reload the view.
      () => this.runtime.notify('save', { state: 'end' }),
    ).fail(
      (msg) => this.showError(msg),
    );
  }

  /**
     Cancel editing.
     * */
  cancel() {
    // Notify the client-side runtime so it will close the editing modal
    this.saveTabState();
    this.runtime.notify('cancel', {});
  }

  /**
     Display an error message to the user.

     Args:
     errorMsg (string): The error message to display.
     * */
  showError(errorMsg) {
    this.runtime.notify('error', { msg: errorMsg });
  }

  /**
     Perform validation on each view and determine views failing validation.

     Returns:
     List of views failing validation or empty list

     * */
  validate() {
    const viewsFailingValidation = [];

    this.views.forEach((view) => {
      if (!view.validate()) {
        viewsFailingValidation.push(view);
      }
    });

    return viewsFailingValidation;
  }

  /** Given a list of views failing validation, mark their tabs as invalid */
  markTabsWithValidationErrors(viewsFailingValidation) {
    viewsFailingValidation.forEach((view) => {
      const tab = view.getTab();
      const numErrors = view.validationErrors().length;
      this.markTabAsInvalid(tab, numErrors);
    });
  }

  /**
   * Given a tab, add invalid warning markup
   *  numErrors - number of errors (only shown in screen reader help-text)
   * */
  markTabAsInvalid(tab, numErrors) {
    $('.tab-error-count', tab).text(gettext(`has ${numErrors} error(s)`));
    $('.validation-warning', tab).show();
  }

  /**
   * Given a tab, remove invalid warning markup
   * */
  clearTabValidation(tab) {
    $('.tab-error-count', tab).text('');
    $('.validation-warning', tab).hide();
  }

  /**
     Return a list of validation errors visible in the UI.
     Mainly useful for testing.

     Returns:
     list of string

     * */
  validationErrors() {
    return this.settingsView.validationErrors().concat(
      this.assessmentsStepsView.validationErrors().concat(
        this.scheduleView.validationErrors().concat(
          this.rubricView.validationErrors().concat(
            this.promptsView.validationErrors(),
          ),
        ),
      ),
    );
  }

  /**
     Clear all validation errors from the UI.
     * */
  clearValidationErrors() {
    this.views.forEach((view) => {
      view.clearValidationErrors();
      this.clearTabValidation(view.getTab());
    });
  }
}

/* XBlock entry point for Studio view */
/* jshint unused:false */
// eslint-disable-next-line no-unused-vars
export const OpenAssessmentEditor = (runtime, element, data) => {
  /**
     Initialize the editing interface on page load.
     * */
  const server = new Server(runtime, element);
  new StudioView(runtime, element, server, data);
};
