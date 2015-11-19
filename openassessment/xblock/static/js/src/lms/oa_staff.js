/**
Interface for staff asssessment view.

Args:
    element (DOM element): The DOM element representing the XBlock.
    server (OpenAssessment.Server): The interface to the XBlock server.
    baseView (OpenAssessment.BaseView): Container view.

Returns:
    OpenAssessment.PeerView
**/

OpenAssessment.StaffView = function(element, server, baseView) {
    this.element = element;
    this.server = server;
    this.baseView = baseView;
    this.rubric = null;
};


OpenAssessment.StaffView.prototype = {

    /**
     Load the peer assessment view.
     **/
    load: function () {
        var view = this;
        this.server.render('staff_assessment').done(
            function (html) {
                // Load the HTML and install event handlers
                $('#openassessment__staff-assessment', view.element).replaceWith(html);
                view.server.renderLatex($('#openassessment__staff-assessment', view.element));
                //view.installHandlers(false);
            }
        ).fail(function () {
                view.baseView.showLoadError('staff-assessment');
            });
        //// Called to update Messageview with info on whether or not it was able to grab a submission
        //// See detailed explanation/Methodology in oa_base.loadAssessmentModules
        //view.baseView.loadMessageView();
    }
}