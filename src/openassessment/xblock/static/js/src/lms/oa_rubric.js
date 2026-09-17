/**
Interface for reading and modifying a rubric.

Args:
    element (DOM element): The DOM element representing the rubric.

Returns:
    OpenAssessment.Rubric
* */
export class Rubric {
  constructor(element) {
    this.element = element;
  }

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

    * */
  criterionFeedback(criterionFeedback) {
    const selector = 'textarea.answer__value';
    const feedback = {};
    const rubric = this;
    $(selector, this.element).each(
      (index, sel) => {
        const criterionName = rubric.getCriterionName(sel);
        if (typeof criterionFeedback !== 'undefined') {
          $(sel).val(criterionFeedback[criterionName]);
          feedback[criterionName] = criterionFeedback[criterionName];
        } else {
          feedback[criterionName] = $(sel).val();
        }
      },
    );
    return feedback;
  }

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

    * */
  /* eslint-disable-next-line consistent-return */
  overallFeedback(overallFeedback) {
    const selector = '.assessment__rubric__question--feedback__value';
    if (typeof overallFeedback === 'undefined') {
      return $(selector, this.element).val();
    }
    $(selector, this.element).val(overallFeedback);
  }

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

    * */
  /* eslint-disable-next-line consistent-return */
  optionsSelected(optionsSelected) {
    const selector = 'input[type=radio]';
    const rubric = this;
    if (typeof optionsSelected === 'undefined') {
      const options = {};
      $(`${selector}:checked`, this.element).each(
        (index, sel) => {
          options[rubric.getCriterionName(sel)] = sel.value;
        },
      );
      return options;
    }
    // Uncheck all the options
    $(selector, this.element).prop('checked', false);

    // Check the selected options
    $(selector, this.element).each((index, sel) => {
      const criterionName = rubric.getCriterionName(sel);
      if (optionsSelected.hasOwnProperty(criterionName)) {
        if (sel.value === optionsSelected[criterionName]) {
          $(sel).prop('checked', true);
        }
      }
    });
  }

  /**
    Install a callback handler to be notified when
    the the user has selected options for all criteria and can submit the assessment.

    Args:
        callback (function): Callback function that accepts one argument, a boolean indicating
            whether the user is allowed to submit the rubric.

    * */
  canSubmitCallback(callback) {
    const rubric = this;

    // Set the initial state
    callback(rubric.canSubmit());

    // Install a handler to update on change
    $(this.element).on('change keyup drop paste',
      () => { callback(rubric.canSubmit()); });
  }

  /**
    Check whether the user has filled in all the required fields
    to be able to submit an assessment.

    Returns:
        boolean

    * */
  canSubmit() {
    const numChecked = $('input[type=radio]:checked', this.element).length;
    const numAvailable = $('.field--radio.assessment__rubric__question.has--options', this.element).length;
    let completedRequiredComments = true;
    $('textarea[required]', this.element).each(function () {
      const trimmedText = $.trim($(this).val());
      if (trimmedText === '') {
        completedRequiredComments = false;
      }
    });

    return (numChecked === numAvailable && completedRequiredComments);
  }

  /**
     * Install a callback handler to be notified when unsaved changes exist in a rubric form.
     *
     * @param {function} callback a function that accepts one argument, a boolean indicating
     *     whether the user has selected options or inserted text.
     */
  changesExistCallback(callback) {
    const rubric = this;

    // Set the initial state
    callback(rubric.changesExist());

    // Install a handler to update on change
    $(this.element).on('change keyup drop paste',
      () => { callback(rubric.changesExist()); });
  }

  /**
     * Helper method for determining of unsubmitted changes exist in the rubric.
     *
     * @return {boolean} true if unsubmitted changes exist.
     */
  changesExist() {
    const numChecked = $('input[type=radio]:checked', this.element).length;
    let textExists = false;

    $('textarea', this.element).each(function () {
      const trimmedText = $.trim($(this).val());
      if (trimmedText !== '') {
        textExists = true;
      }
    });

    return (numChecked > 0 || textExists);
  }

  /**
     Updates the rubric to display positive and negative messages on each
     criterion. For each correction provided, the associated criterion will have
     an appropriate message displayed.

     Args:
        Corrections (list): A list of corrections to the rubric criteria that
        did not match the expected selected options.

     Returns:
        True if there were errors found, False if there are no corrections.
     * */
  showCorrections(corrections) {
    const selector = 'input[type=radio]';
    let hasErrors = false;
    const rubric = this;
    // Display appropriate messages for each selection
    $(selector, this.element).each((index, sel) => {
      const listItem = $(sel).parents('.assessment__rubric__question');
      if (corrections.hasOwnProperty(rubric.getCriterionName(sel))) {
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

  /**
     * Gets the criterion name out of the data on the provided DOM element.
     *
     * @param {object} element
     * @return {String} value stored as data-criterion-name
     */
  getCriterionName(element) {
    return $(element).data('criterion-name');
  }
}

export default Rubric;
