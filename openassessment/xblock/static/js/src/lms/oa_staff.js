/**
 * Interface for staff assessment view.
 *
 * @param {Element} element - The DOM element representing the XBlock.
 * @param {OpenAssessment.Server} server - The interface to the XBlock server.
 * @param {OpenAssessment.BaseView} baseView - Container view.
 */
OpenAssessment.StaffView = function(element, server, baseView) {
    this.element = element;
    this.server = server;
    this.baseView = baseView;
    this.isRendering = false;
    this.announceStatus = false;

};

OpenAssessment.StaffView.prototype = {

    /**
     * Load the staff assessment view.
     **/
    load: function(usageID) {
        var view = this;
        var stepID = ".step--staff-assessment";
        var focusID = "[id='oa_staff_grade_" + usageID + "']";
        view.isRendering = true;

        this.server.render('staff_assessment').done(
            function(html) {
                $('.step--staff-assessment', view.element).replaceWith(html);
                view.isRendering = false;
                view.installHandlers();
                view.baseView.announceStatusChangeToSRandFocus(stepID, usageID, false, view, focusID);
            }
        ).fail(function() {
            view.baseView.showLoadError('staff-assessment');
        });
    },

    /**
    Install event handlers for the view.
    **/
    installHandlers: function() {
        // Install a click handler for collapse/expand
        this.baseView.setUpCollapseExpand($('.step--staff-assessment', this.element));
    },
};
