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
        console.log("A");
        var view = this;
        var baseView = this.baseView;
        this.server.render('leaderboard').done(
            function(html) {
                // Load the HTML and install event handlers
                $('#openassessment__leaderboard', view.element).replaceWith(html);
                view.installHandlers();
            }
        ).fail(function(errMsg) {
            baseView.showLoadError('leaderboard', errMsg);
        });
    },

    /**
    Install event handlers for the view.
    **/
    installHandlers: function() {
        console.log("B");
        // Install a click handler for collapse/expand
        var sel = $('#openassessment__leaderboard', this.element);
        this.baseView.setUpCollapseExpand(sel);

//        // Install a click handler for assessment feedback
//        var view = this;
//        sel.find('#feedback__submit').click(function(eventObject) {
//            eventObject.preventDefault();
//            view.submitFeedbackOnAssessment();
//        });
    },

    /**
    Hide elements, including setting the aria-hidden attribute for screen readers.

    Args:
        sel (JQuery selector): The selector matching elements to hide.
        hidden (boolean): Whether to hide or show the elements.

    Returns:
        undefined
    **/
    setHidden: function(sel, hidden) {
        console.log("E");
        sel.toggleClass('is--hidden', hidden);
        sel.attr('aria-hidden', hidden ? 'true' : 'false');
    },

    /**
    Check whether elements are hidden.

    Args:
        sel (JQuery selector): The selector matching elements to hide.

    Returns:
        boolean
    **/
    isHidden: function(sel) {
        console.log("F");
        return sel.hasClass('is--hidden') && sel.attr('aria-hidden') == 'true';
    }
};
