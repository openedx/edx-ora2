/**
Interface for leaderboard view.

Args:
    element (DOM element): The DOM element representing the XBlock.
    server (OpenAssessment.Server): The interface to the XBlock server.
    baseView (OpenAssessment.BaseView): Container view.

Returns:
    OpenAssessment.ResponseView
**/
OpenAssessment.LeaderboardView = function(element, server, baseView) {
    this.element = element;
    this.server = server;
    this.baseView = baseView;
};


OpenAssessment.LeaderboardView.prototype = {
    /**
    Load the leaderboard view.
    **/
    load: function() {
        var view = this;
        var baseView = this.baseView;
        this.server.render('leaderboard').done(
            function(html) {
                // Load the HTML and install event handlers
                $('#openassessment__leaderboard', view.element).replaceWith(html);
                view.server.renderLatex($('#openassessment__leaderboard', view.element));
            }
        ).fail(function(errMsg) {
            baseView.showLoadError('leaderboard', errMsg);
        });
    },
};
