/**
Tests for OA XBlock editing.
**/

describe("OpenAssessment.StudioView", function() {

    var runtime = {
        notify: function(type, data) {}
    };

    // Stub server that returns dummy data or reports errors.
    var StubServer = function() {
        this.updateError = false;
        this.isReleased = false;
        this.receivedData = null;
        this.successPromise = $.Deferred(function(defer) {
            defer.resolve();
        });
        this.errorPromise = $.Deferred(function(defer) {
            defer.rejectWith(this, ['Test error']);
        }).promise();

        this.updateEditorContext = function(kwargs) {
            if (this.updateError) {
                return this.errorPromise;
            }
            else {
                this.receivedData = kwargs;
                return this.successPromise;
            }
        };

        this.checkReleased = function() {
            var server = this;
            return $.Deferred(function(defer) {
                defer.resolveWith(this, [server.isReleased]);
            }).promise();
        };
    };

    var server = null;
    var view = null;

    beforeEach(function() {
        // Load the DOM fixture
        jasmine.getFixtures().fixturesPath = 'base/fixtures';
        loadFixtures('oa_edit.html');

        // Create the stub server
        server = new StubServer();

        // Mock the runtime
        spyOn(runtime, 'notify');

        // Create the object under test
        var el = $('#openassessment-editor').get(0);
        view = new OpenAssessment.StudioView(runtime, el, server);
    });

    it("saves the editor context definition", function() {
        // Update the context
        view.settingsFieldSelectors.titleField.val('THIS IS THE NEW TITLE');
        view.settingsFieldSelectors.submissionStartField.val('2014-01-01');

        // Save the updated editor definition
        view.save();

        // Expect the saving notification to start/end
        expect(runtime.notify).toHaveBeenCalledWith('save', {state: 'start'});
        expect(runtime.notify).toHaveBeenCalledWith('save', {state: 'end'});

        // Expect the server's context to have been updated
        expect(server.receivedData.title).toEqual('THIS IS THE NEW TITLE');
        expect(server.receivedData.submissionStart).toEqual('2014-01-01T00:00:00.000Z');
    });

    it("confirms changes for a released problem", function() {
        // Simulate an XBlock that has been released
        server.isReleased = true;

        // Stub the confirmation step (avoid showing the dialog)
        spyOn(view, 'confirmPostReleaseUpdate').andCallFake(
            function(onConfirm) { onConfirm(); }
        );

        // Save the updated context
        view.save();

        // Verify that the user was asked to confirm the changes
        expect(view.confirmPostReleaseUpdate).toHaveBeenCalled();
    });

    it("cancels editing", function() {
        view.cancel();
        expect(runtime.notify).toHaveBeenCalledWith('cancel', {});
    });

    it("displays an error when server reports an update XML error", function() {
        server.updateError = true;
        view.save();
        expect(runtime.notify).toHaveBeenCalledWith('error', {msg: 'Test error'});
    });
});
