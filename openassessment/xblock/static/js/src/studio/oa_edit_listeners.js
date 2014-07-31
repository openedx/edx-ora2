/**
Dynamically update student training examples based on
changes to the rubric.
**/
OpenAssessment.StudentTrainingListener = function() {
    this.element = $('#oa_student_training_editor');
    this.alert = new OpenAssessment.ValidationAlert();
};

OpenAssessment.StudentTrainingListener.prototype = {
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
        var view = this;
        var sel = '.openassessment_training_example_criterion[data-criterion="' + data.criterionName + '"]';
        $(sel, this.element).each(
            function() {
                var criterion = this;
                var option = $('option[value="' + data.name + '"]', criterion);
                $(option).text(view._generateOptionString(data.label, data.points));
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
        var options = $('.openassessment_training_example_criterion_option[data-criterion="' + data.criterionName + '"]');
        var view = this;
        var criterionAdded = false;
        var examplesUpdated = false;
        if (options.length === 0) {
            this.criterionAdd(data);
            criterionAdded = true;
        }

        $('.openassessment_training_example_criterion_option', this.element).each(function() {
            if ($(this).data('criterion') === data.criterionName) {
                var criterion = this;
                // Risky; making an assumption that options will remain simple.
                // updates could cause this to get out of sync with templates,
                // but this avoids overly complex templating code.
                $(criterion).append($("<option></option>")
                    .attr("value", data.name)
                    .text(view._generateOptionString(data.label, data.points)));
                examplesUpdated = true;
            }
        });

        if (criterionAdded && examplesUpdated) {
            this.displayAlertMsg(
                gettext("Criterion Addition requires Training Example Updates"),
                gettext("Because you added a criterion, student training examples will have to be updated.")
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
        $('.openassessment_training_example_criterion_option', this.element).each(function() {
            var criterionOption = this;
            if ($(criterionOption).data('criterion') === data.criterionName) {
                if ($(criterionOption).val() === data.name.toString()) {
                    $(criterionOption).val("");
                    $(criterionOption).addClass("openassessment_highlighted_field");
                    $(criterionOption).click(function() {
                        $(criterionOption).removeClass("openassessment_highlighted_field");
                    });
                    invalidated = true;
                }

                $('option[value="' + data.name + '"]', criterionOption).remove();

                // If all options have been removed from the Criterion, remove
                // the criterion entirely.
                if ($("option", criterionOption).length == 1) {
                    handler.removeAllOptions(data);
                    invalidated = false;
                }
            }
        });

        if (invalidated) {
            this.displayAlertMsg(
                gettext("Option Deletion Led to Invalidation"),
                gettext("Because you deleted an option, some student training examples had to be reset.")
            );
        }
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
            if ($(criterion).data('criterion') == data.criterionName) {
                $(criterion).remove();
                changed = true;
            }
        });

        if (changed) {
            this.displayAlertMsg(
                gettext("Option Deletion Led to Invalidation"),
                gettext("The deletion of the last criterion option caused the criterion to be removed in the student training examples.")
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
                gettext("Criterion Deletion Led to Invalidation"),
                gettext("Because you deleted a criterion, there were student training examples where the criterion had to be removed.")
            );
        }
    },

    /**
     Sets up the alert window based on a change message.

     Args:
         title (str): Title of the alert message.
         msg (str): Message body for the alert.

     */
    displayAlertMsg: function(title, msg) {
        this.alert.setMessage(title, msg);
        this.alert.show();
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
                $(".openassessment_training_example_criterion_name_wrapper", this)
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
        var criterion = $("#openassessment_training_example_criterion_template")
            .children().first()
            .clone()
            .removeAttr('id')
            .attr('data-criterion', data.criterionName)
            .toggleClass('is--hidden', false)
            .appendTo(".openassessment_training_example_criteria_selections", view);

        criterion.find(".openassessment_training_example_criterion_option")
            .attr('data-criterion', data.criterionName);
        criterion.find(".openassessment_training_example_criterion_name_wrapper")
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
        $(".openassessment_training_example_criteria_selections", this.element).each(
            function() {
                var exampleDescription = {};
                $(".openassessment_training_example_criterion", this).each(
                    function() {
                        var criterionName = $(this).data('criterion');
                        var criterionLabel = $(".openassessment_training_example_criterion_name_wrapper", this)
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
        $(".openassessment_training_example_criteria_selections", this.element).each(
            function() {
                var exampleDescription = {};
                $(".openassessment_training_example_criterion_option", this).each(
                    function() {
                        var criterionName = $(this).data('criterion');
                        exampleDescription[criterionName] = {};
                        $("option", this).each(
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

    /**
    Format the option label, including the point value.

    Args:
        name (string): The option label (e.g. "Good", "Fair").
        points (int): The number of points that the option is worth.

    Returns:
        string
    **/
    _generateOptionString: function(name, points) {
        return name + ' - ' + points + gettext(' points');
    }
};
