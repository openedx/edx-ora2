describe("OpenAssessment.ValidationAlert", function() {

    var alert = null;

    beforeEach(function() {
        loadFixtures('oa_edit.html');
        alert = new OpenAssessment.ValidationAlert().install();
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
        alert.setMessage("new title", "new message");
        expect(alert.getTitle()).toEqual("new title");
        expect(alert.getMessage()).toEqual("new message");
    });

    it("hides when the user dismisses the alert", function() {
        // Show the alert
        alert.show();
        expect(alert.isVisible()).toBe(true);

        // Simulate a user click on the close button
        alert.closeButton.click();

        // The alert should be hidden
        expect(alert.isVisible()).toBe(false);
    });
});