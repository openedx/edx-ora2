import DateTimeFactory from './oa_datefactory';
import Rubric from './oa_rubric';
/**
Interface for self assessment view.

Args:
    element (DOM element): The DOM element representing the XBlock.
    server (OpenAssessment.Server): The interface to the XBlock server.
    baseView (OpenAssessment.BaseView): Container view.

Returns:
    OpenAssessment.SelfView
* */
export class SelfView {
    UNSAVED_WARNING_KEY = 'self-assessment';

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
    Load the self assessment view.
    * */
    load(usageID) {
      const view = this;
      const stepID = '.step--self-assessment';
      const focusID = `[id='oa_self_${usageID}']`;
      view.isRendering = true;
      this.server.render('self_assessment').done(
        (html) => {
          // Load the HTML and install event handlers
          $(stepID, view.element).replaceWith(html);
          view.isRendering = false;

          view.server.renderLatex($(stepID, view.element));

          this.renderResponseViaEditor();

          view.installHandlers();
          view.baseView.announceStatusChangeToSRandFocus(stepID, usageID, false, view, focusID);
          view.dateFactory.apply();
        },
      ).fail(() => {
        view.showLoadError('self-assessment');
      });
    }

    /**
     Use Response Editor to render response
     * */
    renderResponseViaEditor() {
      const sel = $('.step--self-assessment', this.element);
      const responseElements = sel.find('.submission__answer__part__text__value');
      return this.responseEditorLoader.load(this.data.TEXT_RESPONSE_EDITOR, responseElements);
    }

    /**
    Install event handlers for the view.
    * */
    installHandlers() {
      const view = this;
      const sel = $('.step--self-assessment', view.element);

      // Install a click handler for collapse/expand
      this.baseView.setUpCollapseExpand(sel);

      // Install click handler for the preview button
      this.baseView.bindLatexPreview(sel);

      // Initialize the rubric
      const rubricSelector = $('.self-assessment--001__assessment', this.element);
      if (rubricSelector.size() > 0) {
        const rubricElement = rubricSelector.get(0);
        this.rubric = new Rubric(rubricElement);
      } else {
        // If there was previously a rubric visible, clear the reference to it.
        this.rubric = null;
      }

      // Install a change handler for rubric options to enable/disable the submit button
      if (this.rubric !== null) {
        this.rubric.canSubmitCallback($.proxy(this.selfSubmitEnabled, this));

        this.rubric.changesExistCallback($.proxy(this.assessmentRubricChanges, this));
      }

      // Install a click handler for the submit button
      sel.find('.self-assessment--001__assessment__submit').click(
        (eventObject) => {
          // Override default form submission
          eventObject.preventDefault();

          // Handle the click
          view.selfAssess();
        },
      );
    }

    /**
     Enable/disable the self assess button.
     Check that whether the self assess button is enabled.

     Args:
     enabled (bool): If specified, set the state of the button.

     Returns:
     bool: Whether the button is enabled.

     Examples:
     >> view.selfSubmitEnabled(true);  // enable the button
     >> view.selfSubmitEnabled();  // check whether the button is enabled
     >> true
     * */
    selfSubmitEnabled(enabled) {
      return this.baseView.buttonEnabled('.self-assessment--001__assessment__submit', enabled);
    }

    /**
     * Called when something is selected or typed in the assessment rubric.
     * Used to set the unsaved changes warning dialog.
     *
     * @param {boolean} changesExist true if unsaved changes exist
     */
    assessmentRubricChanges(changesExist) {
      if (changesExist) {
        this.baseView.unsavedWarningEnabled(
          true,
          this.UNSAVED_WARNING_KEY,
          // eslint-disable-next-line max-len
          gettext('If you leave this page without submitting your self assessment, you will lose any work you have done.'),
        );
      }
    }

    /**
    Send a self-assessment to the server and update the view.
    * */
    selfAssess() {
      // Send the assessment to the server
      const view = this;
      const { baseView } = this;
      const usageID = baseView.getUsageID();
      baseView.toggleActionError('self', null);
      view.selfSubmitEnabled(false);

      this.server.selfAssess(
        this.rubric.optionsSelected(),
        this.rubric.criterionFeedback(),
        this.rubric.overallFeedback(),
      ).done(
        () => {
          baseView.unsavedWarningEnabled(false, view.UNSAVED_WARNING_KEY);
          view.announceStatus = true;
          baseView.loadAssessmentModules(usageID);
        },
      ).fail((errMsg) => {
        baseView.toggleActionError('self', errMsg);
        view.selfSubmitEnabled(true);
      });
    }
}

export default SelfView;
