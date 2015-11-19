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
};

OpenAssessment.StaffView.prototype = {

    /**
     * Load the staff assessment view.
     **/
    load: function() {
        var view = this;
        this.server.render('staff_assessment').done(
            function(html) {
                $('#openassessment__staff-assessment', view.element).replaceWith(html);
            }
        ).fail(function() {
            view.baseView.showLoadError('staff-assessment');
        });
    }
};
