/*
Tests for OA XBlock editing.
*/

describe("OpenAssessment.StudioUI", function() {

    var runtime = {
        notify: function(type, data) {}
    };

    // Stub server that returns dummy data or reports errors.
    var StubServer = function() {
        this.loadError = false;
        this.updateError = false;
        this.xml = '<openassessment></openassessment>';

        this.errorPromise = $.Deferred(function(defer) {
            defer.rejectWith(this, ['Test error']);
        }).promise();

        this.loadXml = function() {
            var xml = this.xml;
            if (!this.loadError) {
                return $.Deferred(function(defer) {
                    defer.resolveWith(this, [xml]);
                }).promise();
            }
            else {
                return this.errorPromise;
            }
        }

        this.updateXml = function(xml) {
            if (!this.updateError) {
                this.xml = xml;
                return $.Deferred(function(defer) {
                    defer.resolve();
                }).promise();
            }
            else {
                return this.errorPromise;
            }
        }
    };

    var server = null;
    var ui = null;

    beforeEach(function() {

        // Load the DOM fixture
        jasmine.getFixtures().fixturesPath = 'base/fixtures'
        loadFixtures('oa_edit.html');

        // Create the stub server
        server = new StubServer();

        // Mock the runtime
        spyOn(runtime, 'notify');

        // Create the object under test
        var el = $('#openassessment-edit').get(0);
        ui = new OpenAssessment.StudioUI(runtime, el, server);
    });

    it("loads the XML definition", function() {
        // Initialize the UI
        ui.load()

        // Expect that the XML definition was loaded
        var contents = ui.codeBox.getValue();
        expect(contents).toEqual('<openassessment></openassessment>');
    });

    it("saves the XML definition", function() {
        // Update the XML
        ui.codeBox.setValue('<openassessment>test!</openassessment>');

        // Save the updated XML
        ui.save();

        // Expect the saving notification to start/end
        expect(runtime.notify).toHaveBeenCalledWith('save', {state: 'start'});
        expect(runtime.notify).toHaveBeenCalledWith('save', {state: 'end'});

        // Expect the server's XML to have been updated
        expect(server.xml).toEqual('<openassessment>test!</openassessment>');
    });

    it("cancels editing", function() {
        ui.cancel();
        expect(runtime.notify).toHaveBeenCalledWith('cancel', {});
    });

    it("displays an error when server reports a load XML error", function() {
        server.loadError = true;
        ui.load();
        expect(runtime.notify).toHaveBeenCalledWith('error', {msg: 'Test error'});
    });

    it("displays an error when server reports an update XML error", function() {
        server.updateError = true;
        ui.save('<openassessment>test!</openassessment>');
        expect(runtime.notify).toHaveBeenCalledWith('error', {msg: 'Test error'});
    });

});
