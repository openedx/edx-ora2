import DateTimeFactory from './oa_datefactory';

/**
 * The GradeView class.
 *
 * @param {element} element - The DOM element representing the XBlock
 * @param {OpenAssessment.Server} server - The interface to the XBlock server
 * @param {OpenAssessment.BaseView} baseView - The container view.
 * @constructor
 */
export class GradeView {
  constructor(element, server, responseEditorLoader, data, baseView) {
    this.element = element;
    this.server = server;
    this.responseEditorLoader = responseEditorLoader;
    this.data = data;
    this.baseView = baseView;
    this.announceStatus = false;
    this.isRendering = false;
    this.dateFactory = new DateTimeFactory(this.element);
  }

  /**
     * Load the grade view.
     */
  load(usageID) {
    const view = this;
    const { baseView } = this;
    const stepID = '.step--grade';
    const focusID = `[id='oa_grade_${usageID}']`;
    view.isRendering = true;
    this.server.render('grade').done(
      (html) => {
        // Load the HTML and install event handlers
        $(stepID, view.element).replaceWith(html);
        view.server.renderLatex($(stepID, view.element));
        view.isRendering = false;
        view.installHandlers();

        view.baseView.announceStatusChangeToSRandFocus(stepID, usageID, true, view, focusID);
        view.dateFactory.apply();
      },
    ).fail((errMsg) => {
      baseView.showLoadError('grade', errMsg);
    });
  }

  /**
   Use Response Editor to render response
    * */
  renderResponseViaEditor() {
    const sel = $('.submission__answer__display', this.element);
    const responseElements = sel.find('.submission__answer__part__text__value');
    this.responseEditorLoader.load(this.data.TEXT_RESPONSE_EDITOR, responseElements);
  }

  /**
     * Install event handlers for the view.
     */
  installHandlers() {
    // Install a click handler for collapse/expand
    const sel = $('.step--grade', this.element);
    this.baseView.setUpCollapseExpand(sel);

    // Install a click handler for assessment feedback
    const view = this;
    sel.find('.feedback__submit').click((eventObject) => {
      eventObject.preventDefault();
      view.submitFeedbackOnAssessment();
    });
    view.renderResponseViaEditor();
  }

  /**
     * Get or set the text for feedback on assessments.
     *
     * @param {string} text - The text of the assessment to set (optional).
     * @return {string} The text of the feedback
     */
  /* eslint-disable-next-line consistent-return */
  feedbackText(text) {
    const usageID = this.baseView.getUsageID() || '';
    if (typeof text === 'undefined') {
      return $(`[id='feedback__remarks__value__${usageID}']`, this.element).val();
    }
    $(`[id='feedback__remarks__value__${usageID}']`, this.element).val(text);
  }

  /**
     * Get or set the options for feedback on assessments.
     *
     * @param {dict} options - List of options to check (optional).
     * @return {list} - The values of the options the user selected.
     */
  /* eslint-disable-next-line consistent-return */
  feedbackOptions(options) {
    const view = this;
    const usageID = this.baseView.getUsageID() || '';
    if (typeof options === 'undefined') {
      return $.map(
        $('.feedback__overall__value:checked', view.element),
        (element) => $(element).val(),
      );
    }
    // Uncheck all the options
    $('.feedback__overall__value', this.element).prop('checked', false);

    // Check the selected options
    $.each(options, (index, opt) => {
      $(`[id='feedback__overall__value--${opt}__${usageID}']`, view.element)
        .prop('checked', true);
    });
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
     * Check whether elements are hidden.
     *
     * @param {JQuery.selector} selector - The selector matching the elements to check.
     * @return {boolean} - True if all the elements are hidden, else false.
     */
  isHidden(selector) {
    return selector.hasClass('is--hidden') && selector.attr('aria-hidden') === 'true';
  }

  /**
     * Get or set the state of the feedback on assessment.
     *
     * Each state corresponds to a particular configuration of attributes
     * in the DOM, which control what the user sees in the UI.
     *
     * Valid states are:
     *     'open': The user has not yet submitted feedback on assessments.
     *     'submitting': The user has submitted feedback, but the server has not yet responded.
     *     'submitted': The feedback was successfully submitted.
     *
     * @param {string} newState - the new state to set for the feedback (optional).
     * @return {*} The current state.
     */
  /* eslint-disable-next-line consistent-return */
  feedbackState(newState) {
    const containerSel = $('.submission__feedback__content', this.element);
    const instructionsSel = containerSel.find('.submission__feedback__instructions');
    const fieldsSel = containerSel.find('.submission__feedback__fields');
    const actionsSel = containerSel.find('.submission__feedback__actions');
    const transitionSel = containerSel.find('.transition__status');
    const messageSel = containerSel.find('.message--complete');

    if (typeof newState === 'undefined') {
      const isSubmitting = (
        containerSel.hasClass('is--transitioning') && containerSel.hasClass('is--submitting')
                && !this.isHidden(transitionSel) && this.isHidden(messageSel)
                && this.isHidden(instructionsSel) && this.isHidden(fieldsSel) && this.isHidden(actionsSel)
      );
      const hasSubmitted = (
        containerSel.hasClass('is--submitted')
                && this.isHidden(transitionSel) && !this.isHidden(messageSel)
                && this.isHidden(instructionsSel) && this.isHidden(fieldsSel) && this.isHidden(actionsSel)
      );
      const isOpen = (
        !containerSel.hasClass('is--submitted')
                && !containerSel.hasClass('is--transitioning') && !containerSel.hasClass('is--submitting')
                && this.isHidden(transitionSel) && this.isHidden(messageSel)
                && !this.isHidden(instructionsSel) && !this.isHidden(fieldsSel) && !this.isHidden(actionsSel)
      );

      if (isOpen) {
        return 'open';
      } if (isSubmitting) {
        return 'submitting';
      } if (hasSubmitted) {
        return 'submitted';
      }
      throw new Error('Invalid feedback state');
    } else if (newState === 'open') {
      containerSel.toggleClass('is--transitioning', false);
      containerSel.toggleClass('is--submitting', false);
      containerSel.toggleClass('is--submitted', false);
      this.setHidden(instructionsSel, false);
      this.setHidden(fieldsSel, false);
      this.setHidden(actionsSel, false);
      this.setHidden(transitionSel, true);
      this.setHidden(messageSel, true);
    } else if (newState === 'submitting') {
      containerSel.toggleClass('is--transitioning', true);
      containerSel.toggleClass('is--submitting', true);
      containerSel.toggleClass('is--submitted', false);
      this.setHidden(instructionsSel, true);
      this.setHidden(fieldsSel, true);
      this.setHidden(actionsSel, true);
      this.setHidden(transitionSel, false);
      this.setHidden(messageSel, true);
    } else if (newState === 'submitted') {
      containerSel.toggleClass('is--transitioning', false);
      containerSel.toggleClass('is--submitting', false);
      containerSel.toggleClass('is--submitted', true);
      this.setHidden(instructionsSel, true);
      this.setHidden(fieldsSel, true);
      this.setHidden(actionsSel, true);
      this.setHidden(transitionSel, true);
      this.setHidden(messageSel, false);
    }
  }

  /**
     * Send assessment feedback to the server and update the view.
     */
  submitFeedbackOnAssessment() {
    // Send the submission to the server
    const view = this;
    const { baseView } = this;

    // Disable the submission button to prevent duplicate submissions
    $('.feedback__submit', this.element).prop('disabled', true);

    // Indicate to the user that we're starting to submit
    view.feedbackState('submitting');

    // Submit the feedback to the server
    // When the server reports success, update the UI to indicate that we'v submitted.
    this.server.submitFeedbackOnAssessment(
      this.feedbackText(), this.feedbackOptions(),
    ).done(
      () => { view.feedbackState('submitted'); },
    ).fail((errMsg) => {
      baseView.toggleActionError('feedback_assess', errMsg);
    });
  }
}

export default GradeView;
