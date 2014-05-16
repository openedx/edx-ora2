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
                    if (sel.value == optionsSelected[sel.name]) {
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
        $(this.element).change(
            function() {
                var numChecked = $('input[type=radio]:checked', this).length;
                var numAvailable = $('.field--radio.assessment__rubric__question', this).length;
                var canSubmit = numChecked == numAvailable;
                callback(canSubmit);
            }
        );
    }
};
