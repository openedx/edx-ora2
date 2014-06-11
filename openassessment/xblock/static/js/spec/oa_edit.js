/**
Tests for OA XBlock editing.
**/

describe("OpenAssessment.StudioView", function() {

    var runtime = {
        notify: function(type, data) {}
    };

    // Stub server that returns dummy data or reports errors.
    var StubServer = function() {
        this.loadError = false;
        this.updateError = false;
        this.xml = '<openassessment></openassessment>';
        this.isReleased = false;

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
        };

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
/*
    it("loads the XML definition", function() {
        // Initialize the view
        view.load();

        // Expect that the XML definition(s) were loaded
        var rubric = view.rubricXmlBox.getValue();
        var prompt = view.promptBox.value;
        var assessments = view.assessmentsXmlBox.getValue()

        expect(prompt).toEqual('');
        expect(rubric).toEqual('<rubric></rubric>');
        expect(assessments).toEqual('<assessments></assessments>');
    });

    it("saves the XML definition", function() {
        // Update the XML
        view.codeBox.setValue('<openassessment>test!</openassessment>');

        // Save the updated XML
        view.save();

        // Expect the saving notification to start/end
        expect(runtime.notify).toHaveBeenCalledWith('save', {state: 'start'});
        expect(runtime.notify).toHaveBeenCalledWith('save', {state: 'end'});

        // Expect the server's XML to have been updated
        expect(server.xml).toEqual('<openassessment>test!</openassessment>');
    });

    it("confirms changes for a released problem", function() {
        // Simulate an XBlock that has been released
        server.isReleased = true;

        // Stub the confirmation step (avoid showing the dialog)
        spyOn(view, 'confirmPostReleaseUpdate').andCallFake(
            function(onConfirm) { onConfirm(); }
        );

        // Save the updated XML
        view.save();

        // Verify that the user was asked to confirm the changes
        expect(view.confirmPostReleaseUpdate).toHaveBeenCalled();
    });

    it("cancels editing", function() {
        view.cancel();
        expect(runtime.notify).toHaveBeenCalledWith('cancel', {});
    });

    it("displays an error when server reports a load XML error", function() {
        server.loadError = true;
        view.load();
        expect(runtime.notify).toHaveBeenCalledWith('error', {msg: 'Test error'});
    });

    it("displays an error when server reports an update XML error", function() {
        server.updateError = true;
        view.save('<openassessment>test!</openassessment>');
        expect(runtime.notify).toHaveBeenCalledWith('error', {msg: 'Test error'});
    });
*/
});
