/**
 Dynamically update student training examples based on
 changes to the prompts or the rubric.
 **/
OpenAssessment.StudentTrainingListener = function() {
    this.element = $('#oa_student_training_editor');
    this.alert = new OpenAssessment.ValidationAlert();
};

OpenAssessment.StudentTrainingListener.prototype = {

    /**
     Add a answer part in the training examples when a prompt is added.
     */
    promptAdd: function() {
        var view = this.element;
        $('#openassessment_training_example_part_template')
            .children().first()
            .clone()
            .removeAttr('id')
            .toggleClass('is--hidden', false)
            .appendTo('.openassessment_training_example_essay', view);
    },

    /**
     Remove the answer part in the training examples when a prompt is removed.
     */
    promptRemove: function(data) {
        var view = this.element;
        $('.openassessment_training_example_essay li:nth-child(' + (data.index + 1) + ')', view).remove();
    },

    /**
     Event handler for updating training examples when a criterion option has
     been updated.

     Args:
     criterionName (str): The name of the criterion that contains the updated
     option.
     name (str): The name of the option.
     label (str): The label for the option.
     points (int): The point value for the option.
     */
    optionUpdated: function(data) {
        this._optionSel(data.criterionName).each(
            function() {
                var criterion = this;
                var option = $('option[value="' + data.name + '"]', criterion)
                    .attr('data-points', data.points)
                    .attr('data-label', data.label);
                OpenAssessment.ItemUtilities.refreshOptionString(option);
            }
        );
    },

    /**
     Update the available options for a particular criterion. If this is the
     first option for a criterion, the criterion needs to be created for each
     example as well.

     Since names are unique, and set server side for new criteria and options,
     this will use the label for but the name and label attributes in the
     HTML. This will be resolved server-side.

     Args:
     criterionName (str): The name of the criterion that will have an
     additional option.
     name (str): The name of the new option.
     label (str): The new option label.
     points (int): The point value of the new option.
     */
    optionAdd: function(data) {
        // First, check to see if the criterion exists on the training examples
        var criterionAdded = false;
        if (this._optionSel(data.criterionName).length === 0) {
            this.criterionAdd(data);
            criterionAdded = true;
        }

        this._optionSel(data.criterionName).each(function() {
            var criterion = this;
            // Risky; making an assumption that options will remain simple.
            // updates could cause this to get out of sync with templates,
            // but this avoids overly complex templating code.
            var option = $('<option></option>')
                .attr('value', data.name)
                .attr('data-points', data.points)
                .attr('data-label', data.label);

            // Sets the option's text description, and adds it to the criterion.
            OpenAssessment.ItemUtilities.refreshOptionString(option);
            $(criterion).append(option);
        });

        if (criterionAdded) {
            this.displayAlertMsg(
                gettext('Criterion Added'),
                // eslint-disable-next-line max-len
                gettext('You have added a criterion. You will need to select an option for the criterion in the Learner Training step. To do this, click the Settings tab.')
            );
        }
    },

    /**
     Event handler for when an option is removed from a criterion on the rubric.
     Training examples will be updated accordingly when this occurs, and the
     user is notified that these changes have effected other sections of the
     configuration.

     If this is the last option in the criterion, removeAllOptions should be
     invoked.

     Args:
     criterionName (str): The name of the criterion where the option is
     being removed.
     name (str): The option being removed.

     */
    optionRemove: function(data) {
        var handler = this;
        var invalidated = false;
        this._optionSel(data.criterionName).each(function() {
            var criterionOption = this;
            if ($(criterionOption).val() === data.name.toString()) {
                $(criterionOption).val('')
                    .addClass('openassessment_highlighted_field')
                    .click(function() {
                        $(criterionOption).removeClass('openassessment_highlighted_field');
                    });
                invalidated = true;
            }

            $('option[value="' + data.name + '"]', criterionOption).remove();

            // If all options have been removed from the Criterion, remove
            // the criterion entirely.
            if ($('option', criterionOption).length === 1) {
                handler.removeAllOptions(data);
                invalidated = false;
            }
        });

        if (invalidated) {
            this.displayAlertMsg(
                gettext('Option Deleted'),
                // eslint-disable-next-line max-len
                gettext('You have deleted an option. That option has been removed from its criterion in the sample responses in the Learner Training step. You might have to select a new option for the criterion.')
            );
        }
    },

    _optionSel: function(criterionName) {
        return $(
            '.openassessment_training_example_criterion_option[data-criterion="' + criterionName + '"]',
            this.element
        );
    },

    /**
     Event handler for when all options are removed from a criterion. Right now,
     the logic is the same as if the criterion was removed. When all options are
     removed, training examples should be updated and the user should be
     notified.

     Args:
     criterionName (str): The criterion where all options have been removed.

     */
    removeAllOptions: function(data) {
        var changed = false;
        $('.openassessment_training_example_criterion', this.element).each(function() {
            var criterion = this;
            if ($(criterion).data('criterion') === data.criterionName) {
                $(criterion).remove();
                changed = true;
            }
        });

        if (changed) {
            this.displayAlertMsg(
                gettext('Option Deleted'),
                // eslint-disable-next-line max-len
                gettext('You have deleted all the options for this criterion. The criterion has been removed from the sample responses in the Learner Training step.')
            );
        }
    },

    /**
     Event handler for when a criterion is removed from the rubric. If a
     criterion is removed, we should ensure that the traing examples are updated
     to reflect this change.

     Args:
     criterionName (str): The name of the criterion removed.

     */
    criterionRemove: function(data) {
        var changed = false;
        var sel = '.openassessment_training_example_criterion[data-criterion="' + data.criterionName + '"]';
        $(sel, this.element).each(
            function() {
                $(this).remove();
                changed = true;
            }
        );

        if (changed) {
            this.displayAlertMsg(
                gettext('Criterion Deleted'),
                // eslint-disable-next-line max-len
                gettext('You have deleted a criterion. The criterion has been removed from the example responses in the Learner Training step.')
            );
        }
    },

    /**
     Sets up the alert window based on a change message. Checks that there is
     at least one training example, and that student training is enabled.

     Args:
     title (str): Title of the alert message.
     msg (str): Message body for the alert.

     */
    displayAlertMsg: function(title, msg) {
        if ($('#include_student_training', this.element).is(':checked') &&
        // Check for at least more than one example, to exclude the template
            $('.openassessment_training_example', this.element).length > 1) {
            this.alert.setMessage(title, msg).show();
        }
    },

    /**
     Handler for modifying the criterion label on every example, when the label
     has changed in the rubric.

     Args:
     criterionName (str): Name of the criterion
     criterionLabel (str): New label to replace on the training examples.
     */
    criterionUpdated: function(data) {
        var sel = '.openassessment_training_example_criterion[data-criterion="' + data.criterionName + '"]';
        $(sel, this.element).each(
            function() {
                $('.openassessment_training_example_criterion_name_wrapper', this)
                    .text(data.criterionLabel);
            }
        );
    },

    /**
     Event handler used to generate a new criterion on each training example
     when a criterion is created, and the first option is added. This should
     update all examples as well as the template used to create new training
     examples.

     Args:
     criterionName (str): The name of the criterion being added.
     label (str): The label for the new criterion.
     */
    criterionAdd: function(data) {
        var view = this.element;
        var criterion = $('#openassessment_training_example_criterion_template')
            .children().first()
            .clone()
            .removeAttr('id')
            .attr('data-criterion', data.criterionName)
            .toggleClass('is--hidden', false)
            .appendTo('.openassessment_training_example_criteria_selections', view);

        criterion.find('.openassessment_training_example_criterion_option')
            .attr('data-criterion', data.criterionName);
        criterion.find('.openassessment_training_example_criterion_name_wrapper')
            .text(data.label);
    },

    /**
     Retrieve the available criteria labels for training examples.
     This is mainly useful for testing.

     The returned array will always contain an extra example
     for the client-side template for new examples.

     Returns:
     Array of object literals mapping criteria names to labels.

     Example usage:
     >>> listener.examplesCriteriaLabels();
     >>> [
     >>>     { criterion_1: "abcd", criterion_2: "xyz" },
     >>>     { criterion_1: "abcd", criterion_2: "xyz" }
     >>> ]

     **/
    examplesCriteriaLabels: function() {
        var examples = [];
        $('.openassessment_training_example_criteria_selections', this.element).each(
            function() {
                var exampleDescription = {};
                $('.openassessment_training_example_criterion', this).each(
                    function() {
                        var criterionName = $(this).data('criterion');
                        var criterionLabel = $('.openassessment_training_example_criterion_name_wrapper', this)
                            .text().trim();
                        exampleDescription[criterionName] = criterionLabel;
                    }
                );
                examples.push(exampleDescription);
            }
        );
        return examples;
    },

    /**
     Retrieve the available option labels for training examples.
     This is mainly useful for testing.

     The returned array will always contain an extra example
     for the client-side template for new examples.

     Returns:
     Array of object literals

     Example usage:
     >>> listener.examplesOptionsLabels();
     >>> [
     >>>     {
        >>>         criterion_1: {
        >>>             "": "Not Scored",
        >>>             option_1: "First Option - 1 points",
        >>>             option_2: "Second Option - 2 points",
        >>>         }
        >>>     },
     >>>     {
        >>>         criterion_1: {
        >>>             "": "Not Scored",
        >>>             option_1: "First Option - 1 points",
        >>>             option_2: "Second Option - 2 points",
        >>>         }
        >>>     }
     >>> ]
     **/
    examplesOptionsLabels: function() {
        var examples = [];
        $('.openassessment_training_example_criteria_selections', this.element).each(
            function() {
                var exampleDescription = {};
                $('.openassessment_training_example_criterion_option', this).each(
                    function() {
                        var criterionName = $(this).data('criterion');
                        exampleDescription[criterionName] = {};
                        $('option', this).each(
                            function() {
                                var optionName = $(this).val();
                                var optionLabel = $(this).text().trim();
                                exampleDescription[criterionName][optionName] = optionLabel;
                            }
                        );
                    }
                );
                examples.push(exampleDescription);
            }
        );
        return examples;
    },
};

/**
 Show a warning when a user disables an assessment,
 since any data in the disabled section won't be persisted
 on save.
 **/
OpenAssessment.AssessmentToggleListener = function() {
    this.alert = new OpenAssessment.ValidationAlert();
};

OpenAssessment.AssessmentToggleListener.prototype = {
    toggleOff: function() {
        this.alert.setMessage(
            gettext('Warning'),
            gettext('Changes to steps that are not selected as part of the assignment will not be saved.')
        ).show();
    },

    toggleOn: function() {
        this.alert.hide();
    },
};
