/**
 * The GradeView class.
 *
 * @param {element} element - The DOM element representing the XBlock
 * @param {OpenAssessment.Server} server - The interface to the XBlock server
 * @param {OpenAssessment.BaseView} baseView - The container view.
 * @constructor
 */
OpenAssessment.GradeView = function(element, server, baseView) {
    this.element = element;
    this.server = server;
    this.baseView = baseView;
    this.announceStatus = false;
    this.isRendering = false;
    this.dateFactory = new OpenAssessment.DateTimeFactory(this.element);
};

OpenAssessment.GradeView.prototype = {
    /**
     * Load the grade view.
     */
    load: function(usageID) {
        var view = this;
        var baseView = this.baseView;
        var stepID = '.step--grade';
        var focusID = '[id=\'oa_grade_' + usageID + '\']';
        view.isRendering = true;
        this.server.render('grade').done(
            function(html) {
                // Load the HTML and install event handlers
                $(stepID, view.element).replaceWith(html);
                view.server.renderLatex($(stepID, view.element));
                view.isRendering = false;
                view.installHandlers();

                view.baseView.announceStatusChangeToSRandFocus(stepID, usageID, true, view, focusID);
                view.dateFactory.apply();
            }
        ).fail(function(errMsg) {
            baseView.showLoadError('grade', errMsg);
        });
    },

    /**
     * Install event handlers for the view.
     */
    installHandlers: function() {
        // Install a click handler for collapse/expand
        var sel = $('.step--grade', this.element);
        this.baseView.setUpCollapseExpand(sel);

        // Install a click handler for assessment feedback
        var view = this;
        sel.find('.feedback__submit').click(function(eventObject) {
            eventObject.preventDefault();
            view.submitFeedbackOnAssessment();
        });
    },

    /**
     * Get or set the text for feedback on assessments.
     *
     * @param {string} text - The text of the assessment to set (optional).
     * @return {string} The text of the feedback
     */
    feedbackText: function(text) {
        var usageID = this.baseView.getUsageID() || '';
        if (typeof text === 'undefined') {
            return $('[id=\'feedback__remarks__value__' + usageID + '\']', this.element).val();
        } else {
            $('[id=\'feedback__remarks__value__' + usageID + '\']', this.element).val(text);
        }
    },

    /**
     * Get or set the options for feedback on assessments.
     *
     * @param {dict} options - List of options to check (optional).
     * @return {list} - The values of the options the user selected.
     */
    feedbackOptions: function(options) {
        var view = this;
        var usageID = this.baseView.getUsageID() || '';
        if (typeof options === 'undefined') {
            return $.map(
                $('.feedback__overall__value:checked', view.element),
                function(element) {return $(element).val();}
            );
        } else {
            // Uncheck all the options
            $('.feedback__overall__value', this.element).prop('checked', false);

            // Check the selected options
            $.each(options, function(index, opt) {
                $('[id=\'feedback__overall__value--' + opt + '__' + usageID + '\']', view.element)
                    .prop('checked', true);
            });
        }
    },

    /**
     * Hide elements, including setting the aria-hidden attribute for screen readers.
     *
     * @param {JQuery.selector} selector - The selector matching the elements to hide.
     * @param {boolean} hidden - Whether to hide or show the elements.
     */
    setHidden: function(selector, hidden) {
        selector.toggleClass('is--hidden', hidden);
        selector.attr('aria-hidden', hidden ? 'true' : 'false');
    },

    /**
     * Check whether elements are hidden.
     *
     * @param {JQuery.selector} selector - The selector matching the elements to check.
     * @return {boolean} - True if all the elements are hidden, else false.
     */
    isHidden: function(selector) {
        return selector.hasClass('is--hidden') && selector.attr('aria-hidden') === 'true';
    },

    /**
     * Get or set the state of the feedback on assessment.
     *
     * Each state corresponds to a particular configuration of attributes
     * in the DOM, which control what the user sees in the UI.
     *
     * Valid states are:
     *     'open': The user has not yet submitted feedback on assessments.
     *     'submitting': The user has submitted feedback, but the server has not yet responded.
     *     'submitted': The feedback was successfully submitted.
     *
     * @param {string} newState - the new state to set for the feedback (optional).
     * @return {*} The current state.
     */
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

            if (isOpen) {
                return 'open';
            } else if (isSubmitting) {
                return 'submitting';
            } else if (hasSubmitted) {
                return 'submitted';
            } else {
                throw new Error('Invalid feedback state');
            }
        } else {
            if (newState === 'open') {
                containerSel.toggleClass('is--transitioning', false);
                containerSel.toggleClass('is--submitting', false);
                containerSel.toggleClass('is--submitted', false);
                this.setHidden(instructionsSel, false);
                this.setHidden(fieldsSel, false);
                this.setHidden(actionsSel, false);
                this.setHidden(transitionSel, true);
                this.setHidden(messageSel, true);
            } else if (newState === 'submitting') {
                containerSel.toggleClass('is--transitioning', true);
                containerSel.toggleClass('is--submitting', true);
                containerSel.toggleClass('is--submitted', false);
                this.setHidden(instructionsSel, true);
                this.setHidden(fieldsSel, true);
                this.setHidden(actionsSel, true);
                this.setHidden(transitionSel, false);
                this.setHidden(messageSel, true);
            } else if (newState === 'submitted') {
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
     * Send assessment feedback to the server and update the view.
     */
    submitFeedbackOnAssessment: function() {
        // Send the submission to the server
        var view = this;
        var baseView = this.baseView;

        // Disable the submission button to prevent duplicate submissions
        $('.feedback__submit', this.element).prop('disabled', true);

        // Indicate to the user that we're starting to submit
        view.feedbackState('submitting');

        // Submit the feedback to the server
        // When the server reports success, update the UI to indicate that we'v submitted.
        this.server.submitFeedbackOnAssessment(
            this.feedbackText(), this.feedbackOptions()
        ).done(
            function() {view.feedbackState('submitted');}
        ).fail(function(errMsg) {
            baseView.toggleActionError('feedback_assess', errMsg);
        });
    },
};
