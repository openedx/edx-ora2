/**
Interface for staff assessment view.

Args:
    element (DOM element): The DOM element representing the XBlock.
    server (OpenAssessment.Server): The interface to the XBlock server.
    baseView (OpenAssessment.BaseView): Container view.

Returns:
    OpenAssessment.StaffView
**/

OpenAssessment.StaffView = function(element, server, baseView) {
    this.element = element;
    this.server = server;
    this.baseView = baseView;
};

OpenAssessment.StaffView.prototype = {

    /**
     Load the staff assessment view.
     **/
    load: function () {
        var view = this;
        this.server.render('staff_assessment').done(
            function (html) {
                $('#openassessment__staff-assessment', view.element).replaceWith(html);
            }
        ).fail(function () {
            view.baseView.showLoadError('staff-assessment');
        });
    }
};
