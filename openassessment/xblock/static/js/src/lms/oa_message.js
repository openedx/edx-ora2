/**
Interface for Message banner.

Args:
    element (DOM element): The DOM element representing the XBlock.
    server (OpenAssessment.Server): The interface to the XBlock server.
    baseView (OpenAssessment.BaseView): Container view.

Returns:
    OpenAssessment.ResponseView
**/
OpenAssessment.MessageView = function(element, server, baseView) {
    this.element = element;
    this.server = server;
    this.baseView = baseView;
};

OpenAssessment.MessageView.prototype = {
    /**
    Loads the message view.
    **/
    load: function() {
        var view = this;
        var baseView = this.baseView;
        this.server.render('message').done(
            function(html) {
                //Load the HTML
                $('#openassessment__message', view.element).replaceWith(html);
                view.server.renderLatex($('#openassessment__message', view.element));
            }
        ).fail(function(errMsg) {
            baseView.showLoadError('message', errMsg);
        });
    }
};
