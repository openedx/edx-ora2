import Container from './oa_container';
import { RubricCriterion } from './oa_container_item';
import { Fields } from './oa_edit_fields';
import ValidationAlert from './oa_edit_validation_alert';
/**
 Interface for editing rubric definitions.

 Args:
 element (DOM element): The DOM element representing the rubric.
 notifier (OpenAssessment.Notifier): Used to notify other views about updates to the rubric.

 This view fires the following notification events:
 * optionAdd: An option was added to the rubric.
 * optionRemove: An option was removed from the rubric.
 * optionUpdated: An option's label and/or points were updated in the rubric.
 * criterionRemove: A criterion was removed from the rubric.
 * criterionUpdated: A criterion's label was updated in the rubric.

 * */
export class EditRubricView {
  constructor(element, notifier, server) {
    this.alert = new ValidationAlert();
    this.element = element;
    this.tabElement = $('#oa_edit_rubric_tab');

    this.notifier = notifier;
    this.server = server;
    this.criterionAddButton = $('#openassessment_rubric_add_criterion', this.element);
    this.criteriaContainer = new Container(
      RubricCriterion, {
        containerElement: $('#openassessment_criterion_list', this.element).get(0),
        templateElement: $('#openassessment_criterion_template', this.element).get(0),
        addButtonElement: $('#openassessment_rubric_add_criterion', this.element).get(0),
        removeButtonClass: 'openassessment_criterion_remove_button',
        containerItemClass: 'openassessment_criterion',
        notifier,
      },
    );
    this.criteriaContainer.addEventListeners();
    this.setupRubricReuse();
  }

  /**
   * Sets up the UI for rubric cloning.
   *
   * Setup JQuery-UI Accordion dropdown panel, autocomplete input, autocomplete/combobox button.
   * Load json representation of other course ORAs from rendered JSON
   * Install click handler on the "Clone" button to submit request and display success banner.
   */
  setupRubricReuse() {
    // If the section hasn't been rendered, rubric reuse isn't enabled, so return early
    if ($('#openassessment_rubric_clone', this.element).size() === 0) {
      return;
    }
    // Set up the accordion dropdown section
    $('#openassessment_rubric_clone', this.element).accordion({
      collapsible: true,
      heightStyle: 'content',
      icons: {
        header: false,
        activeHeader: false,
      },
    });
    // Load the rubric reuse data for the autocomplete
    const otherOraData = $.parseJSON(
      $('#openassessment_rubric_reuse_data', this.element).text(),
    ).map((otherOra) => (otherOra.location));

    // Setup the Autocomplete on the text input
    this.rubricAutocomplete = $('#openassessment_rubric_clone_input', this.element).autocomplete({
      delay: 0,
      minLength: 0,
      source: otherOraData,
    });

    // Setup the 'combobox' dropdown button. Based on https://jqueryui.com/autocomplete/#combobox
    this.rubricReuseAutocompleteWasOpen = false;
    $('.openassessment_clone_combobox_toggle', this.element)
      .button()
      .removeClass('ui-corner-all')
      .addClass('custom-combobox-toggle ui-corner-right')
      .on('mousedown', () => { this.handleRubricReuseComboboxButtonMousedown(); })
      .on('click', () => { this.handleRubricReuseComboboxButtonClick(); });

    // Setup click handler for the Clone button
    $('#openassessment_rubric_clone_button', this.element)
      .on('click', () => { this.handleRubricReuseCloneButtonClick(); });
    this.rubricCloneAlert = $('#openassessment_rubric_clone_alert', this.element);
  }

  handleRubricReuseComboboxButtonMousedown() {
    this.rubricReuseAutocompleteWasOpen = this.rubricAutocomplete.autocomplete('widget').is(':visible');
  }

  handleRubricReuseComboboxButtonClick() {
    this.rubricAutocomplete.trigger('focus');
    // Close if already visible
    if (this.rubricReuseAutocompleteWasOpen) {
      return;
    }
    // Pass empty string as value to search for, displaying all results
    this.rubricAutocomplete.autocomplete('search', '');
  }

  handleRubricReuseCloneButtonClick() {
    const blockId = $('#openassessment_rubric_clone_input', this.element).val();
    this.cloneRubric(blockId);
  }

  getTab() {
    return this.tabElement;
  }

  /**
   * Overwrite ORA rubric from existing rubric at location {rubricLocation}
   * @param {xblock-id} rubricLocation
   */
  cloneRubric(rubricLocation) {
    this.server.cloneRubric(rubricLocation).done((rubricData) => {
      this.alert.hide();
      this.setRubric(rubricData);
      this.displayRubricClonedMessage(rubricLocation);
    }).fail((errorMsg) => {
      this.alert.setMessage(gettext('Problem cloning rubric'), errorMsg);
      this.alert.show();
    });
  }

  setRubric(rubricData) {
    // Clear existing rubric data
    this.clearRubric();

    // Replace feedback prompt and default text
    this.feedbackPrompt(rubricData.feedback_prompt);
    this.feedback_default_text(rubricData.feedback_default_text);

    // Replace with new rubric data
    rubricData.criteria.forEach((criterion, criterionIndex) => {
      // Create a new criterion and update values
      this.addCriterion();
      const criterionItem = this.criteriaContainer.getItem(criterionIndex);
      criterionItem.label(criterion.label);
      criterionItem.prompt(criterion.prompt);
      criterionItem.feedback(criterion.feedback);

      // Add Criterion options
      criterion.options.forEach((option, optionIndex) => {
        this.addOption(criterionIndex);
        const optionItem = criterionItem.optionContainer.getItem(optionIndex);
        optionItem.label(option.label);
        optionItem.explanation(option.explanation);
        optionItem.points(option.points);

        // Update option in learner training
        optionItem.updateHandler();
      });

      // Update criterion in learner training
      criterionItem.updateHandler();
    });

    // Notify that the rubric has been replaced - clears training examples
    this.notifier.notificationFired('rubricReplaced', {});
  }

  /**
   * Clear all rubric data in the model & UI
   */
  clearRubric() {
    const rubricCriteria = this.getAllCriteria();

    $.each(rubricCriteria, (_i, elem) => {
      this.removeCriterion(elem);
    });

    this.feedbackPrompt('');
    this.feedback_default_text('');
  }

  /**
  * Show the .openassessment_rubric_clone_alert message banner, fading it out if it already exists.
  * args:
  *   - block_id: The block which the rubric is being cloned
  */
  displayRubricClonedMessage(blockId) {
    const view = this;
    if (this.rubricCloneAlert.is(':visible')) {
      this.rubricCloneAlert.fadeOut('fast', () => {
        view.createNewRubricClonedAlert(blockId);
      });
    } else {
      this.createNewRubricClonedAlert(blockId);
    }
  }

  /**
  * Helper method for displayRubricClonedMessage, sets text and displays the message banner
  * args:
  *   - blockId: The block which the rubric is being cloned
  */
  createNewRubricClonedAlert(blockId) {
    $('#openassessment_rubric_clone_alert_block_id', this.rubricCloneAlert).text(blockId);
    this.rubricCloneAlert.fadeIn('fast');
  }

  /**
     Construct a list of criteria definitions from the editor UI.

     Returns:
     list of criteria objects

     Example usage:
     >>> editRubricView.criteriaDefinition();
     [
     {
         name: "Criterion",
         prompt: "Prompt",
         order_num: 0,
         feedback: "disabled",
         options: [
             {
                 order_num: 0,
                 points: 1,
                 name: "Good",
                 explanation: "Explanation"
             }
             ...
         ]
     },
     ...
     ]

     * */
  criteriaDefinition() {
    const criteria = this.criteriaContainer.getItemValues();

    // Add order_num fields for criteria and options
    for (let criterionIndex = 0; criterionIndex < criteria.length; criterionIndex++) {
      const criterion = criteria[criterionIndex];
      criterion.order_num = criterionIndex;
      for (let optionIndex = 0; optionIndex < criterion.options.length; optionIndex++) {
        const option = criterion.options[optionIndex];
        option.order_num = optionIndex;
      }
    }

    return criteria;
  }

  /**
     Get or set the feedback prompt in the editor.
     This is the prompt shown to students when giving "overall" feedback
     on a submission.

     Args:
     text (string, optional): If provided, set the feedback prompt to this value.

     Returns:
     string

     * */
  feedbackPrompt(text) {
    const sel = $('#openassessment_rubric_feedback', this.element);
    return Fields.stringField(sel, text);
  }

  /**
     Get or set the default feedback response text in the editor.
     The text is used as a student's default response to the feedback
     prompt.

     Args:
     text (string, option): If provided, sets the default text to this value.

     Returns:
     string

     * */
  /* eslint-disable-next-line camelcase */
  feedback_default_text(text) {
    const sel = $('#openassessment_rubric_feedback_default_text', this.element);
    return Fields.stringField(sel, text);
  }

  /**
     Add a new criterion to the rubric.
     Uses a client-side template to create the new criterion.
     * */
  addCriterion() {
    this.criteriaContainer.add();
  }

  /**
     Remove a criterion from the rubric.

     Args:
     item (OpenAssessment.RubricCriterion): The criterion item to remove.
     * */
  removeCriterion(item) {
    this.criteriaContainer.remove(item);
  }

  /**
     Retrieve all criteria from the rubric.

     Returns:
     Array of OpenAssessment.RubricCriterion objects.

     * */
  getAllCriteria() {
    return this.criteriaContainer.getAllItems();
  }

  /**
     Retrieve a criterion item from the rubric.

     Args:
     index (int): The index of the criterion, starting from 0.

     Returns:
     OpenAssessment.RubricCriterion or null

     * */
  getCriterionItem(index) {
    return this.criteriaContainer.getItem(index);
  }

  /**
     Add a new option to the rubric.

     Args:
     criterionIndex (int): The index of the criterion to which
     the option will be added (starts from 0).

     * */
  addOption(criterionIndex) {
    const criterionItem = this.getCriterionItem(criterionIndex);
    criterionItem.optionContainer.add();
  }

  /**
     Remove an option from the rubric.

     Args:
     criterionIndex (int): The index of the criterion, starting from 0.
     item (OpenAssessment.RubricOption): The option item to remove.

     * */
  removeOption(criterionIndex, item) {
    const criterionItem = this.getCriterionItem(criterionIndex);
    criterionItem.optionContainer.remove(item);
  }

  /**
     Retrieve all options for a particular criterion.

     Args:
     criterionIndex (int): The index of the criterion, starting from 0.

     Returns:
     Array of OpenAssessment.RubricOption
     * */
  getAllOptions(criterionIndex) {
    const criterionItem = this.getCriterionItem(criterionIndex);
    return criterionItem.optionContainer.getAllItems();
  }

  /**
     Retrieve a particular option from the rubric.

     Args:
     criterionIndex (int): The index of the criterion, starting from 0.
     optionIndex (int): The index of the option within the criterion,
     starting from 0.

     Returns:
     OpenAssessment.RubricOption

     * */
  getOptionItem(criterionIndex, optionIndex) {
    const criterionItem = this.getCriterionItem(criterionIndex);
    return criterionItem.optionContainer.getItem(optionIndex);
  }

  /**
     Mark validation errors.

     Returns:
     Boolean indicating whether the view is valid.

     * */
  validate() {
    const criteria = this.getAllCriteria();
    let isValid = criteria.length > 0;
    if (!isValid) {
      this.criterionAddButton
        .addClass('openassessment_highlighted_field')
        .attr('aria-invalid', true)
        .click(function () {
          $(this).removeClass('openassessment_highlighted_field');
          $(this).removeAttr('aria-invalid');
        });
    }

    $.each(criteria, function () {
      isValid = (this.validate() && isValid);
    });

    return isValid;
  }

  /**
     Return a list of validation errors visible in the UI.
     Mainly useful for testing.

     Returns:
     list of string

     * */
  validationErrors() {
    let errors = [];

    if (this.criterionAddButton.hasClass('openassessment_highlighted_field')) {
      errors.push('The rubric must contain at least one criterion');
    }

    // Sub-validates the criteria defined by the rubric
    $.each(this.getAllCriteria(), function () {
      errors = errors.concat(this.validationErrors());
    });

    return errors;
  }

  /**
     Clear all validation errors from the UI.
     * */
  clearValidationErrors() {
    this.criterionAddButton.removeClass('openassessment_highlighted_field');
    this.criterionAddButton.removeAttr('aria-invalid', true);

    $.each(this.getAllCriteria(), function () {
      this.clearValidationErrors();
    });
  }
}

export default EditRubricView;
