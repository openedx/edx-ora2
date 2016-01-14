/**
 Utilities for reading / writing fields.
 **/
OpenAssessment.Fields = {
    stringField: function(sel, value) {
        if (value !== undefined) { sel.val(value); }
        return sel.val();
    },

    booleanField: function(sel, value) {
        if (value !== undefined) { sel.prop("checked", value); }
        return sel.prop("checked");
    }
};

/**
 Integer input.

 Args:
 inputSel (JQuery selector or DOM element): The input field.

 Keyword args:
 min (int): The minimum value allowed in the input.
 max (int): The maximum value allowed in the input.

 **/
OpenAssessment.IntField = function(inputSel, restrictions) {
    this.max = restrictions.max;
    this.min = restrictions.min;
    this.input = $(inputSel);
};

OpenAssessment.IntField.prototype = {

    /**
     Retrieve the integer value from the input.
     Decimal values will be truncated, and non-numeric
     values will become NaN.

     Returns:
     integer or NaN
     **/
    get: function() {
        return parseInt(this.input.val().trim(), 10);
    },

    /**
     Set the input value.

     Args:
     val (int or string)

     **/
    set: function(val) {
        this.input.val(val);
    },

    /**
     Mark validation errors if the field does not satisfy the restrictions.
     Fractional values are not considered valid integers.

     This will trim whitespace from the field, so "   34  " would be considered
     a valid input.

     Returns:
     Boolean indicating whether the field's value is valid.

     **/
    validate: function() {
        var value = this.get();
        var isValid = !isNaN(value) && value >= this.min && value <= this.max;

        // Decimal values not allowed
        if (this.input.val().indexOf(".") !== -1) {
            isValid = false;
        }

        if (!isValid) {
            this.input.addClass("openassessment_highlighted_field");
        }
        return isValid;
    },

    /**
     Clear any validation errors from the UI.
     **/
    clearValidationErrors: function() {
        this.input.removeClass("openassessment_highlighted_field");
    },

    /**
     Return a list of validation errors currently displayed
     in the UI.  Mainly useful for testing.

     Returns:
     list of strings

     **/
    validationErrors: function() {
        var hasError = this.input.hasClass("openassessment_highlighted_field");
        return hasError ? ["Int field is invalid"] : [];
    }
};

/**
 Show and hide elements based on a checkbox.

 Args:
 checkboxSel (JQuery selector): The checkbox used to toggle whether sections
 are shown or hidden.
 shownSel (JQuery selector): The section to show when the checkbox is checked.
 hiddenSel (JQuery selector): The section to show when the checkbox is unchecked.
 notifier (OpenAssessment.Notifier): Receives notifications when the checkbox state changes.

 Sends the following notifications:
 * toggleOn
 * toggleOff
 **/
OpenAssessment.ToggleControl = function(checkboxSel, shownSel, hiddenSel, notifier) {
    this.checkbox = checkboxSel;
    this.shownSection = shownSel;
    this.hiddenSection = hiddenSel;
    this.notifier = notifier;
};

OpenAssessment.ToggleControl.prototype = {
    /**
     Install the event handler for the checkbox,
     passing in the toggle control object as the event data.

     Args:
     checkboxSelector (string): The CSS selector string for the checkbox.

     Returns:
     OpenAssessment.ToggleControl
     **/
    install: function() {
        this.checkbox.change(
            this, function(event) {
                var control = event.data;
                if (this.checked) {
                    control.notifier.notificationFired('toggleOn', {});
                    control.show();
                }
                else {
                    control.notifier.notificationFired('toggleOff', {});
                    control.hide();
                }
            }
        );
        return this;
    },

    show: function() {
        this.hiddenSection.addClass('is--hidden');
        this.shownSection.removeClass('is--hidden');
    },

    hide: function() {
        this.shownSection.addClass('is--hidden');
        this.hiddenSection.removeClass('is--hidden');
    }
};

/**
 Date and time input fields.

 Args:
 element (DOM element): The parent element of the control inputs.
 datePicker (string): The CSS selector for the date input field.
 timePicker (string): The CSS selector for the time input field.

 **/
OpenAssessment.DatetimeControl = function(element, datePicker, timePicker) {
    this.element = element;
    this.datePicker = datePicker;
    this.timePicker = timePicker;
};

OpenAssessment.DatetimeControl.prototype = {
    /**
     Configure the date and time picker inputs.

     Returns:
     OpenAssessment.DatetimeControl

     **/
    install: function() {
        var dateString = $(this.datePicker, this.element).val();
        $(this.datePicker, this.element).datepicker({showButtonPanel: true})
            .datepicker("option", "dateFormat", "yy-mm-dd")
            .datepicker("setDate", dateString);
        $(this.timePicker, this.element).timepicker({
            timeFormat: 'H:i',
            step: 60
        });
        return this;
    },

    /**
     Get or set the date and time.

     Args:
     dateString (string, optional): If provided, set the date (YYYY-MM-DD).
     timeString (string, optional): If provided, set the time (HH:MM, 24-hour clock).

     Returns:
     ISO-formatted datetime string.

     **/
    datetime: function(dateString, timeString) {
        var datePickerSel = $(this.datePicker, this.element);
        var timePickerSel = $(this.timePicker, this.element);
        if (typeof(dateString) !== "undefined") { datePickerSel.val(dateString); }
        if (typeof(timeString) !== "undefined") { timePickerSel.val(timeString); }
        return datePickerSel.val() + "T" + timePickerSel.val();
    },

    /**
     Mark validation errors.

     Returns:
     Boolean indicating whether the fields are valid.

     **/
    validate: function() {
        var dateString = $(this.datePicker, this.element).val();
        var timeString = $(this.timePicker, this.element).val();

        //date validation
        var isDateValid = false;

        try {
            var parsedDate = $.datepicker.parseDate($.datepicker.ISO_8601, dateString);
            isDateValid = parsedDate instanceof Date;
        } catch (err) {
            // parseDate function throws error if date is not in expected format.
            // isDateValid flag would remain false.
        }
        if (!isDateValid) {
            $(this.datePicker, this.element).addClass("openassessment_highlighted_field");
        }

        //time validation
        var matches = timeString.match(/^\d{2}:\d{2}$/g);
        var isTimeValid = (matches !== null);
        if (!isTimeValid) {
            $(this.timePicker, this.element).addClass("openassessment_highlighted_field");
        }

        return (isDateValid && isTimeValid);
    },

    /**
     Clear all validation errors from the UI.
     **/
    clearValidationErrors: function() {
        $(this.datePicker, this.element).removeClass("openassessment_highlighted_field");
        $(this.timePicker, this.element).removeClass("openassessment_highlighted_field");
    },

    /**
     Return a list of validation errors visible in the UI.
     Mainly useful for testing.

     Returns:
     list of string

     **/
    validationErrors: function() {
        var errors = [];
        var dateHasError = $(this.datePicker, this.element).hasClass("openassessment_highlighted_field");
        var timeHasError = $(this.timePicker, this.element).hasClass("openassessment_highlighted_field");

        if (dateHasError) { errors.push("Date is invalid"); }
        if (timeHasError) { errors.push("Time is invalid"); }

        return errors;
    }
};

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
 **/
OpenAssessment.SelectControl = function(selectSel, mapping, notifier) {
    this.select = selectSel;
    this.mapping = mapping;
    this.notifier = notifier;
};

OpenAssessment.SelectControl.prototype = {
    /**
     Install the event handler for the select,
     passing in the toggle control object as the event data.

     Returns:
     OpenAssessment.ToggleControl
     **/
    install: function() {
        this.select.change(
            this, function(event) {
                var control = event.data;
                control.notifier.notificationFired('selectionChanged', {selected: this.value});
                control.change(this.value);
            }
        );
        return this;
    },

    change: function(selected) {
        $.each(this.mapping, function(option, sel) {
            if (option === selected) {
                sel.removeClass('is--hidden');
            } else {
                sel.addClass('is--hidden');
            }
        });
    }
};

/**
 Input field that support custom validation.

 This is similar to string field but allow you to pass in a custom validation function to validate the input field.

 Args:
 inputSel (JQuery selector or DOM element): The input field.
 validator (callable): The callback for custom validation function. The function should accept
 one parameter for the value of the input and returns an array of errors strings. If not error, return [].
 */
OpenAssessment.InputControl = function(inputSel, validator) {
    this.input = $(inputSel);
    this.validator = validator;
    this.errors = [];
};

OpenAssessment.InputControl.prototype = {

    /**
     Retrieve the string value from the input.

     Returns:
     string
     **/
    get: function() {
        return this.input.val();
    },

    /**
     Set the input value.

     Args:
     val (string)

     **/
    set: function(val) {
        this.input.val(val);
    },

    /**
     Mark validation errors if the field does not pass the validation callback function.

     Returns:
     Boolean indicating whether the field's value is valid.

     **/
    validate: function() {
        this.errors = this.validator(this.get());

        if (this.errors.length) {
            this.input.addClass("openassessment_highlighted_field");
            this.input.parent().nextAll('.message-status').text(this.errors.join(";"));
            this.input.parent().nextAll('.message-status').addClass("is-shown");
        }
        return this.errors.length === 0;
    },

    /**
     Clear any validation errors from the UI.
     **/
    clearValidationErrors: function() {
        this.input.removeClass("openassessment_highlighted_field");
        this.input.parent().nextAll('.message-status').removeClass("is-shown");
    },

    /**
     Return a list of validation errors currently displayed
     in the UI.

     Returns:
     list of strings that contain error messages

     **/
    validationErrors: function() {
        return this.errors;
    }
};
