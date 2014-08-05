/**
Interface for grade view.

Args:
    element (DOM element): The DOM element representing the XBlock.
    server (OpenAssessment.Server): The interface to the XBlock server.
    baseView (OpenAssessment.BaseView): Container view.

Returns:
    OpenAssessment.ResponseView
**/
OpenAssessment.GradeView = function(element, server, baseView) {
    this.element = element;
    this.server = server;
    this.baseView = baseView;
};


OpenAssessment.GradeView.prototype = {
    /**
    Load the grade view.
    **/
    load: function() {
        var view = this;
        var baseView = this.baseView;
        this.server.render('grade').done(
            function(html) {
                // Load the HTML and install event handlers
                $('#openassessment__grade', view.element).replaceWith(html);
                view.installHandlers();
            }
        ).fail(function(errMsg) {
            baseView.showLoadError('grade', errMsg);
        });
    },

    /**
    Install event handlers for the view.
    **/
    installHandlers: function() {
        // Install a click handler for collapse/expand
        var sel = $('#openassessment__grade', this.element);
        this.baseView.setUpCollapseExpand(sel);

        // Install a click handler for assessment feedback
        var view = this;
        sel.find('#feedback__submit').click(function(eventObject) {
            eventObject.preventDefault();
            view.submitFeedbackOnAssessment();
        });

        // Initialize track changes
        var trackChangesSelector = $(".submission__answer__display__content__edited", this.element);
        if (trackChangesSelector.size() > 0) {
            var trackChangesElement = trackChangesSelector.get(0);
            this.trackChanges = new OpenAssessment.TrackChangesView(trackChangesElement);
            view.baseView.displayTrackChangesView();
        }
    },

    /**
    Get or set the text for feedback on assessments.

    Args:
        text (string or undefined): The text of the assessment to set (optional).

    Returns:
        string or undefined: The text of the feedback.

    Example usage:
        >>> view.feedbackText('I liked my assessment');  // Set the feedback text
        >>> view.feedbackText();  // Retrieve the feedback text
        'I liked my assessment'
    **/
    feedbackText: function(text) {
        if (typeof text === 'undefined') {
            return $('#feedback__remarks__value', this.element).val();
        } else {
            $('#feedback__remarks__value', this.element).val(text);
        }
    },

    /**
    Get or set the options for feedback on assessments.

    Args:
        options (array of strings or undefined): List of options to check (optional).

    Returns:
        list of strings or undefined: The values of the options the user selected.

    Example usage:
        // Set the feedback options; all others will be unchecked
        >>> view.feedbackOptions('notuseful', 'disagree');

        // Retrieve the feedback options that are checked
        >>> view.feedbackOptions();
        [
            'These assessments were not useful.',
            'I disagree with the ways that my peers assessed me'
        ]
    **/
    feedbackOptions: function(options) {
        var view = this;
        if (typeof options === 'undefined') {
            return $.map(
                $('.feedback__overall__value:checked', view.element),
                function(element, index) { return $(element).val(); }
            );
        } else {
            // Uncheck all the options
            $('.feedback__overall__value', this.element).prop('checked', false);

            // Check the selected options
            $.each(options, function(index, opt) {
                $('#feedback__overall__value--' + opt, view.element).prop('checked', true);
            });
        }
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
        return sel.hasClass('is--hidden') && sel.attr('aria-hidden') == 'true';
    },

    /**
        Get or set the state of the feedback on assessment.

        Each state corresponds to a particular configuration of attributes
        in the DOM, which control what the user sees in the UI.

        Valid states are:
            'open': The user has not yet submitted feedback on assessments.
            'submitting': The user has submitted feedback, but the server has not yet responded.
            'submitted': The feedback was successfully submitted

        Args:
            newState (string or undefined): One of above states.

        Returns:
            string or undefined: The current state.

        Throws:
            'Invalid feedback state' if the DOM is not in one of the valid states.

        Example usage:
            >>> view.feedbackState();
            'open'
            >>> view.feedbackState('submitted');
            >>> view.feedbackState();
            'submitted'
    **/
    feedbackState: function(newState) {
        var containerSel = $('.submission__feedback__content', this.element);
        var instructionsSel = containerSel.find('.submission__feedback__instructions');
        var fieldsSel = containerSel.find('.submission__feedback__fields');
        var actionsSel = containerSel.find('.submission__feedback__actions');
        var transitionSel = containerSel.find('.transition__status');
        var messageSel = containerSel.find('.message--complete');

        if (typeof newState === 'undefined') {
            var isSubmitting = (
                containerSel.hasClass('is--transitioning') && containerSel.hasClass('is--submitting') &&
                !this.isHidden(transitionSel) && this.isHidden(messageSel) &&
                this.isHidden(instructionsSel) && this.isHidden(fieldsSel) && this.isHidden(actionsSel)
            );
            var hasSubmitted = (
                containerSel.hasClass('is--submitted') &&
                this.isHidden(transitionSel) && !this.isHidden(messageSel) &&
                this.isHidden(instructionsSel) && this.isHidden(fieldsSel) && this.isHidden(actionsSel)
            );
            var isOpen = (
                !containerSel.hasClass('is--submitted') &&
                !containerSel.hasClass('is--transitioning') && !containerSel.hasClass('is--submitting') &&
                this.isHidden(transitionSel) && this.isHidden(messageSel) &&
                !this.isHidden(instructionsSel) && !this.isHidden(fieldsSel) && !this.isHidden(actionsSel)
            );

            if (isOpen) { return 'open'; }
            else if (isSubmitting) { return 'submitting'; }
            else if (hasSubmitted) { return 'submitted'; }
            else { throw 'Invalid feedback state'; }
        }

        else {
            if (newState == 'open') {
                containerSel.toggleClass('is--transitioning', false);
                containerSel.toggleClass('is--submitting', false);
                containerSel.toggleClass('is--submitted', false);
                this.setHidden(instructionsSel, false);
                this.setHidden(fieldsSel, false);
                this.setHidden(actionsSel, false);
                this.setHidden(transitionSel, true);
                this.setHidden(messageSel, true);
            }

            else if (newState == 'submitting') {
                containerSel.toggleClass('is--transitioning', true);
                containerSel.toggleClass('is--submitting', true);
                containerSel.toggleClass('is--submitted', false);
                this.setHidden(instructionsSel, true);
                this.setHidden(fieldsSel, true);
                this.setHidden(actionsSel, true);
                this.setHidden(transitionSel, false);
                this.setHidden(messageSel, true);
            }

            else if (newState == 'submitted') {
                containerSel.toggleClass('is--transitioning', false);
                containerSel.toggleClass('is--submitting', false);
                containerSel.toggleClass('is--submitted', true);
                this.setHidden(instructionsSel, true);
                this.setHidden(fieldsSel, true);
                this.setHidden(actionsSel, true);
                this.setHidden(transitionSel, true);
                this.setHidden(messageSel, false);
            }
        }
    },

    /**
    Send assessment feedback to the server and update the view.
    **/
    submitFeedbackOnAssessment: function() {
        // Send the submission to the server
        var view = this;
        var baseView = this.baseView;

        // Disable the submission button to prevent duplicate submissions
        $("#feedback__submit", this.element).toggleClass('is--disabled', true);

        // Indicate to the user that we're starting to submit
        view.feedbackState('submitting');

        // Submit the feedback to the server
        // When the server reports success, update the UI to indicate that we'v submitted.
        this.server.submitFeedbackOnAssessment(
            this.feedbackText(), this.feedbackOptions()
        ).done(
            function() { view.feedbackState('submitted'); }
        ).fail(function(errMsg) {
            baseView.toggleActionError('feedback_assess', errMsg);
        });
    }
};
