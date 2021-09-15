import Container from './oa_container';
import { Fields, IntField } from './oa_edit_fields';
import { oaTinyMCE } from './oa_tiny_mce';

export const ItemUtilities = {
  /**
     Utility method for creating a unique name given a set of
     options.

     Args:
     selector (JQuery selector): Selector used to find the relative attribute
     for the name.
     nameAttribute (str): The name of the attribute that stores the unique
     names for a particular set.

     Returns:
     A unique name for an object in the collection.
     */
  createUniqueName(selector, nameAttribute) {
    let index = 0;
    while (index <= selector.length) {
      if (selector.parent().find(`*[${nameAttribute}='${index}']`).length === 0) {
        return index.toString();
      }
      index++;
    }
    return index.toString();
  },

  /**
     Format the option label, including the point value, and add it to the option.
     Relies on the data-points and data-label attributes to provide information about the option.

     Args:
     element (Jquery Element): The element that represents the object.
     * */
  refreshOptionString(element) {
    const points = $(element).attr('data-points');
    let label = $(element).attr('data-label');
    const name = $(element).val();
    // We don't want the lack of a label to make it look like - 1 points.
    if (label === '') {
      label = gettext('Unnamed Option');
    }
    const singularString = `${label} - ${points} point`;
    const multipleString = `${label} - ${points} points`;

    // If the option's name value is the empty string, that indicates to us that it is not a user-specified option,
    // but represents the "Not Selected" option which all criterion drop-downs have. This is an acceptable
    // assumption because we require name (option value) to be a unique identifier for each option.
    let finalLabel = '';
    if (name === '') {
      finalLabel = gettext('Not Selected');
    } else if (Number.isNaN(points) || points === 'NaN') {
      // If the points are invalid, we'll be given NaN
      // Don't show this to the user.
      finalLabel = label;
    } else {
      // Otherwise, set the text of the option element to be the properly conjugated, translated string.
      finalLabel = ngettext(singularString, multipleString, points);
    }

    $(element).text(finalLabel);
  },
};

/**
 The Prompt Class is used to construct and maintain references to prompts from within a prompts
 container object. Constructs a new Prompt element.

 Args:
 element (OpenAssessment.Container): The container that the prompt is a member of.
 notifier (OpenAssessment.Notifier): Used to send notifications of updates to prompts.

 Returns:
 OpenAssessment.Prompt
 * */
export class Prompt {
  constructor(element, notifier) {
    this.element = element;
    this.notifier = notifier;
    this.tinyMCEEnabled = window.tinyMCE !== undefined;
    if (this.tinyMCEEnabled) {
      element = this.attachWysiwygToPrompt(element);
    }
  }

  /**
     Attach Wysiwyg editor to the textarea field.

     Args:
     el (OpenAssessment.Container): The container that the prompt is a member of.

     Returns:
     Updated OpenAssessment.Container

     * */
  attachWysiwygToPrompt(el) {
    const elId = $(el).find('textarea').attr('id');
    if (!elId) {
      /* jshint undef:false */
      const textarea = $(el).find('textarea');
      let text = $(textarea).val();
      const type = $(textarea).data('type');
      if (text && (type === 'text')) {
        text = _.escape(text).replace(/(?:\r\n|\r|\n)/g, '<br />');
        $(textarea).val(text);
      }
      const newElId = `${Date.now()}-textarea-${Math.random() * 100}`;
      $(textarea).attr('id', newElId).tinymce(oaTinyMCE(
        {
          base_asset_url: $('#openassessment_prompt_template').data('baseAssetUrl'),
        },
      ));
    }
    return $(el);
  }

  /**
     Finds the values currently entered in the Prompts's fields, and returns them.

     Returns:
     object literal of the form:
     {
         'description': 'Write a nice long essay about anything.'
     }
     * */
  getFieldValues() {
    const fields = {
      description: this.description(),
    };
    return fields;
  }

  /**
     Get or set the description of the prompt.

     Args:
     text (string, optional): If provided, set the description of the prompt.

     Returns:
     string

     * */
  /* eslint-disable-next-line consistent-return */
  description(text) {
    const sel = $('.openassessment_prompt_description', this.element);

    if (!this.tinyMCEEnabled) {
      return Fields.stringField(sel, text);
    }

    const tinyEl = window.tinyMCE.get(sel.attr('id'));
    if (text) {
      tinyEl.setContent(text);
    } else {
      return tinyEl.getContent();
    }
  }

  addEventListeners() {}

  /**
     Hook into the event handler for addition of a prompt.

     */
  addHandler() {
    this.notifier.notificationFired(
      'promptAdd',
      {
        index: this.element.index(),
      },
    );
  }

  /**
     Hook into the event handler for removal of a prompt.

     */
  removeHandler() {
    this.notifier.notificationFired(
      'promptRemove',
      {
        index: this.element.index(),
      },
    );
  }

  updateHandler() {}

  /**
     Mark validation errors.

     Returns:
     Boolean indicating whether the option is valid.

     * */
  validate() {
    return true;
  }

  /**
     Return a list of validation errors visible in the UI.
     Mainly useful for testing.

     Returns:
     list of strings

     * */
  validationErrors() {
    return [];
  }

  /**
     Clear all validation errors from the UI.
     * */
  clearValidationErrors() {}
}

/**
 The RubricOption Class used to construct and maintain references to rubric options from within an options
 container object. Constructs a new RubricOption element.

 Args:
 element (OpenAssessment.Container): The container that the option is a member of.
 notifier (OpenAssessment.Notifier): Used to send notifications of updates to rubric options.

 Returns:
 OpenAssessment.RubricOption
 * */
export class RubricOption {
  constructor(element, notifier) {
    this.element = element;
    this.notifier = notifier;
    this.pointsField = new IntField(
      $('.openassessment_criterion_option_points', this.element),
      { min: 0, max: 999 },
    );
  }

  /**
     Adds event listeners specific to this container item.
     * */
  addEventListeners() {
    // Install a focus out handler for container changes.
    $(this.element).focusout($.proxy(this.updateHandler, this));
  }

  /**
     Finds the values currently entered in the Option's fields, and returns them.

     Returns:
     object literal of the form:
     {
         'name': 'Real Bad',
         'points': 1,
         'explanation': 'Essay was primarily composed of emojis.'
     }
     * */
  getFieldValues() {
    const fields = {
      label: this.label(),
      points: this.points(),
      explanation: this.explanation(),
    };

    // New options won't have unique names assigned.
    // By convention, we exclude the "name" key from the JSON dict
    // sent to the server, and the server will assign a unique name.
    const nameString = Fields.stringField(
      $('.openassessment_criterion_option_name', this.element),
    );
    if (nameString !== '') { fields.name = nameString; }

    return fields;
  }

  /**
     Get or set the label of the option.

     Args:
     label (string, optional): If provided, set the label to this string.

     Returns:
     string

     * */
  label(label) {
    const sel = $('.openassessment_criterion_option_label', this.element);
    return Fields.stringField(sel, label);
  }

  /**
     Get or set the point value of the option.

     Args:
     points (int, optional): If provided, set the point value of the option.

     Returns:
     int

     * */
  points(points) {
    if (points !== undefined) { this.pointsField.set(points); }
    return this.pointsField.get();
  }

  /**
     Get or set the explanation for the option.

     Args:
     explanation (string, optional): If provided, set the explanation to this string.

     Returns:
     string

     * */
  explanation(explanation) {
    const sel = $('.openassessment_criterion_option_explanation', this.element);
    return Fields.stringField(sel, explanation);
  }

  /**
     Hook into the event handler for addition of a criterion option.

     */
  addHandler() {
    const criterionElement = $(this.element).closest('.openassessment_criterion');
    const criterionName = $(criterionElement).data('criterion');
    const criterionLabel = $('.openassessment_criterion_label', criterionElement).val();
    const options = $('.openassessment_criterion_option', this.element.parent());
    // Create the unique name for this option.
    const name = ItemUtilities.createUniqueName(options, 'data-option');

    // Set the criterion name and option name in the new rubric element.
    $(this.element)
      .attr('data-criterion', criterionName)
      .attr('data-option', name);
    $('.openassessment_criterion_option_name', this.element).attr('value', name);

    const fields = this.getFieldValues();
    this.notifier.notificationFired(
      'optionAdd',
      {
        criterionName,
        criterionLabel,
        name,
        label: fields.label,
        points: fields.points,
      },
    );
  }

  /**
     Hook into the event handler for removal of a criterion option.

     */
  removeHandler() {
    const criterionName = $(this.element).data('criterion');
    const optionName = $(this.element).data('option');
    this.notifier.notificationFired(
      'optionRemove',
      {
        criterionName,
        name: optionName,
      },
    );
  }

  /**
     Hook into the event handler when a rubric criterion option is
     modified.

     */
  updateHandler() {
    const fields = this.getFieldValues();
    const criterionName = $(this.element).data('criterion');
    const optionName = $(this.element).data('option');
    const optionLabel = fields.label;
    const optionPoints = fields.points;
    this.notifier.notificationFired(
      'optionUpdated',
      {
        criterionName,
        name: optionName,
        label: optionLabel,
        points: optionPoints,
      },
    );
  }

  /**
     Mark validation errors.

     Returns:
     Boolean indicating whether the option is valid.

     * */
  validate() {
    return this.pointsField.validate();
  }

  /**
     Return a list of validation errors visible in the UI.
     Mainly useful for testing.

     Returns:
     list of string

     * */
  validationErrors() {
    const hasError = (this.pointsField.validationErrors().length > 0);
    return hasError ? ['Option points are invalid'] : [];
  }

  /**
     Clear all validation errors from the UI.
     * */
  clearValidationErrors() {
    this.pointsField.clearValidationErrors();
  }
}

/**
 The RubricCriterion Class is used to construct and get information from a rubric element within
 the DOM.

 Args:
 element (JQuery Object): The selection which describes the scope of the criterion.
 notifier (OpenAssessment.Notifier): Used to send notifications of updates to rubric criteria.

 Returns:
 OpenAssessment.RubricCriterion
 * */
export class RubricCriterion {
  constructor(element, notifier) {
    this.element = element;
    this.notifier = notifier;
    this.labelSel = $('.openassessment_criterion_label', this.element);
    this.promptSel = $('.openassessment_criterion_prompt', this.element);
    this.optionContainer = new Container(RubricOption, {
      containerElement: $('.openassessment_criterion_option_list', this.element).get(0),
      templateElement: $('#openassessment_option_template').get(0),
      addButtonElement: $('.openassessment_criterion_add_option', this.element).get(0),
      removeButtonClass: 'openassessment_criterion_option_remove_button',
      containerItemClass: 'openassessment_criterion_option',
      notifier: this.notifier,
    });
    this.feedbackSel = $('.openassessment_criterion_feedback', this.element);
  }

  /**
     Invoked by the container to add event listeners to all child containers
     of this item, and add event listeners specific to this container item.
     * */
  addEventListeners() {
    this.optionContainer.addEventListeners();
    // Install a focus out handler for container changes.
    $(this.element).focusout($.proxy(this.updateHandler, this));
  }

  /**
     Finds the values currently entered in the Criterion's fields, and returns them.

     Returns:
     object literal of the form:
     {
         'name': 'Emoji Content',
         'prompt': 'How expressive was the author with their words, and how much did they rely on emojis?',
         'feedback': 'optional',
         'options': [
             {
                 'name': 'Real Bad',
                 'points': 1,
                 'explanation': 'Essay was primarily composed of emojis.'
             }
             ...
         ]
     }
     * */
  getFieldValues() {
    const fields = {
      label: this.label(),
      prompt: this.prompt(),
      feedback: this.feedback(),
      options: this.optionContainer.getItemValues(),
    };

    // New criteria won't have unique names assigned.
    // By convention, we exclude the "name" key from the JSON dict
    // sent to the server, and the server will assign a unique name.
    const nameString = Fields.stringField(
      $('.openassessment_criterion_name', this.element),
    );
    if (nameString !== '') { fields.name = nameString; }

    return fields;
  }

  /**
     Get or set the label of the criterion.

     Args:
     label (string, optional): If provided, set the label to this string.

     Returns:
     string

     * */
  label(label) {
    return Fields.stringField(this.labelSel, label);
  }

  /**
     Get or set the prompt of the criterion.

     Args:
     prompt (string, optional): If provided, set the prompt to this string.

     Returns:
     string

     * */
  prompt(prompt) {
    return Fields.stringField(this.promptSel, prompt);
  }

  /**
     Get or set the feedback value for the criterion.
     This is one of: "disabled", "optional", or "required".

     Returns:
     string

     * */
  feedback(feedback) {
    return Fields.selectField(this.feedbackSel, feedback);
  }

  /**
     Add an option to the criterion.
     Uses the client-side template to create the new option.
     * */
  addOption() {
    this.optionContainer.add();
  }

  /**
     Hook into the event handler for addition of a criterion.

     */
  addHandler() {
    const criteria = $('.openassessment_criterion', this.element.parent());
    // Create the unique name for this option.
    const name = ItemUtilities.createUniqueName(criteria, 'data-criterion');
    // Set the criterion name in the new rubric element.
    $(this.element).attr('data-criterion', name);
    $('.openassessment_criterion_name', this.element).attr('value', name);
  }

  /**
     Hook into the event handler for removal of a criterion.

     */
  removeHandler() {
    const criterionName = $(this.element).data('criterion');
    this.notifier.notificationFired('criterionRemove', { criterionName });
  }

  /**
     Hook into the event handler when a rubric criterion is modified.

     */
  updateHandler() {
    const fields = this.getFieldValues();
    const criterionName = fields.name;
    const criterionLabel = fields.label;
    this.notifier.notificationFired(
      'criterionUpdated',
      { criterionName, criterionLabel },
    );
  }

  /**
     Mark validation errors.

     Returns:
     Boolean indicating whether the criterion is valid.

     * */
  validate() {
    // The criterion prompt is required.
    let isValid = (this.prompt() !== '');

    if (!isValid) {
      this.promptSel.addClass('openassessment_highlighted_field');
      this.promptSel.attr('aria-invalid', true);
    }

    // All options must be valid
    $.each(this.optionContainer.getAllItems(), function () {
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

    // Criterion prompt errors
    if (this.promptSel.hasClass('openassessment_highlighted_field')) {
      errors.push('Criterion prompt is invalid.');
    }

    // Option errors
    $.each(this.optionContainer.getAllItems(), function () {
      errors = errors.concat(this.validationErrors());
    });

    return errors;
  }

  /**
     Clear all validation errors from the UI.
     * */
  clearValidationErrors() {
    // Clear criterion prompt errors
    this.promptSel.removeClass('openassessment_highlighted_field');
    this.promptSel.removeAttr('aria-invalid');

    // Clear option errors
    $.each(this.optionContainer.getAllItems(), function () {
      this.clearValidationErrors();
    });
  }
}

/**
 The TrainingExample class is used to construct and retrieve information from its element within the DOM

 Args:
 element (JQuery Object): the selection which identifies the scope of the training example.

 Returns:
 OpenAssessment.TrainingExample

 * */
export class TrainingExample {
  constructor(element) {
    this.element = element;
    this.criteria = $('.openassessment_training_example_criterion_option', this.element);
    this.answer = $('.openassessment_training_example_essay_part textarea', this.element);
  }

  /**
     Returns the values currently stored in the fields associated with this training example.
     * */
  getFieldValues() {
    // Iterates through all of the options selected by the training example, and adds them
    // to a list.
    const optionsSelected = this.criteria.map(
      function () {
        return {
          criterion: $(this).data('criterion'),
          option: $(this).prop('value'),
        };
      },
    ).get();

    return {
      answer: this.answer.map(function () {
        return $(this).prop('value');
      }).get(),
      options_selected: optionsSelected,
    };
  }

  addHandler() {
    // Goes through and instantiates the option description in the training example for each option.
    $('.openassessment_training_example_criterion_option', this.element).each(function () {
      $('option', this).each(function () {
        ItemUtilities.refreshOptionString($(this));
      });
    });
  }

  addEventListeners() {}

  removeHandler() {}

  updateHandler() {}

  /**
     Mark validation errors.

     Returns:
     Boolean indicating whether the criterion is valid.

     * */
  validate() {
    let isValid = true;

    this.criteria.each(
      function () {
        const isOptionValid = ($(this).prop('value') !== '');
        isValid = isOptionValid && isValid;

        if (!isOptionValid) {
          $(this).addClass('openassessment_highlighted_field');
          $(this).attr('aria-invalid', true);
        }
      },
    );

    return isValid;
  }

  /**
     Return a list of validation errors visible in the UI.
     Mainly useful for testing.

     Returns:
     list of string

     * */
  validationErrors() {
    const errors = [];
    this.criteria.each(
      function () {
        const hasError = $(this).hasClass('openassessment_highlighted_field');
        if (hasError) {
          errors.push('Student training example is invalid.');
        }
      },
    );
    return errors;
  }

  /**
     Retrieve all elements representing items in this container.

     Returns:
     array of container item objects

     * */
  clearValidationErrors() {
    this.criteria.each(
      function () {
        $(this).removeClass('openassessment_highlighted_field');
        $(this).removeAttr('aria-invalid');
      },
    );
  }
}

/**
 Simple helper class, that adds click event listener to some control element, and on
 click removes control itself and ``is--hidden`` class from another element.

 Args:
 controlElement (JQuery Object): control element.
 hiddenElement (JQuery Object): element with ``is--hidden`` class, that will be showed.

 Returns:
 OpenAssessment.ShowControl

 * */
export class ShowControl {
  constructor(controlElement, hiddenElement) {
    this.controlElement = controlElement;
    this.hiddenElement = hiddenElement;
  }

  install() {
    this.controlElement.click((event) => {
      event.preventDefault();
      this.showHiddenElement();
      this.hideSelf();
    });
    return this;
  }

  showHiddenElement() {
    this.hiddenElement.removeClass('is--hidden');
  }

  hideSelf() {
    this.controlElement.addClass('is--hidden');
  }
}
