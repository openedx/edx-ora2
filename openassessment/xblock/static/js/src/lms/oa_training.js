/**
Interface for student training view.

Args:
    element (DOM element): The DOM element representing the XBlock.
    server (OpenAssessment.Server): The interface to the XBlock server.
    baseView (OpenAssessment.BaseView): Container view.

Returns:
    OpenAssessment.StudentTrainingView
**/
OpenAssessment.StudentTrainingView = function(element, server, baseView) {
    this.element = element;
    this.server = server;
    this.baseView = baseView;
    this.rubric = null;
    this.isRendering = false;
    this.announceStatus = false;
    this.dateFactory = new OpenAssessment.DateTimeFactory(this.element);
};

OpenAssessment.StudentTrainingView.prototype = {

    /**
    Load the student training view.
    **/
    load: function(usageID) {
        var view = this;
        var stepID = '.step--student-training';
        var focusID = '[id=\'oa_training_' + usageID + '\']';
        view.isRendering = true;
        this.server.render('student_training').done(
            function(html) {
                // Load the HTML and install event handlers
                $(stepID, view.element).replaceWith(html);
                view.isRendering = false;
                view.server.renderLatex($(stepID, view.element));
                view.installHandlers();

                view.baseView.announceStatusChangeToSRandFocus(stepID, usageID, false, view, focusID);
                view.announceStatus = false;
                view.dateFactory.apply();
            }
        ).fail(function() {
            view.baseView.showLoadError('student-training');
        });
    },

    /**
    Install event handlers for the view.
    **/
    installHandlers: function() {
        var sel = $('.step--student-training', this.element);
        var view = this;

        // Install a click handler for collapse/expand
        this.baseView.setUpCollapseExpand(sel);

        // Initialize the rubric
        var rubricSelector = $('.student-training--001__assessment', this.element);
        if (rubricSelector.size() > 0) {
            var rubricElement = rubricSelector.get(0);
            this.rubric = new OpenAssessment.Rubric(rubricElement);
        }

        // Install a change handler for rubric options to enable/disable the submit button
        if (this.rubric !== null) {
            this.rubric.canSubmitCallback($.proxy(this.assessButtonEnabled, this));
        }

        // Install a click handler for submitting the assessment
        sel.find('.student-training--001__assessment__submit').click(
            function(eventObject) {
                // Override default form submission
                eventObject.preventDefault();

                // Handle the click
                view.assess();
                view.announceStatus = true;
            }
        );
    },

    /**
    Submit an assessment for the training example.
    **/
    assess: function() {
        // Immediately disable the button to prevent resubmission
        this.assessButtonEnabled(false);

        var options = {};
        if (this.rubric !== null) {
            options = this.rubric.optionsSelected();
        }
        var view = this;
        var baseView = this.baseView;
        var usageID = baseView.getUsageID();
        this.server.trainingAssess(options).done(
            function(corrections) {
                var incorrect = $('.openassessment__student-training--incorrect', view.element);
                var instructions = $('.openassessment__student-training--instructions', view.element);
                var $questionAnswers = $('.question__answers', view.rubric.element);

                if (!view.rubric.showCorrections(corrections)) {
                    view.load(usageID);
                    baseView.loadAssessmentModules(usageID);
                    incorrect.addClass('is--hidden');
                    instructions.removeClass('is--hidden');
                } else {
                    instructions.addClass('is--hidden');
                    incorrect.removeClass('is--hidden');
                    $questionAnswers.each(function(index, answer) {
                        var $notification = $('.step__message.message', view.rubric.element).not('.is--hidden');
                        $(answer).attr('aria-describedby', $($notification[index]).attr('id'));
                    });
                    baseView.srReadTexts([gettext('Feedback available for selection.')]);
                }
                baseView.scrollToTop('.step--student-training');
            }
        ).fail(function(errMsg) {
            // Display the error
            baseView.toggleActionError('student-training', errMsg);

            // Re-enable the button to allow the user to resubmit
            view.assessButtonEnabled(true);
        });
    },

    /**
     Enable/disable the submit training assessment button.
     Check that whether the assessment button is enabled.

     Args:
     enabled (bool): If specified, set the state of the button.

     Returns:
     bool: Whether the button is enabled.

     Examples:
     >> view.assessButtonEnabled(true);  // enable the button
     >> view.assessButtonEnabled();  // check whether the button is enabled
     >> true
    **/
    assessButtonEnabled: function(isEnabled) {
        return this.baseView.buttonEnabled('.student-training--001__assessment__submit', isEnabled);
    },
};
