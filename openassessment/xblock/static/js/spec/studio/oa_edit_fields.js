var StubNotifier = function() {
    this.receivedNotifications = [];
    this.notificationFired = function(name, data) {
        this.receivedNotifications.push({
            name: name,
            data: data
        });
    };
};

describe("OpenAssessment.DatetimeControl", function() {

    var datetimeControl = null;

    beforeEach(function() {
        // Install a minimal HTML fixture
        // containing text fields for the date and time
        setFixtures(
            '<div id="datetime_parent">' +
                '<input type="text" class="date_field" />' +
                '<input type="text" class="time_field" />' +
            '</div>'
        );

        // Create the datetime control, which uses elements
        // available in the fixture.
        datetimeControl = new OpenAssessment.DatetimeControl(
            $("#datetime_parent").get(0),
            ".date_field",
            ".time_field"
        );
        datetimeControl.install();
    });

    // Set the date and time values, then check whether
    // the datetime control has the expected validation status
    var testValidateDate = function(control, dateValue, timeValue, isValid, expectedError) {
        control.datetime(dateValue, timeValue);

        var actualIsValid = control.validate();
        expect(actualIsValid).toBe(isValid);

        if (isValid) { expect(control.validationErrors()).toEqual([]); }
        else { expect(control.validationErrors()).toContain(expectedError); }
    };

    it("validates invalid dates", function() {
        var expectedError = "Date is invalid";

        testValidateDate(datetimeControl, "", "00:00", false, expectedError);
        testValidateDate(datetimeControl, "1", "00:00", false, expectedError);
        testValidateDate(datetimeControl, "123abcd", "00:00", false, expectedError);
        testValidateDate(datetimeControl, "2014-", "00:00", false, expectedError);
        testValidateDate(datetimeControl, "99999999-01-01", "00:00", false, expectedError);
        testValidateDate(datetimeControl, "2014-99999-01", "00:00", false, expectedError);
        testValidateDate(datetimeControl, "2014-01-99999", "00:00", false, expectedError);
        //invalid month
        testValidateDate(datetimeControl, "2014-13-01", "00:00", false, expectedError);
        //invalid day
        testValidateDate(datetimeControl, "2014-02-30", "00:00", false, expectedError);
    });

    it("validates invalid times", function() {
        var expectedError = "Time is invalid";

        testValidateDate(datetimeControl, "2014-04-01", "", false, expectedError);
        testValidateDate(datetimeControl, "2014-04-01", "00:00abcd", false, expectedError);
        testValidateDate(datetimeControl, "2014-04-01", "1", false, expectedError);
        testValidateDate(datetimeControl, "2014-04-01", "1.23", false, expectedError);
        testValidateDate(datetimeControl, "2014-04-01", "1:1", false, expectedError);
        testValidateDate(datetimeControl, "2014-04-01", "000:00", false, expectedError);
        testValidateDate(datetimeControl, "2014-04-01", "00:000", false, expectedError);
    });

    it("validates valid dates and times", function() {
        testValidateDate(datetimeControl, "2014-04-01", "00:00", true);
        testValidateDate(datetimeControl, "9999-01-01", "00:00", true);
        testValidateDate(datetimeControl, "2001-12-31", "00:00", true);
        testValidateDate(datetimeControl, "2014-04-01", "12:34", true);
        testValidateDate(datetimeControl, "2014-04-01", "23:59", true);
        // single character for month and date.
        testValidateDate(datetimeControl, "2014-4-1", "23:59", true);
    });

    it("clears validation errors", function() {
        // Set an invalid state
        datetimeControl.datetime("invalid", "invalid");
        datetimeControl.validate();
        expect(datetimeControl.validationErrors().length).toEqual(2);

        // Clear validation errors
        datetimeControl.clearValidationErrors();
        expect(datetimeControl.validationErrors()).toEqual([]);
    });
});

describe("OpenAssessment.ToggleControl", function() {

    var notifier = null;
    var toggleControl = null;

    beforeEach(function() {
        setFixtures(
            '<div id="toggle_test">' +
                '<div id="shown_section" />' +
                '<div id="hidden_section" class="is--hidden"/>' +
            '</div>' +
            '<input type="checkbox" id="checkbox" checked />'
        );

        notifier = new StubNotifier();
        toggleControl = new OpenAssessment.ToggleControl(
            $("#checkbox"),
            $("#shown_section"),
            $("#hidden_section"),
            notifier
        ).install();
    });

    it("shows and hides elements", function() {
        var assertIsVisible = function(isVisible) {
            expect(toggleControl.hiddenSection.hasClass('is--hidden')).toBe(isVisible);
            expect(toggleControl.shownSection.hasClass('is--hidden')).toBe(!isVisible);
        };

        // Initially, the section is visible (default from the fixture)
        assertIsVisible(true);

        // Simulate clicking the checkbox, hiding the section
        toggleControl.checkbox.click();
        assertIsVisible(false);

        // Click it again to show it
        toggleControl.checkbox.click();
        assertIsVisible(true);
    });

    it("fires notifications", function() {
        // Toggle off notification
        toggleControl.checkbox.click();
        expect(notifier.receivedNotifications).toContain({
            name: "toggleOff",
            data: {}
        });

        // Toggle back on
        toggleControl.checkbox.click();
        expect(notifier.receivedNotifications).toContain({
            name: "toggleOn",
            data: {}
        });

        // ... and toggle off
        toggleControl.checkbox.click();
        expect(notifier.receivedNotifications).toContain({
            name: "toggleOff",
            data: {}
        });
    });

});


describe("OpenAssessment.SelectControl", function() {

    var notifier = null;
    var selectControl = null;

    beforeEach(function() {
        setFixtures(
            '<div id="toggle_test"> \
                <div id="shown_for_option1" /> \
                <div id="shown_for_option2" class="is--hidden"/> \
            </div> \
            <select id="select"> \
                <option value="1">1</option> \
                <option value="2">2</option> \
            </select>'
        );

        notifier = new StubNotifier();
        selectControl = new OpenAssessment.SelectControl(
            $("#select"),
            {'1': $("#shown_for_option1"), '2': $("#shown_for_option2")},
            notifier
        ).install();
    });

    it("shows and hides elements", function() {
        var assertIsVisible = function(selected) {
            $.each(selectControl.mapping, function(option, sel) {
                expect(sel.hasClass('is--hidden')).toBe(option != selected);
            });
        };

        // Initially, the section is visible (default from the fixture)
        assertIsVisible(1);

        // Simulate select the option, hiding the section 2
        selectControl.select.val(2).change();
        assertIsVisible(2);

        // Click it again, hiding section 1
        selectControl.select.val(1).change();
        assertIsVisible(1);
    });

    it("fires notifications", function() {
        selectControl.select.val(1).change();
        expect(notifier.receivedNotifications).toContain({
            name: "selectionChanged",
            data: {selected: "1"}
        });

        selectControl.select.val(2).change();
        expect(notifier.receivedNotifications).toContain({
            name: "selectionChanged",
            data: {selected: "2"}
        });

        selectControl.select.val(1).change();
        expect(notifier.receivedNotifications).toContain({
            name: "selectionChanged",
            data: {selected: "1"}
        });
    });

});


describe("OpenAssessment.InputControl", function() {

    var inputControl = null;
    var validator = jasmine.createSpy('validator');

    beforeEach(function() {
        setFixtures(
            '<div><input type="text" id="input"></div><p class="message-status error" id="error"></p>'
        );

        inputControl = new OpenAssessment.InputControl($("#input"), validator);
    });

    it("should call validator function when validate is called", function() {
        validator.and.returnValue([]);
        inputControl.set('test');
        inputControl.validate();

        expect(validator).toHaveBeenCalledWith('test');
    });

    it("should return true when validate is called and there is no error", function() {
        validator.and.returnValue([]);
        inputControl.set('test');
        var isValid = inputControl.validate();

        expect(isValid).toBe(true);
    });

    it("should return false when validate is called and there is an error", function() {
        validator.and.returnValue(['error']);
        inputControl.set('error input');
        var isValid = inputControl.validate();

        expect(isValid).toBe(false);
    });

    it("should show the error message when validate is called and there is an error", function() {
        validator.and.returnValue(['error']);
        inputControl.set('error input');
        inputControl.validate();

        expect(inputControl.input.hasClass("openassessment_highlighted_field")).toBe(true);
        expect(inputControl.input.parent().nextAll('.message-status').hasClass("is-shown")).toBe(true);
    });

    it("should clear the errors when clearValidationErrors is called", function() {
        validator.and.returnValue(['error']);
        inputControl.set('error input');
        inputControl.validate();
        inputControl.clearValidationErrors();

        expect(inputControl.input.hasClass("openassessment_highlighted_field")).toBe(false);
        expect(inputControl.input.parent().nextAll('.message-status').hasClass("is-shown")).toBe(false);
    });

    it("should return errors generated by validator when validationErrors is called", function() {
        var errors = ['error1', 'error2'];
        validator.and.returnValue(errors);
        inputControl.set('error input');
        inputControl.validate();

        expect(inputControl.validationErrors()).toEqual(errors);
    })
});
