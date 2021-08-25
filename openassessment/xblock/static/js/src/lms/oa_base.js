import Server from '../oa_server';
import CourseItemsListingView from './oa_course_items_listing';
import FileUploader from './oa_file_upload';
import ResponseView from './oa_response';
import SelfView from './oa_self';
import StaffView from './oa_staff';
import GradeView from './oa_grade';
import LeaderboardView from './oa_leaderboard';
import MessageView from './oa_message';
import StaffAreaView from './oa_staff_area';
import StudentTrainingView from './oa_training';
import PeerView from './oa_peer';
import ResponseEditorLoader from './oa_response_editor';
import renderWaitingStepDetailsView from './oa_staff_waiting_step';

/**
Interface for student-facing views.

Args:
    runtime (Runtime): an XBlock runtime instance.
    element (DOM element): The DOM element representing this XBlock.
    server (OpenAssessment.Server): The interface to the XBlock server.
    data (Object): The data object passed from XBlock backend.

Returns:
    OpenAssessment.BaseView
* */
export class BaseView {
    IS_SHOWING_CLASS = 'is--showing';

    SLIDABLE_CLASS = 'ui-slidable';

    SLIDABLE_CONTENT_CLASS = 'ui-slidable__content';

    SLIDABLE_CONTROLS_CLASS = 'ui-slidable__control';

    SLIDABLE_CONTAINER_CLASS = 'ui-slidable__container';

    READER_FEEDBACK_CLASS = '.sr.reader-feedback';

    constructor(runtime, element, server, data) {
      this.runtime = runtime;
      this.element = element;
      this.server = server;
      this.fileUploader = new FileUploader();

      this.responseEditorLoader = new ResponseEditorLoader(data.AVAILABLE_EDITORS);

      this.responseView = new ResponseView(
        this.element, this.server, this.fileUploader, this.responseEditorLoader, this, data,
      );
      this.trainingView = new StudentTrainingView(this.element, this.server, this.responseEditorLoader, data, this);
      this.selfView = new SelfView(this.element, this.server, this.responseEditorLoader, data, this);
      this.peerView = new PeerView(this.element, this.server, this.responseEditorLoader, data, this);
      this.staffView = new StaffView(this.element, this.server, this);
      this.gradeView = new GradeView(this.element, this.server, this.responseEditorLoader, data, this);
      this.leaderboardView = new LeaderboardView(this.element, this.server, this.responseEditorLoader, data, this);
      this.messageView = new MessageView(this.element, this.server, this);
      // Staff-only area with information and tools for managing student submissions
      this.staffAreaView = new StaffAreaView(this.element, this.server, this.responseEditorLoader, data, this);
      this.usageID = '';
      this.srStatusUpdates = [];

      this.unsavedChanges = {};
    }

    // This is used by unit tests to reset state.
    clearUnsavedChanges() {
      this.unsavedChanges = {};
      window.onbeforeunload = null;
    }

    /**
     * Checks to see if the scrollTo function is available, then scrolls to the
     * top of the list of steps (or the specified selector) for this display.
     *
     * Ideally, we would not need to check if the function exists, and could
     * import scrollTo, or other dependencies, into workbench.
     *
     * @param {string} selector optional CSS selector to scroll to. If not supplied,
     *     the default value of ".openassessment__steps" is used.
     */
    scrollToTop(selector) {
      if (!selector) {
        selector = '.openassessment__steps';
      }
      if ($.scrollTo instanceof Function) {
        $(window).scrollTo($(selector, this.element), 800, { offset: -50 });
        $(`${selector} > header .${this.SLIDABLE_CLASS}`, this.element).focus();
      }
    }

    /**
     * Clear the text in the Aria live region.
     */
    srClear() {
      $(this.READER_FEEDBACK_CLASS).html('');
    }

    /**
     * Add the text messages to the Aria live region.
     *
     * @param {string[]} texts
     */
    srReadTexts(texts) {
      const $readerFeedbackSelector = $(this.READER_FEEDBACK_CLASS);
      let htmlFeedback = '';
      this.srClear();
      $.each(texts, (ids, value) => {
        htmlFeedback = `${htmlFeedback}<p>${value}</p>\n`;
      });
      $readerFeedbackSelector.html(htmlFeedback);
    }

    /**
     * Checks the rendering status of the views that may require Screen Reader Status updates.
     *
     * The only views that should be added here are those that require Screen Reader updates when moving from one
     * step to another.
     *
     * @return {boolean} true if any step's view is still loading.
     */
    areSRStepsLoading() {
      return this.responseView.isRendering
            || this.peerView.isRendering
            || this.selfView.isRendering
            || this.gradeView.isRendering
            || this.trainingView.isRendering
            || this.staffView.isRendering;
    }

    /**
     * Updates text in the Aria live region if all sections are rendered and focuses on the specified ID.
     *
     * @param {String} stepID - The id of the Step being worked on.
     * @param {String} usageID  - The Usage id of the xBlock.
     * @param {boolean} gradeStatus - true if this is a Grade status, false if it is an assessment status.
     * @param {Object} currentView - Current active view.
     * @param {String} focusID - The ID of the region to focus on.
     */
    announceStatusChangeToSRandFocus(stepID, usageID, gradeStatus, currentView, focusID) {
      const text = this.getStatus(stepID, currentView, gradeStatus);

      if (typeof usageID !== 'undefined'
            && $(stepID, currentView.element).hasClass('is--showing')
            && typeof focusID !== 'undefined') {
        $(focusID, currentView.element).focus();
        this.srStatusUpdates.push(text);
      } else if (currentView.announceStatus) {
        this.srStatusUpdates.push(text);
      }
      if (!this.areSRStepsLoading() && this.srStatusUpdates.length > 0) {
        this.srReadTexts(this.srStatusUpdates);
        this.srStatusUpdates = [];
      }
      currentView.announceStatus = false;
    }

    /**
     * Retrieves and returns the current status of a given step.
     *
     * @param {String} stepID - The id of the Step to retrieve status for.
     * @param {Object} currentView - The current view.
     * @param {boolean} gradeStatus - true if the status to be retrieved is the grade status,
     *      false if it is the assessment status
     * @return {String} - the current status.
     */
    getStatus(stepID, currentView, gradeStatus) {
      const cssBase = `${stepID} .step__header .step__title `;
      const cssStringTitle = `${cssBase}.step__label`;
      let cssStringStatus = `${cssBase}.step__status`;

      if (gradeStatus) {
        cssStringStatus = `${cssBase}.grade__value`;
      }

      return `${$(cssStringTitle, currentView.element).text().trim()} ${
        $(cssStringStatus, currentView.element).text().trim()}`;
    }

    /**
     * Install click handlers to expand/collapse a section.
     *
     * @param {element} parentElement JQuery selector for the container element.
     */
    setUpCollapseExpand(parentElement) {
      const view = this;

      $(`.${view.SLIDABLE_CONTROLS_CLASS}`, parentElement).each(function () {
        $(this).on('click', (event) => {
          event.preventDefault();

          const $slidableControl = $(event.target).closest(`.${view.SLIDABLE_CONTROLS_CLASS}`);

          const $container = $slidableControl.closest(`.${view.SLIDABLE_CONTAINER_CLASS}`);
          const $toggleButton = $slidableControl.find(`.${view.SLIDABLE_CLASS}`);
          const $panel = $slidableControl.next(`.${view.SLIDABLE_CONTENT_CLASS}`);

          if ($container.hasClass('is--showing')) {
            $panel.slideUp();
            $toggleButton.attr('aria-expanded', 'false');
            $container.removeClass('is--showing');
          } else if (!$container.hasClass('has--error')
                    && !$container.hasClass('is--empty')
                    && !$container.hasClass('is--unavailable')) {
            $panel.slideDown();
            $toggleButton.attr('aria-expanded', 'true');
            $container.addClass('is--showing');
          }

          $container.removeClass('is--initially--collapsed ');
        });
      });
    }

    /**
     *Install click handler for the LaTeX preview button.
     *
     * @param {element} parentElement JQuery selector for the container element.
     */
    bindLatexPreview(parentElement) {
      // keep the preview as display none at first
      parentElement.find('.submission__preview__item').hide();
      parentElement.find('.submission__preview').click(
        (eventObject) => {
          eventObject.preventDefault();
          const previewName = $(eventObject.target).data('input');
          // extract typed-in response and replace newline with br
          const previewText = parentElement.find(`textarea[data-preview="${previewName}"]`).val();
          const previewContainer = parentElement.find(`.preview_content[data-preview="${previewName}"]`);
          previewContainer.html(previewText.replace(/\r\n|\r|\n/g, '<br />'));

          // Render in mathjax
          previewContainer.parent().parent().parent().show();
          // eslint-disable-next-line new-cap
          MathJax.Hub.Queue(['Typeset', MathJax.Hub, previewContainer[0]]);
        },
      );
    }

    /**
     * Get usage key of an XBlock.
     */
    getUsageID() {
      if (!this.usageID) {
        this.usageID = $(this.element).data('usage-id');
      }
      return this.usageID;
    }

    /**
     * Asynchronously load each sub-view into the DOM.
     */
    load() {
      this.responseView.load();
      this.loadAssessmentModules();
      this.staffAreaView.load();
    }

    /**
     * Refresh the Assessment Modules. This should be called any time an action is
     * performed by the user.
     */
    loadAssessmentModules(usageID) {
      this.trainingView.load(usageID);
      this.peerView.load(usageID);
      this.staffView.load(usageID);
      this.selfView.load(usageID);
      this.gradeView.load(usageID);
      this.leaderboardView.load(usageID);

      /**
        this.messageView.load() is intentionally omitted.
        Because of the asynchronous loading, there is no way to tell (from the perspective of the
        messageView) whether or not the peer view was able to grab an assessment to assess. Any
        asynchronous strategy would run into a race condition based around this problem at some
        point.  Instead, we created a field in the XBlock called no_peers, which is set by the
        Peer XBlock Handler, and which is examined by the Message XBlock Handler.

        To Avoid rendering the message more than one time per update/load (and avoiding all comp-
        lications that that would likely induce), we chose to load the method view only after
        the peer view has been loaded.  This is achieved by having the peer view  call to render
        the message view after rendering itself but before exiting its load method.
        */
    }

    /**
     * Refresh the message only (called by PeerView to update and avoid race condition)
     */
    loadMessageView() {
      this.messageView.load();
    }

    /**
     * Report an error to the user.
     *
     * @param {string} type The type of error. Options are "save", submit", "peer", and "self".
     * @param {string} message The error message to display, or if null hide the message.
     *     Note: loading errors are never hidden once displayed.
     */
    toggleActionError(type, message) {
      const { element } = this;
      let container = null;
      if (type === 'save') {
        container = '.response__submission__actions';
      } else if (type === 'submit' || type === 'peer' || type === 'self' || type === 'student-training') {
        container = '.step__actions';
      } else if (type === 'feedback_assess') {
        container = '.submission__feedback__actions';
      } else if (type === 'upload') {
        container = '.upload__error';
      } else if (type === 'delete') {
        container = '.delete__error';
      }

      // If we don't have anywhere to put the message, just log it to the console
      if (container === null) {
        /* eslint-disable-next-line no-console */
        if (message !== null) { console.log(message); }
      } else {
        // Insert the error message
        $(`${container} .message__content`, element).html(`<p>${message ? _.escape(message) : ''}</p>`);
        // Toggle the error class
        $(container, element).toggleClass('has--error', message !== null);
        // Send focus to the error message
        $(`${container} > .message`, element).focus();
      }

      if (message !== null) {
        const contentTitle = $(`${container} .message__title`).text();
        this.srReadTexts([contentTitle, message]);
      }
    }

    /**
     * Report an error loading a step.
     *
     * @param {string} stepName The step that could not be loaded.
     * @param {string} errorMessage An optional error message to use instead of the default.
     */
    showLoadError(stepName, errorMessage) {
      if (!errorMessage) {
        errorMessage = gettext('Unable to load');
      }
      const $container = $(`.step--${stepName}`);
      $container.toggleClass('has--error', true);
      $container.removeClass('is--showing');
      $container.find('.ui-slidable').attr('aria-expanded', 'false');
      $container.find('.step__status__value i').removeClass().addClass('icon fa fa-exclamation-triangle');
      $container.find('.step__status__value .copy').html(_.escape(errorMessage));
    }

    /**
     * Enable/disable the "navigate away" warning to alert the user of unsaved changes.
     *
     * @param {boolean} enabled If specified, set whether the warning is enabled.
     * @param {string} key A unique key related to the type of unsaved changes. Must be supplied
     * if "enabled" is also supplied.
     * @param {string} message The message to show if navigating away with unsaved changes. Only needed
     * if "enabled" is true.
     * @return {boolean} Whether the warning is enabled (only if "enabled" argument is not supplied).
     */
    /* eslint-disable-next-line consistent-return */
    unsavedWarningEnabled(enabled, key, message) {
      if (typeof enabled === 'undefined') {
        return (window.onbeforeunload !== null);
      }
      // To support multiple ORA XBlocks on the same page, store state by XBlock usage-id.
      const usageID = $(this.element).data('usage-id');
      if (enabled) {
        if (typeof this.unsavedChanges[usageID] === 'undefined'
                    || !this.unsavedChanges[usageID]) {
          this.unsavedChanges[usageID] = {};
        }
        this.unsavedChanges[usageID][key] = message;

        /* eslint-disable-next-line consistent-return */
        window.onbeforeunload = function () {
          let returnValue;
          Object.keys(this.unsavedChanges).some((xblockUsageID) => {
            if (this.unsavedChanges.hasOwnProperty(xblockUsageID)) {
              const change = this.unsavedChanges[xblockUsageID];
              return Object.keys(change).some((changeKey) => {
                if (change.hasOwnProperty(key)) {
                  returnValue = change[key];
                  return true;
                }
                return false;
              });
            }
            return false;
          });
          return returnValue;
        };
      } else if (typeof this.unsavedChanges[usageID] !== 'undefined') {
        delete this.unsavedChanges[usageID][key];
        if ($.isEmptyObject(this.unsavedChanges[usageID])) {
          delete this.unsavedChanges[usageID];
        }
        if ($.isEmptyObject(this.unsavedChanges)) {
          window.onbeforeunload = null;
        }
      }
    }

    /**
     * Enable/disable the button with the given class name.
     *
     * @param {string} className The css class to find the button
     * @param {boolean} enabled If specified enables or disables the button. If not specified,
     *     the state of the button is not changed, but the current enabled status is returned.
     * @return {boolean} whether or not the button is enabled
     */
    buttonEnabled(className, enabled) {
      const $element = $(className, this.element);
      if (typeof enabled === 'undefined') {
        return !$element.prop('disabled');
      }
      $element.prop('disabled', !enabled);
      return enabled;
    }
}

/* XBlock JavaScript entry point for OpenAssessmentXBlock. */
/* jshint unused:false */
// eslint-disable-next-line no-unused-vars
export const OpenAssessmentBlock = (runtime, element, data) => {
  /**
    Render views within the base view on page load.
    * */
  const server = new Server(runtime, element);
  const view = new BaseView(runtime, element, server, data);
  view.load();
};

/* XBlock JavaScript entry point for OpenAssessmentXBlock. */
/* jshint unused:false */
// eslint-disable-next-line no-unused-vars
export const CourseOpenResponsesListingBlock = (runtime, element, data) => {
  const view = new CourseItemsListingView(runtime, element, data);
  view.refreshGrids();
};

/* XBlock JavaScript entry point for OpenAssessmentXBlock. */
/* jshint unused:false */
// eslint-disable-next-line no-unused-vars
export const StaffAssessmentBlock = (runtime, element, data) => {
  /**
    Render auxiliary view which displays the staff grading area
    * */
  const server = new Server(runtime, element);
  const view = new BaseView(runtime, element, server, data);
  view.staffAreaView.installHandlers();
};

/* XBlock JavaScript entry point for OpenAssessmentXBlock. */
/* jshint unused:false */
// eslint-disable-next-line no-unused-vars
export const WaitingStepDetailsBlock = (runtime, element, data) => {
  /**
    Render auxiliary view which displays the staff grading area
  * */
  const server = new Server(runtime, element);
  const baseView = new BaseView(runtime, element, server, data);
  renderWaitingStepDetailsView(baseView, data);
};

export default BaseView;
