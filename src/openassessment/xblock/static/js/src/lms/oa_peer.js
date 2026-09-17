import DateTimeFactory from './oa_datefactory';
import Rubric from './oa_rubric';

/**
Interface for peer asssessment view.

Args:
    element (DOM element): The DOM element representing the XBlock.
    server (OpenAssessment.Server): The interface to the XBlock server.
    baseView (OpenAssessment.BaseView): Container view.

Returns:
    OpenAssessment.PeerView
* */
export class PeerView {
    UNSAVED_WARNING_KEY = 'peer-assessment';

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

      this.load = this.load.bind(this);
      this.loadContinuedASsessment = this.loadContinuedAssessment.bind(this);
      this.continueAssessmentEnabled = this.continueAssessmentEnabled.bind(this);
      this.installHandlers = this.installHandlers.bind(this);
      this.peerSubmitEnabled = this.peerSubmitEnabled.bind(this);
      this.assessmentRubricChanges = this.assessmentRubricChanges.bind(this);
      this.continuedPeerAssess = this.continuedPeerAssess.bind(this);
      this.peerAssessRequest = this.peerAssessRequest.bind(this);
      this.peerAssess = this.peerAssess.bind(this);
      this.getUUID = this.getUUID.bind(this);
    }

    /**
    Load the peer assessment view.
    * */
    load(usageID) {
      const view = this;
      const stepID = '.step--peer-assessment';
      const focusID = `[id='oa_peer_${usageID}']`;

      view.isRendering = true;
      this.server.render('peer_assessment').done(
        (html) => {
          // Load the HTML and install event handlers
          $(stepID, view.element).replaceWith(html);
          view.isRendering = false;

          view.server.renderLatex($(stepID, view.element));

          this.renderResponseViaEditor();

          view.installHandlers(false);

          view.baseView.announceStatusChangeToSRandFocus(stepID, usageID, false, view, focusID);
          view.announceStatus = false;
          view.dateFactory.apply();
        },
      ).fail(() => {
        view.baseView.showLoadError('peer-assessment');
      });
      // Called to update Messagview with info on whether or not it was able to grab a submission
      // See detailed explanation/Methodology in oa_base.loadAssessmentModules
      view.baseView.loadMessageView();
    }

    /**
     Use Response Editor to render response
     * */
    renderResponseViaEditor() {
      const sel = $('.step--peer-assessment', this.element);
      const responseElements = sel.find('.submission__answer__part__text__value');
      this.responseEditorLoader.load(this.data.TEXT_RESPONSE_EDITOR, responseElements);
    }

    /**
    Load the continued grading version of the view.
    This is a version of the peer grading step that a student
    can use to continue assessing peers after they've completed
    their peer assessment requirements.
    * */
    loadContinuedAssessment(usageID) {
      const view = this;
      const stepID = '.step--peer-assessment';
      const focusID = `[id='oa_peer_${usageID}']`;

      view.continueAssessmentEnabled(false);
      view.isRendering = true;
      this.server.renderContinuedPeer().done(
        (html) => {
          // Load the HTML and install event handlers
          $('.step--peer-assessment', view.element).replaceWith(html);
          view.server.renderLatex($('.step--peer-assessment', view.element));
          view.isRendering = false;

          view.installHandlers(true);

          view.baseView.announceStatusChangeToSRandFocus(stepID, usageID, false, view, focusID);
        },
      ).fail(() => {
        view.baseView.showLoadError('peer-assessment');
        view.continueAssessmentEnabled(true);
      });
    }

    /**
    Enable and disable the continue assessment button.

    Args:
        enabled (bool): If specified, sets the button as enabled or disabled.
            if not specified, return the current value.

    Returns:
        A boolean. TRUE if the continue assessment button is enabled.

    * */
    continueAssessmentEnabled(enabled) {
      return this.baseView.buttonEnabled('.action--continue--grading', enabled);
    }

    /**
    Install event handlers for the view.

    Args:
        isContinuedAssessment (boolean): If true, we are in "continued grading" mode,
            meaning that the user is continuing to grade even though she has met
            the requirements.
    * */
    installHandlers(isContinuedAssessment) {
      const sel = $('.step--peer-assessment', this.element);
      const view = this;

      // Install a click handler for collapse/expand
      this.baseView.setUpCollapseExpand(sel);

      // Install click handler for the preview button
      this.baseView.bindLatexPreview(sel);

      // Initialize the rubric
      const rubricSelector = $('.peer-assessment--001__assessment', this.element);
      if (rubricSelector.size() > 0) {
        const rubricElement = rubricSelector.get(0);
        this.rubric = new Rubric(rubricElement);
      } else {
        // If there was previously a rubric visible, clear the reference to it.
        this.rubric = null;
      }

      // Install a change handler for rubric options to enable/disable the submit button
      if (this.rubric !== null) {
        this.rubric.canSubmitCallback($.proxy(view.peerSubmitEnabled, view));

        this.rubric.changesExistCallback($.proxy(view.assessmentRubricChanges, view));
      }

      // Install a click handler for assessment
      sel.find('.peer-assessment--001__assessment__submit').click(
        (eventObject) => {
          // Override default form submission
          eventObject.preventDefault();

          // Status will change in update announce it to the Screen Reader after Render
          view.announceStatus = true;

          // Handle the click
          if (!isContinuedAssessment) { view.peerAssess(); } else { view.continuedPeerAssess(); }
        },
      );

      // Install a click handler for continued assessment
      sel.find('.action--continue--grading').click(
        (eventObject) => {
          eventObject.preventDefault();
          view.loadContinuedAssessment(view.baseView.getUsageID());
        },
      );
    }

    /**
     Enable/disable the peer assess button button.
     Check that whether the peer assess button is enabled.

     Args:
     enabled (bool): If specified, set the state of the button.

     Returns:
     bool: Whether the button is enabled.

     Examples:
     >> view.peerSubmitEnabled(true);  // enable the button
     >> view.peerSubmitEnabled();  // check whether the button is enabled
     >> true
     * */
    peerSubmitEnabled(enabled) {
      return this.baseView.buttonEnabled('.peer-assessment--001__assessment__submit', enabled);
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
          gettext('If you leave this page without submitting your peer assessment, you will lose any work you have done.'),
        );
      }
    }

    /**
    Send an assessment to the server and update the view.
    * */
    peerAssess() {
      const view = this;
      const { baseView } = this;
      const usageID = baseView.getUsageID();
      this.peerAssessRequest(() => {
        baseView.unsavedWarningEnabled(false, view.UNSAVED_WARNING_KEY);
        baseView.loadAssessmentModules(usageID);
        baseView.scrollToTop('.step--peer-assessment');
      });
    }

    /**
     * Send an assessment to the server and update the view, with the assumption
     * that we are continuing peer assessments beyond the required amount.
     */
    continuedPeerAssess() {
      const view = this;
      const { gradeView } = this.baseView;
      const { baseView } = this;
      const usageID = baseView.getUsageID();
      this.peerAssessRequest(() => {
        baseView.unsavedWarningEnabled(false, view.UNSAVED_WARNING_KEY);
        view.loadContinuedAssessment(usageID);
        gradeView.load();
        baseView.scrollToTop('.step--peer-assessment');
      });
    }

    /**
    Common peer assessment request building, used for all types of peer assessments.

    Args:
        successfunction(function): The function called if the request is
            successful. This varies based on the type of request to submit
            a peer assessment.

    * */
    peerAssessRequest(successFunction) {
      const view = this;
      const uuid = this.getUUID();

      this.baseView.toggleActionError('peer', null);
      this.peerSubmitEnabled(false);

      // Pull the assessment info from the DOM and send it to the server
      this.server.peerAssess(
        this.rubric.optionsSelected(),
        this.rubric.criterionFeedback(),
        this.rubric.overallFeedback(),
        uuid,
      ).done(
        successFunction,
      ).fail((errMsg) => {
        view.baseView.toggleActionError('peer', errMsg);
        view.peerSubmitEnabled(true);
      });
    }

    /**
    Get uuid of a peer assessment.
    * */
    getUUID() {
      const xBlockElement = $(`div[data-usage-id='${this.baseView.getUsageID()}']`);
      return xBlockElement.find('.step--peer-assessment').data('submission-uuid');
    }
}

export default PeerView;
