/**
 * Interface for staff assessment view.
 *
 * @param {Element} element - The DOM element representing the XBlock.
 * @param {OpenAssessment.Server} server - The interface to the XBlock server.
 * @param {OpenAssessment.BaseView} baseView - Container view.
 */
export class StaffView {
  constructor(element, server, baseView) {
    this.element = element;
    this.server = server;
    this.baseView = baseView;
    this.isRendering = false;
    this.announceStatus = false;
  }

  /**
     * Load the staff assessment view.
     * */
  load(usageID) {
    const view = this;
    const stepID = '.step--staff-assessment';
    const focusID = `[id='oa_staff_grade_${usageID}']`;
    view.isRendering = true;

    this.server.render('staff_assessment').done(
      (html) => {
        $('.step--staff-assessment', view.element).replaceWith(html);
        view.isRendering = false;
        view.installHandlers();
        view.baseView.announceStatusChangeToSRandFocus(stepID, usageID, false, view, focusID);
      },
    ).fail(() => {
      view.baseView.showLoadError('staff-assessment');
    });
  }

  /**
    Install event handlers for the view.
    * */
  installHandlers() {
    // Install a click handler for collapse/expand
    this.baseView.setUpCollapseExpand($('.step--staff-assessment', this.element));
  }
}

export default StaffView;
