import DateTimeFactory from './oa_datefactory';
import Rubric from './oa_rubric';

/**
Interface for student training view.

Args:
    element (DOM element): The DOM element representing the XBlock.
    server (OpenAssessment.Server): The interface to the XBlock server.
    baseView (OpenAssessment.BaseView): Container view.

Returns:
    OpenAssessment.StudentTrainingView
* */
export class StudentTrainingView {
  constructor(element, server, responseEditorLoader, data, baseView) {
    this.element = element;
    this.server = server;
    this.responseEditorLoader = responseEditorLoader;
    this.data = data;
    this.baseView = baseView;
    this.rubric = null;
    this.isRendering = false;
    this.announceStatus = false;
    this.dateFactory = new DateTimeFactory(this.element);
  }

  /**
      Load the student training view.
      * */
  load(usageID) {
    const view = this;
    const stepID = '.step--student-training';
    const focusID = `[id='oa_training_${usageID}']`;
    view.isRendering = true;
    this.server.render('student_training').done(
      (html) => {
        // Load the HTML and install event handlers
        $(stepID, view.element).replaceWith(html);
        this.isRendering = false;
        this.server.renderLatex($(stepID, view.element));

        this.renderResponseViaEditor();

        this.installHandlers();

        this.baseView.announceStatusChangeToSRandFocus(stepID, usageID, false, view, focusID);
        this.announceStatus = false;
        this.dateFactory.apply();
      },
    ).fail(() => {
      this.baseView.showLoadError('student-training');
    });
  }

  /**
    Use Response Editor to render response
    * */
  renderResponseViaEditor() {
    const sel = $('.step--student-training', this.element);
    const responseElements = sel.find('.submission__answer__part__text__value');
    return this.responseEditorLoader.load(this.data.TEXT_RESPONSE_EDITOR, responseElements);
  }

  /**
    Install event handlers for the view.
    * */
  installHandlers() {
    const sel = $('.step--student-training', this.element);

    // Install a click handler for collapse/expand
    this.baseView.setUpCollapseExpand(sel);

    // Initialize the rubric
    const rubricSelector = $('.student-training--001__assessment', this.element);
    if (rubricSelector.size() > 0) {
      const rubricElement = rubricSelector.get(0);
      this.rubric = new Rubric(rubricElement);
    }

    // Install a change handler for rubric options to enable/disable the submit button
    if (this.rubric !== null) {
      this.rubric.canSubmitCallback($.proxy(this.assessButtonEnabled, this));
    }

    // Install a click handler for submitting the assessment
    sel.find('.student-training--001__assessment__submit').click(
      (eventObject) => {
        // Override default form submission
        eventObject.preventDefault();

        // Handle the click
        this.assess();
        this.announceStatus = true;
      },
    );
  }

  /**
    Submit an assessment for the training example.
    * */
  assess() {
    // Immediately disable the button to prevent resubmission
    this.assessButtonEnabled(false);

    let options = {};
    if (this.rubric !== null) {
      options = this.rubric.optionsSelected();
    }
    const { baseView } = this;
    const usageID = baseView.getUsageID();
    this.server.trainingAssess(options).done(
      (corrections) => {
        const incorrect = $('.openassessment__student-training--incorrect', this.element);
        const instructions = $('.openassessment__student-training--instructions', this.element);
        const $questionAnswers = $('.question__answers', this.rubric.element);

        if (!this.rubric.showCorrections(corrections)) {
          this.load(usageID);
          baseView.loadAssessmentModules(usageID);
          incorrect.addClass('is--hidden');
          instructions.removeClass('is--hidden');
        } else {
          instructions.addClass('is--hidden');
          incorrect.removeClass('is--hidden');
          $questionAnswers.each((index, answer) => {
            const $notification = $('.step__message.message', this.rubric.element).not('.is--hidden');
            $(answer).attr('aria-describedby', $($notification[index]).attr('id'));
          });
          baseView.srReadTexts([gettext('Feedback available for selection.')]);
        }
        baseView.scrollToTop('.step--student-training');
      },
    ).fail((errMsg) => {
      // Display the error
      baseView.toggleActionError('student-training', errMsg);

      // Re-enable the button to allow the user to resubmit
      this.assessButtonEnabled(true);
    });
  }

  /**
     Enable/disable the submit training assessment button.
     Check that whether the assessment button is enabled.

     Args:
     enabled (bool): If specified, set the state of the button.

     Returns:
     bool: Whether the button is enabled.

     Examples:
     >> view.assessButtonEnabled(true);  // enable the button
     >> view.assessButtonEnabled();  // check whether the button is enabled
     >> true
    * */
  assessButtonEnabled(isEnabled) {
    return this.baseView.buttonEnabled('.student-training--001__assessment__submit', isEnabled);
  }
}

export default StudentTrainingView;
