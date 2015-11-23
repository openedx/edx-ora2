/**
Interface for reading and modifying a rubric.

Args:
    element (DOM element): The DOM element representing the rubric.

Returns:
    OpenAssessment.Rubric
**/
OpenAssessment.Rubric = function(element) {
    this.element = element;
};

OpenAssessment.Rubric.prototype = {
    /**
    Get or set per-criterion feedback.

    Args:
        criterionFeedback (object literal or undefined):
            Map of criterion names to feedback strings.

    Returns:
        object literal or undefined

    Example usage:
        >>> view.criterionFeedback({'ideas': 'Good ideas'});  // Set per-criterion feedback
        >>> view.criterionFeedback(); // Retrieve criterion feedback
        {'ideas': 'Good ideas'}

    **/
    criterionFeedback: function(criterionFeedback) {
        var selector = 'textarea.answer__value';
        var feedback = {};
        $(selector, this.element).each(
            function(index, sel) {
                if (typeof criterionFeedback !== 'undefined') {
                    $(sel).val(criterionFeedback[sel.name]);
                    feedback[sel.name] = criterionFeedback[sel.name];
                }
                else {
                    feedback[sel.name] = $(sel).val();
                }
            }
        );
        return feedback;
    },

    /**
    Get or set overall feedback on the submission.

    Args:
        overallFeedback (string or undefined): The overall feedback text (optional).

    Returns:
        string or undefined

    Example usage:
        >>> view.overallFeedback('Good job!');  // Set the feedback text
        >>> view.overallFeedback();  // Retrieve the feedback text
        'Good job!'

    **/
    overallFeedback: function(overallFeedback) {
        var selector = '#assessment__rubric__question--feedback__value';
        if (typeof overallFeedback === 'undefined') {
            return $(selector, this.element).val();
        }
        else {
            $(selector, this.element).val(overallFeedback);
        }
    },

    /**
    Get or set the options selected in the rubric.

    Args:
        optionsSelected (object literal or undefined):
            Map of criterion names to option values.

    Returns:
        object literal or undefined

    Example usage:
        >>> view.optionsSelected({'ideas': 'Good'});  // Set the criterion option
        >>> view.optionsSelected(); // Retrieve the options selected
        {'ideas': 'Good'}

    **/
    optionsSelected: function(optionsSelected) {
        var selector = "input[type=radio]";
        if (typeof optionsSelected === 'undefined') {
            var options = {};
            $(selector + ":checked", this.element).each(
                function(index, sel) {
                    options[sel.name] = sel.value;
                }
            );
            return options;
        }
        else {
            // Uncheck all the options
            $(selector, this.element).prop('checked', false);

            // Check the selected options
            $(selector, this.element).each(function(index, sel) {
                if (optionsSelected.hasOwnProperty(sel.name)) {
                    if (sel.value === optionsSelected[sel.name]) {
                        $(sel).prop('checked', true);
                    }
                }
            });
        }
    },

    /**
    Install a callback handler to be notified when
    the the user has selected options for all criteria and can submit the assessment.

    Args:
        callback (function): Callback function that accepts one argument, a boolean indicating
            whether the user is allowed to submit the rubric.

    **/
    canSubmitCallback: function(callback) {
        var rubric = this;

        // Set the initial state
        callback(rubric.canSubmit());

        // Install a handler to update on change
        $(this.element).on('change keyup drop paste',
            function() { callback(rubric.canSubmit()); }
        );
    },

    /**
    Check whether the user has filled in all the required fields
    to be able to submit an assessment.

    Returns:
        boolean

    **/
    canSubmit: function() {
        var numChecked = $('input[type=radio]:checked', this.element).length;
        var numAvailable = $('.field--radio.assessment__rubric__question.has--options', this.element).length;
        var completedRequiredComments = true;
        $('textarea[required]', this.element).each(function() {
            var trimmedText = $.trim($(this).val());
            if (trimmedText === "") {
                completedRequiredComments = false;
            }
        });

        return (numChecked === numAvailable && completedRequiredComments);
    },

    /**
     Updates the rubric to display positive and negative messages on each
     criterion. For each correction provided, the associated criterion will have
     an appropriate message displayed.

     Args:
        Corrections (list): A list of corrections to the rubric criteria that
        did not match the expected selected options.

     Returns:
        True if there were errors found, False if there are no corrections.
     **/
    showCorrections: function(corrections) {
        var selector = "input[type=radio]";
        var hasErrors = false;
        // Display appropriate messages for each selection
        $(selector, this.element).each(function(index, sel) {
            var listItem = $(sel).parents(".assessment__rubric__question");
            if (corrections.hasOwnProperty(sel.name)) {
                hasErrors = true;
                listItem.find('.message--incorrect').removeClass('is--hidden');
                listItem.find('.message--correct').addClass('is--hidden');
            } else {
                listItem.find('.message--correct').removeClass('is--hidden');
                listItem.find('.message--incorrect').addClass('is--hidden');
            }
        });
        return hasErrors;
    }
};
