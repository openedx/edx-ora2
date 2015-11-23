/**
Interface for self assessment view.

Args:
    element (DOM element): The DOM element representing the XBlock.
    server (OpenAssessment.Server): The interface to the XBlock server.
    baseView (OpenAssessment.BaseView): Container view.

Returns:
    OpenAssessment.SelfView
**/
OpenAssessment.SelfView = function(element, server, baseView) {
    this.element = element;
    this.server = server;
    this.baseView = baseView;
    this.rubric = null;
};

OpenAssessment.SelfView.prototype = {

    /**
    Load the self assessment view.
    **/
    load: function() {
        var view = this;
        this.server.render('self_assessment').done(
            function(html) {
                // Load the HTML and install event handlers
                $('#openassessment__self-assessment', view.element).replaceWith(html);
                view.server.renderLatex($('#openassessment__self-assessment', view.element));
                view.installHandlers();
            }
        ).fail(function() {
            view.showLoadError('self-assessment');
        });
    },

    /**
    Install event handlers for the view.
    **/
    installHandlers: function() {
        var view = this;
        var sel = $('#openassessment__self-assessment', view.element);

        // Install a click handler for collapse/expand
        this.baseView.setUpCollapseExpand(sel);

        // Initialize the rubric
        var rubricSelector = $("#self-assessment--001__assessment", this.element);
        if (rubricSelector.size() > 0) {
            var rubricElement = rubricSelector.get(0);
            this.rubric = new OpenAssessment.Rubric(rubricElement);
        }

        // Install a change handler for rubric options to enable/disable the submit button
        if (this.rubric !== null) {
            this.rubric.canSubmitCallback($.proxy(this.selfSubmitEnabled, this));
        }

        // Install a click handler for the submit button
        sel.find('#self-assessment--001__assessment__submit').click(
            function(eventObject) {
                // Override default form submission
                eventObject.preventDefault();

                // Handle the click
                view.selfAssess();
            }
        );
    },

    /**
     Enable/disable the self assess button.
     Check that whether the self assess button is enabled.

     Args:
     enabled (bool): If specified, set the state of the button.

     Returns:
     bool: Whether the button is enabled.

     Examples:
     >> view.selfSubmitEnabled(true);  // enable the button
     >> view.selfSubmitEnabled();  // check whether the button is enabled
     >> true
     **/
    selfSubmitEnabled: function(enabled) {
        var button = $('#self-assessment--001__assessment__submit', this.element);
        if (typeof enabled === 'undefined') {
            return !button.hasClass('is--disabled');
        } else {
            button.toggleClass('is--disabled', !enabled);
        }
    },

    /**
    Send a self-assessment to the server and update the view.
    **/
    selfAssess: function() {
        // Send the assessment to the server
        var view = this;
        var baseView = this.baseView;
        baseView.toggleActionError('self', null);
        view.selfSubmitEnabled(false);

        this.server.selfAssess(
            this.rubric.optionsSelected(),
            this.rubric.criterionFeedback(),
            this.rubric.overallFeedback()
        ).done(
            function() {
                baseView.loadAssessmentModules();
                baseView.scrollToTop();
            }
        ).fail(function(errMsg) {
            baseView.toggleActionError('self', errMsg);
            view.selfSubmitEnabled(true);
        });
    }
};
