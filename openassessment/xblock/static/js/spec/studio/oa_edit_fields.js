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
    });

    // Set the date and time values, then check whether
    // the datetime control has the expected validation status
    var testValidateDate = function(control, dateValue, timeValue, isValid, expectedError) {
        control.datetime(dateValue, timeValue);
        expect(control.validate()).toBe(isValid);

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
        testValidateDate(datetimeControl, "2014-99-01", "00:00", false, expectedError);
        testValidateDate(datetimeControl, "2014-01-99", "00:00", false, expectedError);
        testValidateDate(datetimeControl, "2014-99999-01", "00:00", false, expectedError);
        testValidateDate(datetimeControl, "2014-01-99999", "00:00", false, expectedError);
    });

    it("validates invalid times", function() {
        var expectedError = "Time is invalid";

        testValidateDate(datetimeControl, "2014-04-01", "", false, expectedError);
        testValidateDate(datetimeControl, "2014-04-01", "00:00abcd", false, expectedError);
        testValidateDate(datetimeControl, "2014-04-01", "24:00", false, expectedError);
        testValidateDate(datetimeControl, "2014-04-01", "00:60", false, expectedError);
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