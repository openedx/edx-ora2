import Rubric from './oa_rubric';
import ConfirmationAlert from './oa_confirmation_alert';

/**
 * Interface for staff area view.
 *
 * Args:
 *   element (DOM element): The DOM element representing the XBlock.
 *   server (OpenAssessment.Server): The interface to the XBlock server.
 *   baseView (OpenAssessment.BaseView): Container view.
 *
 * Returns:
 *   OpenAssessment.StaffAreaView
 */
export class StaffAreaView {
    FULL_GRADE_UNSAVED_WARNING_KEY = 'staff-grade';

    OVERRIDE_UNSAVED_WARNING_KEY = 'staff-override';

    constructor(element, server, responseEditorLoader, data, baseView) {
      this.element = element;
      this.server = server;
      this.responseEditorLoader = responseEditorLoader;
      this.data = data;
      this.baseView = baseView;
    }

    /**
     * Load the staff area.
     */
    load() {
      const view = this;

      // If we're course staff, the base template should contain a section
      // for us to render the staff area into.  If that doesn't exist,
      // then we're not staff, so we don't need to send the AJAX request.
      if ($('.openassessment__staff-area', view.element).length > 0) {
        this.server.render('staff_area').done((html) => {
          // Load the HTML and install event handlers
          $('.openassessment__staff-area', view.element).replaceWith(html);
          view.server.renderLatex($('.openassessment__staff-area', view.element));
          view.installHandlers();
        }).fail(() => {
          view.baseView.showLoadError('staff_area');
        });
      }
    }

    /**
     Use Response Editor to render response
     * */
    renderResponseViaEditor() {
      const sel = $('.openassessment__staff-area', this.element);
      const responseElements = sel.find('.submission__answer__part__text__value');
      this.responseEditorLoader.load(this.data.TEXT_RESPONSE_EDITOR, responseElements);
    }

    /**
     * Upon request, loads the student info section of the staff area.
     * This allows viewing all the submissions and assessments associated
     * to the given student's current workflow.
     *
     * @param {string} classToExpand An optional CSS class. If present, the "slidable content"
     *     within the element with this class will be expanded after rendering the student
     *     info section.
     * @return {promise} A promise representing the successful loading
     *     of the student info section.
     */
    loadStudentInfo(classToExpand) {
      const view = this;
      const $manageLearnersTab = $('.openassessment__staff-tools', this.element);
      const $form = $manageLearnersTab.find('.openassessment_student_info_form');
      const studentUsername = $manageLearnersTab.find('.openassessment__student_username').val();
      const showFormError = function (errorMessage) {
        $form.find('.form--error').text(errorMessage).focus();
      };
        // eslint-disable-next-line new-cap
      const deferred = $.Deferred();

      // Clear any previous student information
      $('.openassessment__student-info', view.element).text('');

      if (studentUsername.trim()) {
        this.server.studentInfo(studentUsername).done((html) => {
          // Clear any error message
          showFormError('');

          // Load the HTML and install event handlers
          $('.openassessment__student-info', view.element).replaceWith(html);

          // Install key handler for cancel submission button.
          $manageLearnersTab.on('click', '.action--submit-cancel-submission', function (eventObject) {
            eventObject.preventDefault();
            // eslint-disable-next-line no-invalid-this
            view.cancelSubmission($(this).data('submission-uuid'));
          });

          // Install change handler for textarea (to enable cancel submission button)
          const handleChange = function (eventData) { view.handleCommentChanged(eventData); };
          $manageLearnersTab.find('.cancel_submission_comments').on('change keyup drop paste', handleChange);

          // Initialize the rubric
          const $rubric = $manageLearnersTab.find('.staff-assessment__assessment');
          if ($rubric.size() > 0) {
            const rubricElement = $rubric.get(0);
            const rubric = new Rubric(rubricElement);

            // Install a change handler for rubric options to enable/disable the submit button
            rubric.canSubmitCallback($.proxy(view.staffSubmitEnabled, view, $manageLearnersTab));

            rubric.changesExistCallback(
              $.proxy(view.assessmentRubricChanges, view, view.OVERRIDE_UNSAVED_WARNING_KEY),
            );

            // Install a click handler for the submit button
            $manageLearnersTab.find('.wrapper--staff-assessment .action--submit', view.element).click(
              (eventObject) => {
                const target = $(eventObject.currentTarget);
                const rootElement = target.closest('.openassessment__student-info');
                const submissionID = rootElement.data('submission-uuid');

                eventObject.preventDefault();
                view.submitStaffOverride(submissionID, rubric, $manageLearnersTab);
              },
            );
          }
          // Install click handlers for ui-slidable sections
          view.baseView.setUpCollapseExpand($manageLearnersTab);

          // By default, focus is put on the summary.
          $manageLearnersTab.find('.staff-info__student__report__summary').focus();

          if (classToExpand) {
            $manageLearnersTab.find(`.${classToExpand} .${view.baseView.SLIDABLE_CONTENT_CLASS}`)
              .slideDown();
            $manageLearnersTab.find(`.${classToExpand} .${view.baseView.SLIDABLE_CLASS}`)
              .addClass(view.baseView.IS_SHOWING_CLASS).attr('aria-expanded', 'true').focus();
          }

          view.renderResponseViaEditor();
          deferred.resolve();
        }).fail(() => {
          showFormError(gettext('Unexpected server error.'));
          deferred.reject();
        });
      } else {
        showFormError(gettext('You must provide a learner name.'));
        deferred.reject();
      }
      return deferred.promise();
    }

    /**
     * Upon request, loads the staff grade/assessment section of the staff area.
     * This allows staff grading when staff assessment is a required step.
     *
     * @return {promise} A promise representing the successful loading
     * of the staff grade (assessment) section.
     */
    loadStaffGradeForm() {
      const view = this;
      const $staffGradeTab = $('.openassessment__staff-grading', this.element);
      const $staffGradeControl = $staffGradeTab.find(`.${view.baseView.SLIDABLE_CLASS}`);
      const $staffGradeContent = $staffGradeTab.find(`.${view.baseView.SLIDABLE_CONTENT_CLASS}`);
      const $staffGradeContainer = $staffGradeTab.find(`.${view.baseView.SLIDABLE_CONTAINER_CLASS}`);

      // eslint-disable-next-line new-cap
      const deferred = $.Deferred();
      const showFormError = function (errorMessage) {
        $staffGradeTab.find('.staff__grade__form--error').text(errorMessage).focus();
      };

      $staffGradeControl.attr('aria-expanded', 'true');
      if (this.staffGradeFormLoaded) {
        $staffGradeContent.slideDown();
        $staffGradeContainer.addClass(view.baseView.IS_SHOWING_CLASS);
        deferred.resolve();
      } else {
        this.staffGradeFormLoaded = true;
        this.server.staffGradeForm().done((html) => {
          showFormError('');

          // Load the HTML and install event handlers
          $staffGradeTab.find('.staff__grade__form').replaceWith(html);

          // Update the number of ungraded and checked out assigments.
          view.updateStaffGradeCounts();

          const $rubric = $staffGradeTab.find('.staff-assessment__assessment');
          if ($rubric.size() > 0) {
            const rubricElement = $rubric.get(0);
            const rubric = new Rubric(rubricElement);

            // Install a change handler for rubric options to enable/disable the submit button
            rubric.canSubmitCallback($.proxy(view.staffSubmitEnabled, view, $staffGradeTab));

            rubric.changesExistCallback(
              $.proxy(view.assessmentRubricChanges, view, view.FULL_GRADE_UNSAVED_WARNING_KEY),
            );

            // Install a click handler for the submit buttons
            $staffGradeTab.find('.wrapper--staff-assessment .action--submit').click(
              (eventObject) => {
                const submissionID = $staffGradeTab.find('.staff__grade__form').data('submission-uuid');
                const teamSubmissionEnabled = $staffGradeTab.find('.staff__grade__form')
                  .data('team-submission') === 'True';

                eventObject.preventDefault();

                // team submissions get a warning prompt

                if (teamSubmissionEnabled) {
                  const msg = gettext(
                    'This grade will be applied to all members of the team. '
                        + 'Do you want to continue?',
                  );
                  view.confirmDialog.confirm(
                    gettext('Confirm Grade Team Submission'),
                    msg,
                    () => {
                      view.submitStaffGrade(
                        submissionID,
                        rubric,
                        $staffGradeTab,
                        $(eventObject.currentTarget).hasClass('continue_grading--action'),
                      );
                    },
                    () => {},
                  );
                  return;
                }

                view.submitStaffGrade(submissionID, rubric, $staffGradeTab,
                  $(eventObject.currentTarget).hasClass('continue_grading--action'));
              },
            );
          }

          $staffGradeContent.slideDown(
            () => {
              // For accessibility, move focus to the staff grade form control
              // (since this code may have executed as part of "Submit and Grade Next...").
              $staffGradeControl.focus();
              // Install click handlers for ui-slidable sections
              view.baseView.setUpCollapseExpand($('.staff__grade__form', view.element));
            },
          );
          $staffGradeContainer.addClass(view.baseView.IS_SHOWING_CLASS);

          view.renderResponseViaEditor();
          deferred.resolve();
        }).fail(() => {
          showFormError(gettext('Unexpected server error.'));
          view.staffGradeFormLoaded = false;
          deferred.reject();
        });
      }

      return deferred.promise();
    }

    /**
     * Closes the staff grade/assessment section of the staff area.
     *
     * @param {boolean} clear if true, remove the staff grade form and collapse it. Otherwise
     *     the staff grade form is collapsed but not removed (meaning that the same
     *     form will be presented if the user later expands the staff grade section again).
     */
    closeStaffGradeForm(clear) {
      const view = this;
      const $staffGradeTab = $('.openassessment__staff-grading', view.element);
      const $staffGradeControl = $staffGradeTab.find(`.${view.baseView.SLIDABLE_CLASS}`).first();
      const $staffGradeContent = $staffGradeTab.find(`.${view.baseView.SLIDABLE_CONTENT_CLASS}`);
      const $staffGradeContainer = $staffGradeTab.find(`.${view.baseView.SLIDABLE_CONTAINER_CLASS}`);

      $staffGradeControl.attr('aria-expanded', 'false');
      if (clear) {
        // Collapse the editor and update the counts.
        // This is the case of submitting an assessment and NOT continuing with grading.
        $staffGradeTab.find('.staff__grade__form').replaceWith('<div class="staff__grade__form"></div>');
        this.updateStaffGradeCounts();
      } else {
        // Just hide the form currently being shown (no need to update counts).
        $staffGradeContent.slideUp();
      }

      $staffGradeContainer.removeClass(view.baseView.IS_SHOWING_CLASS);
      // For accessibility, move focus to the staff grade form control.
      $staffGradeControl.focus();
    }

    /**
     * Update the counts of ungraded and checked out assessments.
     */
    updateStaffGradeCounts() {
      const view = this;
      const $staffGradeTab = $('.openassessment__staff-grading', this.element);

      view.server.staffGradeCounts().done((html) => {
        $staffGradeTab.find('.staff__grade__status').replaceWith(html);
      }).fail(() => {
        $staffGradeTab.find('.staff__grade__status').replaceWith(
          `<span class="staff__grade__status"><span class="staff__grade__value"><span class="copy">${
            gettext('Error getting the number of ungraded responses')
          }</span></span></span>`,
        );
      });
    }

    /**
     * Install event handlers for the view.
     */
    installHandlers() {
      const view = this;
      const $staffArea = $('.openassessment__staff-area', this.element);
      const $manageLearnersTab = $('.openassessment__staff-tools', $staffArea);
      const $staffGradeTool = $('.openassessment__staff-grading', $staffArea);

      if ($staffArea.length <= 0) {
        return;
      }

      // Install a click handler for the staff button panel
      $staffArea.find('.ui-staff__button').click(
        (eventObject) => {
          // Close all other panels first. Classes and aria attributes will be updated below.
          $staffArea.find('.ui-staff__button').each((index, button) => {
            if (button !== eventObject.currentTarget) {
              const $panel = $staffArea.find(`.${$(button).data('panel')}`).first();
              $panel.slideUp(0);
            }
          });

          const $button = $(eventObject.currentTarget);
          const $panel = $staffArea.find(`.${$button.data('panel')}`).first();

          if ($button.hasClass('is--active')) {
            $button.removeClass('is--active').attr('aria-expanded', 'false');
            $panel.slideUp();
          } else {
            // Remove "is--active" and the aria-expanded state from all buttons.
            $staffArea.find('.ui-staff__button').removeClass('is--active').attr('aria-expanded', 'false');
            // Set "is--active" and aria-expanded state on the toggled button.
            $button.addClass('is--active').attr('aria-expanded', 'true');
            $panel.slideDown();
          }
          // For accessibility, move focus to the first focusable component.
          $panel.find('.ui-staff_close_button').focus();
        },
      );

      // Install a click handler for the close button for staff panels
      $staffArea.find('.ui-staff_close_button').click(
        (eventObject) => {
          const $button = $(eventObject.currentTarget);
          const $panel = $button.closest('.wrapper--ui-staff');
          $staffArea.find('.ui-staff__button').removeClass('is--active').attr('aria-expanded', 'false');
          $panel.slideUp();

          // For accessibility, move focus back to the tab associated with the closed panel.
          $staffArea.find('.ui-staff__button').each((index, button) => {
            const $staffPanel = $staffArea.find(`.${$(button).data('panel')}`).first();
            if ($staffPanel[0] === $panel[0]) {
              $(button).focus();
            }
          });
        },
      );

      // Install key handler for student id field
      $manageLearnersTab.find('.openassessment_student_info_form').submit(
        (eventObject) => {
          eventObject.preventDefault();
          view.loadStudentInfo();
        },
      );

      // Install a click handler for requesting student info
      $manageLearnersTab.find('.action--submit-username').click(
        (eventObject) => {
          eventObject.preventDefault();
          view.loadStudentInfo();
        },
      );

      // Install a click handler for scheduling AI classifier training
      $manageLearnersTab.find('.action--submit-training').click(
        (eventObject) => {
          eventObject.preventDefault();
          view.scheduleTraining();
        },
      );

      // Install a click handler for rescheduling unfinished AI tasks for this problem
      $manageLearnersTab.find('.action--submit-unfinished-tasks').click(
        (eventObject) => {
          eventObject.preventDefault();
          view.rescheduleUnfinishedTasks();
        },
      );

      // Install a click handler for showing the staff grading form.
      $staffGradeTool.find('.staff__grade__show-form').click(
        (event) => {
          const $container = $(event.currentTarget).closest(`.${view.baseView.SLIDABLE_CONTAINER_CLASS}`);
          const wasShowing = $container.hasClass(view.baseView.IS_SHOWING_CLASS);
          if (wasShowing) {
            view.closeStaffGradeForm(false);
          } else {
            view.loadStaffGradeForm();
          }
        },
      );
      view.confirmDialog = new ConfirmationAlert($staffArea.find('.openassessment__staff-area-dialog-confirm'));
    }

    /**
     * Sends a request to the server to schedule the training
     * of classifiers for this problem's Example Based Assessments.
     */
    scheduleTraining() {
      const view = this;
      this.server.scheduleTraining().done((msg) => {
        $('.schedule_training_message', view.element).text(msg);
      }).fail((errMsg) => {
        $('.schedule_training_message', view.element).text(errMsg);
      });
    }

    /**
     * Begins the process of rescheduling all unfinished grading tasks.
     * This includes checking if the classifiers have been created,
     * and grading any unfinished student submissions.
     */
    rescheduleUnfinishedTasks() {
      const view = this;
      this.server.rescheduleUnfinishedTasks().done((msg) => {
        $('.reschedule_unfinished_tasks_message', view.element).text(msg);
      }).fail((errMsg) => {
        $('.reschedule_unfinished_tasks_message', view.element).text(errMsg);
      });
    }

    /**
     * Upon request, cancel the submission from grading pool.
     */
    cancelSubmission(submissionUUID) {
      // Immediately disable the button to prevent multiple requests.
      this.cancelSubmissionEnabled(false);
      const view = this;
      const comments = $('.cancel_submission_comments', this.element).val();
      this.server.cancelSubmission(submissionUUID, comments).done(() => {
        // Note: we ignore any message returned from the server and instead
        // re-render the student info with the "Learner's Final Grade"
        // section expanded. This section will show that the learner's
        // submission was cancelled.
        view.loadStudentInfo('staff-info__student__grade');
      }).fail((errorMessage) => {
        $('.cancel-submission-error').html(_.escape(errorMessage));
      });
    }

    /**
     * Enable/disable the cancel submission button.
     *
     * Check whether the cancel submission button is enabled.
     *
     * Args:
     *   enabled (bool): If specified, set the state of the button.
     *
     * Returns:
     *   bool: Whether the button is enabled.
     *
     * Examples:
     * >> view.submitEnabled(true);  // enable the button
     * >> view.submitEnabled();  // check whether the button is enabled
     * >> true
     */
    cancelSubmissionEnabled(enabled) {
      return this.baseView.buttonEnabled('.action--submit-cancel-submission', enabled);
    }

    /**
     * Set the comment text.
     *
     * Retrieve the comment text.
     *
     * Args:
     *   text (string): reason to .
     *
     * Returns:
     *   string: The current comment text.
     */
    /* eslint-disable-next-line consistent-return */
    comment(text) {
      const $submissionComments = $('.cancel_submission_comments', this.element);
      if (typeof text === 'undefined') {
        return $submissionComments.val();
      }
      $submissionComments.val(text);
    }

    /**
     * Enable/disable the cancel submission based on whether
     * the user has entered a comment.
     */
    handleCommentChanged() {
      // Enable the cancel submission button only for non-blank comments
      const isBlank = $.trim(this.comment()) !== '';
      this.cancelSubmissionEnabled(isBlank);
    }

    /**
     * Enable/disable submit button(s) for staff grading or staff override.
     *
     * @param {element} scope An ancestor element for the submit button (to allow for shared
     *     classes in different form).
     * @param {boolean} enabled If specified, sets the state of the button.
     * @return {boolean} Whether the button is enabled
     */
    staffSubmitEnabled(scope, enabled) {
      return this.baseView.buttonEnabled('.wrapper--staff-assessment .action--submit', enabled);
    }

    /**
     * Called when something is selected or typed in the assessment rubric.
     * Used to set the unsaved changes warning dialog.
     *
     * @param {string} key the unsaved changes key
     * @param {boolean} changesExist true if unsaved changes exist
     */
    assessmentRubricChanges(key, changesExist) {
      if (changesExist) {
        this.baseView.unsavedWarningEnabled(
          true,
          key,
          // eslint-disable-next-line max-len
          gettext('If you leave this page without submitting your staff assessment, you will lose any work you have done.'),
        );
      }
    }

    /**
     * Submit the staff assessment override.
     *
     * @param {string} submissionID The ID of the submission to be submitted.
     * @param {element} rubric The rubric element to be assessed.
     * @param {element} scope An ancestor element for the submit button (to allow for shared
     *     classes in different form).
     */
    submitStaffOverride(submissionID, rubric, scope) {
      const view = this;
      const successCallback = function () {
        view.baseView.unsavedWarningEnabled(false, view.OVERRIDE_UNSAVED_WARNING_KEY);
        // Note: we ignore any message returned from the server and instead
        // re-render the student info with the "Learner's Final Grade"
        // section expanded. This section will show the learner's
        // final grade and in the future should include details of
        // the staff override itself.
        view.loadStudentInfo('staff-info__student__grade');
      };
      this.callStaffAssess(submissionID, rubric, scope, successCallback, '.staff-override-error', 'regrade');
    }

    /**
     * Submit the staff grade, and check out another learner for grading if continueGrading is true.
     *
     * @param {string} submissionID The ID of the submission to be submitted.
     * @param {element} rubric The rubric element to be assessed.
     * @param {element} scope An ancestor element for the submit button (to allow for shared
     *     classes in different form).
     * @param {boolean} continueGrading If true, another learner will be marked as "In Progress",
     *     and a new grading form will be rendered with the learner's answer.
     */
    submitStaffGrade(submissionID, rubric, scope, continueGrading) {
      const view = this;
      const successCallback = function () {
        view.baseView.unsavedWarningEnabled(false, view.FULL_GRADE_UNSAVED_WARNING_KEY);
        view.staffGradeFormLoaded = false;
        if (continueGrading) {
          view.loadStaffGradeForm();
          view.baseView.scrollToTop('.openassessment__staff-area');
        } else {
          view.closeStaffGradeForm(true);
        }
      };
      this.callStaffAssess(submissionID, rubric, scope, successCallback, '.staff-grade-error', 'full-grade');
    }

    /**
     * Make the server call to submit the staff assessment.
     *
     * @param {string} submissionID The ID of the submission to be submitted.
     * @param {element} rubric The rubric element to be assessed.
     * @param {element} scope An ancestor element for the submit button (to allow for shared
     *     classes in different form).
     * @param {function} successCallback A function to execute on success.
     * @param {string} errorSelector a CSS class selector for displaying error messages.
     * @param {string} assessType a string indicating whether this was a 'full-grade' or 'regrade'
     */
    callStaffAssess(submissionID, rubric, scope, successCallback, errorSelector, assessType) {
      const view = this;
      view.staffSubmitEnabled(scope, false);

      this.server.staffAssess(
        rubric.optionsSelected(), rubric.criterionFeedback(), rubric.overallFeedback(), submissionID, assessType,
      ).done(successCallback).fail((errorMessage) => {
        scope.find(errorSelector).html(_.escape(errorMessage));
        view.staffSubmitEnabled(scope, true);
      });
    }
}

export default StaffAreaView;
