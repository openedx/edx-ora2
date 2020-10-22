/**
Interface for leaderboard view.

Args:
    element (DOM element): The DOM element representing the XBlock.
    server (OpenAssessment.Server): The interface to the XBlock server.
    baseView (OpenAssessment.BaseView): Container view.

Returns:
    OpenAssessment.ResponseView
* */
export class LeaderboardView {
  constructor(element, server, baseView) {
    this.element = element;
    this.server = server;
    this.baseView = baseView;
  }

  /**
    Load the leaderboard view.
    * */
  load(usageID) {
    const view = this;
    const { baseView } = this;
    const stepID = '.step--leaderboard';

    this.server.render('leaderboard').done(
      (html) => {
        // Load the HTML and install event handlers
        $(stepID, view.element).replaceWith(html);
        view.server.renderLatex($(stepID, view.element));
        view.installHandlers();
        if (typeof usageID !== 'undefined'
                    && $(stepID, view.element).hasClass('is--showing')) {
          $(`[id='oa_leaderboard_${usageID}']`, view.element).focus();
        }
      },
    ).fail((errMsg) => {
      baseView.showLoadError('leaderboard', errMsg);
    });
  }

  /**
    Install event handlers for the view.
    * */
  installHandlers() {
    // Install a click handler for collapse/expand
    this.baseView.setUpCollapseExpand($('.step--leaderboard', this.element));
  }
}

export default LeaderboardView;
