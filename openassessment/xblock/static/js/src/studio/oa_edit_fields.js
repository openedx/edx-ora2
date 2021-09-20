/* eslint-disable max-classes-per-file */
/**
 Utilities for reading / writing fields.
 * */
export const Fields = {
  // Wrapper for text/textarea select components
  stringField: (sel, value) => {
    if (value !== undefined) { sel.val(value); }
    return sel.val();
  },

  // Wrapper for checkbox select components
  booleanField: (sel, value) => {
    if (value !== undefined) { sel.prop('checked', value); }
    return sel.prop('checked');
  },

  // Wrapper for dropdown select components
  selectField: (sel, value) => {
    if (value !== undefined) { sel.val(value); }
    return sel.val();
  },
};

/**
 Integer input.

 Args:
 inputSel (JQuery selector or DOM element): The input field.

 Keyword args:
 min (int): The minimum value allowed in the input.
 max (int): The maximum value allowed in the input.

 * */

export class IntField {
  constructor(inputSel, restrictions) {
    this.max = restrictions.max;
    this.min = restrictions.min;
    this.input = $(inputSel);
  }

  /**
     Retrieve the integer value from the input.
     Decimal values will be truncated, and non-numeric
     values will become NaN.

     Returns:
     integer or NaN
     * */
  get() {
    return parseInt(this.input.val().trim(), 10);
  }

  /**
     Set the input value.

     Args:
     val (int or string)

     * */
  set(val) {
    this.input.val(val);
  }

  /**
     Mark validation errors if the field does not satisfy the restrictions.
     Fractional values are not considered valid integers.

     This will trim whitespace from the field, so "   34  " would be considered
     a valid input.

     Returns:
     Boolean indicating whether the field's value is valid.

     * */
  validate() {
    const value = this.get();
    let isValid = !Number.isNaN(value) && value >= this.min && value <= this.max;

    // Decimal values not allowed
    if (this.input.val().indexOf('.') !== -1) {
      isValid = false;
    }

    if (!isValid) {
      this.input.addClass('openassessment_highlighted_field');
      this.input.attr('aria-invalid', true);
    }
    return isValid;
  }

  /**
     Clear any validation errors from the UI.
     * */
  clearValidationErrors() {
    this.input.removeClass('openassessment_highlighted_field');
    this.input.removeAttr('aria-invalid');
  }

  /**
     Return a list of validation errors currently displayed
     in the UI.  Mainly useful for testing.

     Returns:
     list of strings

     * */
  validationErrors() {
    const hasError = this.input.hasClass('openassessment_highlighted_field');
    return hasError ? ['Int field is invalid'] : [];
  }
}

/**
 Show and hide elements based on a checkbox.

 Args:
 checkboxSel (JQuery selector): The checkbox used to toggle whether sections
 are shown or hidden.
 shownSel (list of JQuery selectors): Sections to show when the checkbox is checked.
 hiddenSel (list of JQuery selectors): Sections to show when the checkbox is unchecked.
 notifier (OpenAssessment.Notifier): Receives notifications when the checkbox state changes.

 Sends the following notifications:
 * toggleOn
 * toggleOff
 * */
export class ToggleControl {
  constructor(checkboxSel, shownSel, hiddenSel, notifier) {
    this.checkbox = checkboxSel;
    this.shownSections = shownSel;
    this.hiddenSections = hiddenSel;
    this.notifier = notifier;
  }

  /**
     Install the event handler for the checkbox,
     passing in the toggle control object as the event data.

     Args:
     checkboxSelector (string): The CSS selector string for the checkbox.

     Returns:
     OpenAssessment.ToggleControl
     * */
  install() {
    this.checkbox.change(
      this, function (event) {
        const control = event.data;
        if (this.checked) {
          control.notifier.notificationFired('toggleOn', {});
          control.show();
        } else {
          control.notifier.notificationFired('toggleOff', {});
          control.hide();
        }
      },
    );
    return this;
  }

  show() {
    $.each(this.hiddenSections, (i, section) => {
      section.addClass('is--hidden');
    });
    $.each(this.shownSections, (i, section) => {
      section.removeClass('is--hidden');
    });
  }

  hide() {
    $.each(this.shownSections, (i, section) => {
      section.addClass('is--hidden');
    });
    $.each(this.hiddenSections, (i, section) => {
      section.removeClass('is--hidden');
    });
  }
}

/**
 Date and time input fields.

 Args:
 element (DOM element): The parent element of the control inputs.
 datePicker (string): The CSS selector for the date input field.
 timePicker (string): The CSS selector for the time input field.

 * */
export class DatetimeControl {
  constructor(element, datePicker, timePicker) {
    this.element = element;
    this.datePicker = datePicker;
    this.timePicker = timePicker;
  }

  /**
     Configure the date and time picker inputs.

     Returns:
     OpenAssessment.DatetimeControl

     * */
  install() {
    const dateString = $(this.datePicker, this.element).val();
    $(this.datePicker, this.element).datepicker({ showButtonPanel: true })
      .datepicker('option', 'dateFormat', 'yy-mm-dd')
      .datepicker('setDate', dateString);
    $(this.timePicker, this.element).timepicker({
      timeFormat: 'H:i',
      step: 60,
    });
    return this;
  }

  /**
     Get or set the date and time.

     Args:
     dateString (string, optional): If provided, set the date (YYYY-MM-DD).
     timeString (string, optional): If provided, set the time (HH:MM, 24-hour clock).

     Returns:
     ISO-formatted datetime string.

     * */
  datetime(dateString, timeString) {
    const datePickerSel = $(this.datePicker, this.element);
    const timePickerSel = $(this.timePicker, this.element);
    if (typeof (dateString) !== 'undefined') { datePickerSel.val(dateString); }
    if (typeof (timeString) !== 'undefined') { timePickerSel.val(timeString); }
    return `${datePickerSel.val()}T${timePickerSel.val()}`;
  }

  /**
     Mark validation errors.

     Returns:
     Boolean indicating whether the fields are valid.

     * */
  validate() {
    const dateString = $(this.datePicker, this.element).val();
    const timeString = $(this.timePicker, this.element).val();

    // date validation
    let isDateValid = false;

    try {
      const parsedDate = $.datepicker.parseDate($.datepicker.ISO_8601, dateString);
      isDateValid = parsedDate instanceof Date;
    } catch (err) {
      // parseDate function throws error if date is not in expected format.
      // isDateValid flag would remain false.
    }
    if (!isDateValid) {
      $(this.datePicker, this.element).addClass('openassessment_highlighted_field');
      $(this.datePicker, this.element).attr('aria-invalid', true);
    }

    // time validation
    const matches = timeString.match(/^\d{2}:\d{2}$/g);
    const isTimeValid = (matches !== null);
    if (!isTimeValid) {
      $(this.timePicker, this.element).addClass('openassessment_highlighted_field');
      $(this.timePicker, this.element).attr('aria-invalid', true);
    }

    return (isDateValid && isTimeValid);
  }

  /**
     Clear all validation errors from the UI.
     * */
  clearValidationErrors() {
    $(this.datePicker, this.element).removeClass('openassessment_highlighted_field');
    $(this.timePicker, this.element).removeClass('openassessment_highlighted_field');
    $(this.datePicker, this.element).removeAttr('aria-invalid');
    $(this.timePicker, this.element).removeAttr('aria-invalid');
  }

  /**
     Return a list of validation errors visible in the UI.
     Mainly useful for testing.

     Returns:
     list of string

     * */
  validationErrors() {
    const errors = [];
    const dateHasError = $(this.datePicker, this.element).hasClass('openassessment_highlighted_field');
    const timeHasError = $(this.timePicker, this.element).hasClass('openassessment_highlighted_field');

    if (dateHasError) { errors.push('Date is invalid'); }
    if (timeHasError) { errors.push('Time is invalid'); }

    return errors;
  }
}

/**
 Show and hide elements based on select options.

 Args:
 selectSel (JQuery selector): The select used to toggle whether sections
 are shown or hidden.
 mapping (Object): A mapping object that is used to specify the relationship
 between option and section.  e.g.
 {
     option1: selector1,
     option2: selector2,
 }
 When an option is selected, the section is shown and all other sections will be hidden.
 notifier (OpenAssessment.Notifier): Receives notifications when the select state changes.

 Sends the following notifications:
 * selectionChanged
 * */
export class SelectControl {
  constructor(selectSel, mapping, notifier) {
    this.select = selectSel;
    this.mapping = mapping;
    this.notifier = notifier;
  }

  /**
     Install the event handler for the select,
     passing in the toggle control object as the event data.

     Returns:
     OpenAssessment.ToggleControl
     * */
  install() {
    this.select.change(
      this, function (event) {
        const control = event.data;
        control.notifier.notificationFired('selectionChanged', { selected: this.value });
        control.change(this.value);
      },
    );
    return this;
  }

  change(selected) {
    if ($.isFunction(this.mapping)) {
      this.mapping(selected);
    } else {
      $.each(this.mapping, (option, sel) => {
        if (option === selected) {
          sel.removeClass('is--hidden');
        } else {
          sel.addClass('is--hidden');
        }
      });
    }
  }
}

/**
 Input field that support custom validation.

 This is similar to string field but allow you to pass in a custom validation function to validate the input field.

 Args:
 inputSel (JQuery selector or DOM element): The input field.
 validator (callable): The callback for custom validation function. The function should accept
 one parameter for the value of the input and returns an array of errors strings. If not error, return [].
 */
export class InputControl {
  constructor(inputSel, validator) {
    this.input = $(inputSel);
    this.validator = validator;
    this.errors = [];
  }

  /**
     Retrieve the string value from the input.

     Returns:
     string
     * */
  get() {
    return this.input.val();
  }

  /**
     Set the input value.

     Args:
     val (string)

     * */
  set(val) {
    this.input.val(val);
  }

  /**
     Mark validation errors if the field does not pass the validation callback function.

     Returns:
     Boolean indicating whether the field's value is valid.

     * */
  validate() {
    this.errors = this.validator(this.get());

    if (this.errors.length) {
      this.input.addClass('openassessment_highlighted_field');
      this.input.attr('aria-invalid', true);
      this.input.parent().nextAll('.message-status').text(this.errors.join(';'));
      this.input.parent().nextAll('.message-status').removeClass('is--hidden');
    }
    return this.errors.length === 0;
  }

  /**
     Clear any validation errors from the UI.
     * */
  clearValidationErrors() {
    this.input.removeClass('openassessment_highlighted_field');
    this.input.removeAttr('aria-invalid');
    this.input.parent().nextAll('.message-status').addClass('is--hidden');
  }

  /**
     Return a list of validation errors currently displayed
     in the UI.

     Returns:
     list of strings that contain error messages

     * */
  validationErrors() {
    return this.errors;
  }
}
