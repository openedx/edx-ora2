describe("OpenAssessment.ValidationAlert", function() {

    var alert = null;

    beforeEach(function() {
        loadFixtures('oa_edit.html');
        alert = new OpenAssessment.ValidationAlert(
            $("#openassessment_rubric_validation_alert")
        );
    });

    it("shows and hides an alert", function() {
        // Initially, the alert should be hidden
        expect(alert.isVisible()).toBe(false);

        // Show the alert
        alert.show();
        expect(alert.isVisible()).toBe(true);

        // Hide the alert
        alert.hide();
        expect(alert.isVisible()).toBe(false);
    });

    it("sets the alert title and message", function() {
        // Set the title and message
        alert.setMessage("new title", "new message");
        expect(alert.getTitle()).toEqual("new title");
        expect(alert.getMessage()).toEqual("new message");
    });

});