describe("OpenAssessment.Notifier", function() {

    var notifier = null;
    var listeners = [];

    var StubListener = function() {
        this.receivedData = null;
        this.testNotification = function(data) {
            this.receivedData = data;
        };
    };

    beforeEach(function() {
        listeners = [ new StubListener(), new StubListener() ];
        notifier = new OpenAssessment.Notifier(listeners);
    });

    it("notifies listeners when a notification fires", function() {
        // Fire a notification that the listeners don't respond to
        notifier.notificationFired("ignore this!", {});
        expect(listeners[0].receivedData).toBe(null);
        expect(listeners[1].receivedData).toBe(null);

        // Fire a notification that the listeners care about
        var testData = { foo: "bar" };
        notifier.notificationFired("testNotification", testData);

        // Check that the listeners were notified
        expect(listeners[0].receivedData).toBe(testData);
        expect(listeners[1].receivedData).toBe(testData);
    });
});
