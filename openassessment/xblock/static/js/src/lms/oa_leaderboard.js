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
    load: function(usageID) {
        var view = this;
        var baseView = this.baseView;
        var stepID = ".step--leaderboard";

        this.server.render('leaderboard').done(
            function(html) {
                // Load the HTML and install event handlers
                $(stepID, view.element).replaceWith(html);
                view.server.renderLatex($(stepID, view.element));
                view.installHandlers();
                if (typeof usageID !== 'undefined' &&
                    $(stepID, view.element).hasClass("is--showing")) {
                    $("[id='oa_leaderboard_" + usageID + "']", view.element).focus();
                }
            }
        ).fail(function(errMsg) {
            baseView.showLoadError('leaderboard', errMsg);
        });
    },

    /**
    Install event handlers for the view.
    **/
    installHandlers: function() {
        // Install a click handler for collapse/expand
        this.baseView.setUpCollapseExpand($(".step--leaderboard", this.element));
    },
};
