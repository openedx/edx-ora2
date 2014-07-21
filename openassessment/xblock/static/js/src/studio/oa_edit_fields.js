/**
Utilities for reading / writing fields.
**/
OpenAssessment.Fields = {
    stringField: function(sel, value) {
        if (typeof(value) !== "undefined") { sel.val(value); }
        return sel.val();
    },

    intField: function(sel, value) {
        if (typeof(value) !== "undefined") { sel.val(value); }
        return parseInt(sel.val(), 10);
    },

    booleanField: function(sel, value) {
        if (typeof(value) !== "undefined") { sel.prop("checked", value); }
        return sel.prop("checked");
    },
};


/**
Show and hide elements based on a checkbox.

Args:
    element (DOM element): The parent element, used to scope the selectors.
    hiddenSelector (string): The CSS selector string for elements
        to show when the checkbox is in the "off" state.
    shownSelector (string): The CSS selector string for elements
        to show when the checkbox is in the "on" state.
**/
OpenAssessment.ToggleControl = function(element, hiddenSelector, shownSelector) {
    this.element = element;
    this.hiddenSelector = hiddenSelector;
    this.shownSelector = shownSelector;
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
    install: function(checkboxSelector) {
        $(checkboxSelector, this.element).change(
            this, function(event) {
                var control = event.data;
                if (this.checked) { control.show(); }
                else { control.hide(); }
            }
        );
        return this;
    },

    show: function() {
        $(this.hiddenSelector, this.element).addClass('is--hidden');
        $(this.shownSelector, this.element).removeClass('is--hidden');
    },

    hide: function() {
        $(this.hiddenSelector, this.element).removeClass('is--hidden');
        $(this.shownSelector, this.element).addClass('is--hidden');
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
        $(this.datePicker, this.element).datepicker({ showButtonPanel: true })
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
        dateString (string, optional): If provided, set the date (YY-MM-DD).
        timeString (string, optional): If provided, set the time (HH:MM, 24-hour clock).

    Returns:
        ISO-formatted datetime string.

    **/
    datetime: function(dateString, timeString) {
        var datePickerSel = $(this.datePicker, this.element);
        var timePickerSel = $(this.timePicker, this.element);
        if (typeof(dateString) !== "undefined") { datePickerSel.datepicker("setDate", dateString); }
        if (typeof(timeString) !== "undefined") { timePickerSel.val(timeString); }

        if (datePickerSel.val() === "" && timePickerSel.val() === "") {
            return null;
        }
        return datePickerSel.val() + "T" + timePickerSel.val();
    }
};